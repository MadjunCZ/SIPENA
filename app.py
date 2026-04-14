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
from flask import Flask, request, render_template, send_file, flash
from sensor import apply_sensor
from report import log_report, poll_telegram_updates, TELEGRAM_TOKEN_SIPENA

app = Flask(__name__)
app.secret_key = "sipena"

BASE_FOLDER = "slips"
OUTPUT_FOLDER = "output"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Secara default fitur sensor nyala. Untuk mematikannya, set env ENABLE_SENSOR ke "False" atau "0".
ENABLE_SENSOR = os.getenv("ENABLE_SENSOR", "True").lower() in ("true", "1", "t", "yes")
print(f"ENABLE_SENSOR: {ENABLE_SENSOR}")
# Konfigurasi Telegram
TELEGRAM_TOKEN_SIPENA = os.getenv("TELEGRAM_TOKEN_SIPENA", "")
TELEGRAM_CHAT_ID_SIPENA = os.getenv("TELEGRAM_CHAT_ID_SIPENA", "")

@app.route("/", methods=["GET", "POST"])
def index():
    print(TELEGRAM_TOKEN_SIPENA)
    print(TELEGRAM_CHAT_ID_SIPENA)
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
            return render_template("index.html")
        if len(nips) > 1:
            flash("Hanya diperbolehkan mencari maksimal 1 NIP")
            log_report("-", unit_kerja, keperluan, nip_input, bulan_input, "Gagal (Lebih dari 1 NIP)")
            return render_template("index.html")
        if len(bulan_list) > 1:
            flash("Hanya diperbolehkan mencari maksimal 1 Bulan")
            log_report("-", unit_kerja, keperluan, nip_input, bulan_input, "Gagal (Lebih dari 1 Bulan)")
            return render_template("index.html")

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
                        
                        # Ekstrak nama (Nama berada 2 baris di atas baris yang mengandung NIP)
                        lines = text.split('\n')
                        raw_nama = ""
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
            return render_template("index.html")

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

    return render_template("index.html")

if __name__ == "__main__":
    if TELEGRAM_TOKEN_SIPENA:
        t = threading.Thread(target=poll_telegram_updates, daemon=True)
        t.start()
    app.run()