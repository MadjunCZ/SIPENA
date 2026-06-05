import os
import re
import threading
import logging

# Konfigurasi pencatatan log (Ke Terminal & File)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("sipena_error.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

import fitz  # PyMuPDF
from flask import Flask, request, render_template, send_file, flash, jsonify
from flask_cors import CORS
from sensor import apply_sensor
from report import log_report, poll_telegram_updates, TELEGRAM_TOKEN_SIPENA
from api_helpers import (
    require_api_key, validate_nip, validate_bulan,
    get_satuan_kerja_list, get_keperluan_list,
    search_slip_gaji, send_pdf_response
)
from slip_search import search_slip_in_folder

app = Flask(__name__)
app.secret_key = "sipena"

# Enable CORS untuk API endpoints
CORS(app)

BASE_FOLDER = "slips"
OUTPUT_FOLDER = "output"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Secara default fitur sensor nyala. Untuk mematikannya, set env ENABLE_SENSOR ke "False" atau "0".
ENABLE_SENSOR = os.getenv("ENABLE_SENSOR", "False").lower() in ("true", "1", "t", "yes")
print(f"ENABLE_SENSOR: {ENABLE_SENSOR}")
# Konfigurasi Telegram
TELEGRAM_TOKEN_SIPENA = os.getenv("TELEGRAM_TOKEN_SIPENA", "")
TELEGRAM_CHAT_ID_SIPENA = os.getenv("TELEGRAM_CHAT_ID_SIPENA", "")

@app.route("/", methods=["GET", "POST"])
def index():
    logging.info(f"TELEGRAM_TOKEN_SIPENA: {TELEGRAM_TOKEN_SIPENA}")
    logging.info(f"TELEGRAM_CHAT_ID_SIPENA: {TELEGRAM_CHAT_ID_SIPENA}")
    if request.method == "POST":
        nip_input = request.form.get("nip", "")
        bulan_input = request.form.get("bulan", "")
        unit_kerja = request.form.get("unit_kerja", "")
        unit_kerja_lainnya = request.form.get("unit_kerja_lainnya", "")
        keperluan = request.form.get("keperluan", "")
        keperluan_lainnya = request.form.get("keperluan_lainnya", "")

        if unit_kerja == "lainnya" and unit_kerja_lainnya:
            unit_kerja = f"Lainnya ({unit_kerja_lainnya})"

        if keperluan == "Lainnya" and keperluan_lainnya:
            keperluan = f"Lainnya ({keperluan_lainnya})"

        nips = set(re.findall(r"\d{18}", nip_input))
        bulan_list = [b.strip() for b in bulan_input.split(",") if b.strip()]

        if not nips:
            flash("NIP tidak valid")
            log_report("-", unit_kerja, keperluan, nip_input, bulan_input, "Gagal (NIP tidak valid)")
            return render_template("index_new.html")
        if len(nips) > 1:
            flash("Hanya diperbolehkan mencari maksimal 1 NIP")
            log_report("-", unit_kerja, keperluan, nip_input, bulan_input, "Gagal (Lebih dari 1 NIP)")
            return render_template("index_new.html")
        if len(bulan_list) > 1:
            flash("Hanya diperbolehkan mencari maksimal 1 Bulan")
            log_report("-", unit_kerja, keperluan, nip_input, bulan_input, "Gagal (Lebih dari 1 Bulan)")
            return render_template("index_new.html")

        target_nip = list(nips)[0]
        out_doc = fitz.open()  # Untuk menyimpan hasil PDF baru
        names = {target_nip: ""}

        logging.info(f"Memulai proses pencarian untuk NIP: {target_nip}, Bulan: {bulan_list[0]}")

        is_found = False

        for bulan in bulan_list:
            folder = os.path.join(BASE_FOLDER, bulan)
            if not os.path.isdir(folder):
                logging.warning(f"Data bulan {bulan} tidak ditemukan di folder {BASE_FOLDER}")
                continue

            for file in os.listdir(folder):
                if not file.endswith(".pdf"):
                    continue

                pdf_path = os.path.join(folder, file)
                logging.info(f"Membaca isi file: {file}")

                try:
                    doc = fitz.open(pdf_path)
                except Exception as e:
                    logging.warning(f"File rusak atau kosong, dilewati ({file}): {e}")
                    continue

                for page_num in range(len(doc)):
                    page = doc[page_num]
                    text = page.get_text("text")

                    if target_nip in text:
                        logging.info(f">> Halaman {page_num+1} mengandung NIP {target_nip}")

                        # Ekstrak nama menggunakan koordinat y (nama berada di atas NIP pada halaman yang sama)
                        blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]
                        nip_y = None
                        nip_x = None
                        raw_nama = ""

                        # Pertama cari posisi y NIP
                        for block in blocks:
                            if "lines" not in block:
                                continue
                            for line in block["lines"]:
                                for span in line["spans"]:
                                    span_text = span["text"]
                                    if target_nip in span_text:
                                        nip_y = span["bbox"][1]
                                        nip_x = span["bbox"][0]
                                        break

                        # Cari nama di atas NIP - kumpulkan kandidat dan pilih yang terdekat dengan NIP
                        if nip_y is not None:
                            candidates = []
                            # Buat mapping untuk cari span后续
                            all_spans = []
                            for block in blocks:
                                if "lines" not in block:
                                    continue
                                for line in block["lines"]:
                                    for span in line.get("spans", []):
                                        all_spans.append({
                                            "text": span["text"],
                                            "bbox": span["bbox"],
                                            "y": span["bbox"][1],
                                            "x": span["bbox"][0]
                                        })

                            for block in blocks:
                                if "lines" not in block:
                                    continue
                                for line in block["lines"]:
                                    spans = line.get("spans", [])
                                    for idx, span in enumerate(spans):
                                        span_text = span["text"].strip()
                                        bbox = span["bbox"]
                                        # Nama harus di atas NIP dan di kiri (x posisi similar)
                                        if bbox[1] < nip_y and abs(bbox[0] - nip_x) < 100:
                                            # Skip jika ini adalah header/label
                                            if any(skip in span_text.upper() for skip in ['NAMA', 'NIP', 'UNIT', 'GAJI', 'LHR', 'NIK', 'NO.', 'NOMOR']):
                                                continue
                                            # Skip jika hanya angka atau simbol
                                            if re.match(r'^[\d\s\.\-]+$', span_text):
                                                continue
                                            # Skip gelar单独出现的情况 (termasuk gelar dengan titik di akhir)
                                            if span_text.startswith(',') or re.match(r'^S\.(Pd|PdI|Si|Kom|MM|MT|Dr)\.?$', span_text):
                                                continue
                                            # Ini应该是 nama
                                            if len(span_text) > 2:
                                                # Check if next span in same line is a gelar
                                                if idx + 1 < len(spans):
                                                    next_span = spans[idx + 1]
                                                    next_text = next_span["text"].strip()
                                                    if next_text.startswith(','):
                                                        span_text = span_text + next_text

                                                # Check for gelar on next line (close in y position ~10-20 units)
                                                span_y = bbox[1]
                                                for next_span_info in all_spans:
                                                    if abs(next_span_info["y"] - span_y) < 20 and abs(next_span_info["x"] - bbox[0]) < 50:
                                                        next_text = next_span_info["text"].strip()
                                                        # Gabungkan jika gelar atau nama kedua
                                                        if next_text.startswith(','):
                                                            span_text = span_text + next_text
                                                        elif re.match(r'^S\.(Pd|PdI|Si|Kom|MM|MT|Dr)\.?$', next_text):
                                                            # Hindari double comma
                                                            if not span_text.endswith(','):
                                                                span_text = span_text + ","
                                                            span_text = span_text + " " + next_text
                                                            break

                                                # Jarak dari NIP (semakin dekat semakin baik)
                                                distance = nip_y - bbox[1]
                                                candidates.append((distance, span_text))

                            # Pilih kandidat yang paling dekat dengan NIP
                            if candidates:
                                candidates.sort(key=lambda x: x[0])
                                raw_nama = candidates[0][1]

                        # Fallback: jika tidak ketemu dengan span, cari di lines
                        if not raw_nama:
                            lines = text.split('\n')
                            for i, line in enumerate(lines):
                                if target_nip in line:
                                    if i >= 2:
                                        raw_nama = lines[i-2].strip()
                                    break

                        if raw_nama:
                            clean_nama = re.sub(r'[<>\:"/\\|?*\n\r]', '', raw_nama)
                            names[target_nip] = clean_nama.strip()[:50]

                        # Eksekusi logika sensor jika saklar fitur aktif (kode logic dipisah ke sensor.py)
                        if ENABLE_SENSOR:
                            apply_sensor(page, target_nip, text)

                        # Masukkan halaman yang sudah disensor ke file output
                        out_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)

                        is_found = True
                        break

                doc.close()
                if is_found:
                    logging.info(f"Pencarian dihentikan karena slip NIP {list(nips)[0]} telah ditemukan.")
                    break

            if is_found:
                break

        # simpan & download hasil akhir
        if out_doc.page_count == 0:
            logging.info(f"Pencarian selesai. NIP {target_nip} tidak ditemukan.")
            flash("Tidak ditemukan")
            out_doc.close()
            bulan = bulan_list[0] if bulan_list else "unknown"
            log_report("-", unit_kerja, keperluan, target_nip, bulan, "Tidak Ditemukan")
            return render_template("index_new.html")

        bulan = bulan_list[0] if bulan_list else "unknown"
        nama_pegawai = names.get(target_nip, "")
        if nama_pegawai:
            filename = f"slip_gaji_{target_nip}_{nama_pegawai}_{bulan}.pdf"
        else:
            filename = f"slip_gaji_{target_nip}_{bulan}.pdf"

        path = os.path.join(OUTPUT_FOLDER, filename)

        logging.info(f"Pencarian selesai. Menyimpan {out_doc.page_count} halaman ke {filename}")
        out_doc.save(path)
        out_doc.close()

        log_report(nama_pegawai if nama_pegawai else "-", unit_kerja, keperluan, target_nip, bulan, "Berhasil Diunduh")

        # Baca file ke dalam memori agar fisiknya dapat langsung dihapus
        with open(path, "rb") as f:
            pdf_data = f.read()

        try:
            os.remove(path)
            logging.info(f"File {filename} telah dihapus dari direktori lokal.")
        except Exception as e:
            logging.error(f"Gagal menghapus file {filename}: {e}")

        logging.info(f"Mengirim file {filename} ke pengguna.")
        from flask import Response
        response = Response(
            pdf_data,
            mimetype="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
        response.set_cookie('download_complete', '1', max_age=30)
        return response

    return render_template("index_new.html")


# =============================================================================
# API ENDPOINTS
# =============================================================================

@app.route("/api/slip", methods=["POST"])
@require_api_key
def api_get_slip():
    """
    Endpoint API untuk mengambil slip gaji

    Request Headers:
        X-API-KEY: sipena-secret
        Content-Type: application/json

    Request Body:
        {
            "nip": "198765432109876543",
            "bulan": "2026-05",
            "unit_kerja": "BKD",        // optional
            "keperluan": "API"          // optional
        }

    Response:
        - 200: PDF file (Content-Type: application/pdf)
        - 400: JSON error (invalid request)
        - 401: JSON error (unauthorized)
        - 404: JSON error (slip not found)
        - 500: JSON error (internal error)
    """
    logging.info(f"API: Request slip gaji dari IP: {request.remote_addr}")

    try:
        # Validate Content-Type
        if not request.is_json:
            return jsonify({
                "success": False,
                "message": "Content-Type harus application/json"
            }), 400

        data = request.get_json()

        # Get parameters
        nip = data.get("nip", "")
        bulan = data.get("bulan", "")
        unit_kerja = data.get("unit_kerja", "API")
        keperluan = data.get("keperluan", "API")

        # Validate NIP
        is_valid_nip, nip_error = validate_nip(nip)
        if not is_valid_nip:
            logging.warning(f"API: NIP tidak valid - {nip_error}")
            return jsonify({
                "success": False,
                "message": nip_error
            }), 400

        # Validate Bulan
        is_valid_bulan, bulan_error = validate_bulan(bulan)
        if not is_valid_bulan:
            logging.warning(f"API: Bulan tidak valid - {bulan_error}")
            return jsonify({
                "success": False,
                "message": bulan_error
            }), 400

        logging.info(f"API: Mencari slip untuk NIP: {nip}, Bulan: {bulan}")

        # Search slip using helper (with sensor if enabled)
        apply_sensor_func = apply_sensor if ENABLE_SENSOR else None
        is_found, result, error_msg = search_slip_gaji(nip, bulan, apply_sensor_func)

        if not is_found:
            logging.info(f"API: Slip tidak ditemukan untuk NIP: {nip}")
            log_report("-", unit_kerja, keperluan, nip, bulan, "API - Tidak Ditemukan")
            return jsonify({
                "success": False,
                "message": error_msg or "Slip gaji tidak ditemukan"
            }), 404

        # Log success report
        nama_pegawai = result.get("nama", "-")
        log_report(nama_pegawai, unit_kerja, keperluan, nip, bulan, "API - Berhasil Diunduh")

        # Send PDF response
        logging.info(f"API: Slip ditemukan, mengirim PDF: {result['filename']}")
        return send_pdf_response(result["pdf_data"], result["filename"])

    except Exception as e:
        logging.error(f"API: Error pada endpoint /api/slip: {str(e)}")
        return jsonify({
            "success": False,
            "message": "Internal Server Error"
        }), 500


@app.route("/api/satuan-kerja", methods=["GET"])
@require_api_key
def api_satuan_kerja():
    """
    Endpoint API untuk mengambil daftar satuan kerja

    Request Headers:
        X-API-KEY: sipena-secret

    Response:
        200: {
            "success": true,
            "data": ["Satuan Kerja 1", "Satuan Kerja 2", ...]
        }
    """
    logging.info(f"API: Request daftar satuan kerja dari IP: {request.remote_addr}")

    try:
        satuan_kerja = get_satuan_kerja_list()
        return jsonify({
            "success": True,
            "data": satuan_kerja
        }), 200
    except Exception as e:
        logging.error(f"API: Error pada endpoint /api/satuan-kerja: {str(e)}")
        return jsonify({
            "success": False,
            "message": "Internal Server Error"
        }), 500


@app.route("/api/keperluan", methods=["GET"])
@require_api_key
def api_keperluan():
    """
    Endpoint API untuk mengambil daftar keperluan

    Request Headers:
        X-API-KEY: sipena-secret

    Response:
        200: {
            "success": true,
            "data": ["Pengajuan Bank", "BPJS", "Kredit", "Administrasi", "Lainnya"]
        }
    """
    logging.info(f"API: Request daftar keperluan dari IP: {request.remote_addr}")

    try:
        keperluan = get_keperluan_list()
        return jsonify({
            "success": True,
            "data": keperluan
        }), 200
    except Exception as e:
        logging.error(f"API: Error pada endpoint /api/keperluan: {str(e)}")
        return jsonify({
            "success": False,
            "message": "Internal Server Error"
        }), 500


if __name__ == "__main__":
    if TELEGRAM_TOKEN_SIPENA:
        t = threading.Thread(target=poll_telegram_updates, daemon=True)
        t.start()
    app.run()