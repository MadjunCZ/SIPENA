"""
Slip Search Module
Modul ini berisi logic untuk mencari slip gaji
Digunakan oleh both web route dan API endpoint
"""
import os
import re
import logging
import fitz  # PyMuPDF
import io


def convert_api_bulan_to_folder(bulan):
    """
    Konversi format API (YYYY-MM) ke format folder (MM-YYYY)
    Contoh: "2026-05" -> "05-2026"
    """
    try:
        parts = bulan.split("-")
        if len(parts) == 2:
            return f"{parts[1]}-{parts[0]}"
    except:
        pass
    return bulan


def search_slip_in_folder(nip, bulan, apply_sensor_func=None):
    """
    Fungsi utama untuk mencari slip gaji berdasarkan NIP dan bulan.

    Args:
        nip: 18 digit NIP
        bulan: Format YYYY-MM (dari API) atau MM-YYYY (dari web)
        apply_sensor_func: Function untuk apply sensor (optional)

    Returns:
        tuple: (is_found, result_dict, message)
            - Jika found: (True, {"pdf_data": bytes, "filename": str, "nama": str}, None)
            - Jika tidak found: (False, None, "Slip tidak ditemukan")
            - Jika folder tidak ada: (False, None, "Data bulan {bulan} tidak ditemukan")
            - Jika error: (False, None, "Error message")
    """
    BASE_FOLDER = "slips"

    try:
        # Konversi format YYYY-MM ke MM-YYYY
        folder_bulan = convert_api_bulan_to_folder(bulan)
        folder = os.path.join(BASE_FOLDER, folder_bulan)

        if not os.path.isdir(folder):
            logging.warning(f"Data bulan {bulan} tidak ditemukan di folder {BASE_FOLDER}")
            return False, None, f"Data bulan {bulan} tidak ditemukan"

        # Ekstrak nama untuk nama file
        names = {nip: ""}
        is_found = False
        out_doc = fitz.open()

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

                if nip in text:
                    logging.info(f">> Halaman {page_num+1} mengandung NIP {nip}")

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
                                if nip in span_text:
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
                            if nip in line:
                                if i >= 2:
                                    raw_nama = lines[i-2].strip()
                                break

                    if raw_nama:
                        clean_nama = re.sub(r'[<>\:"/\\|?*\n\r]', '', raw_nama)
                        names[nip] = clean_nama.strip()[:50]

                    # Apply sensor jika function disediakan
                    if apply_sensor_func:
                        apply_sensor_func(page, nip, text)

                    # Masukkan halaman yang sudah disensor ke file output
                    out_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)

                    is_found = True
                    break

            doc.close()
            if is_found:
                logging.info(f"Pencarian dihentikan karena slip NIP {nip} telah ditemukan.")
                break

        if out_doc.page_count == 0:
            out_doc.close()
            logging.info(f"Pencarian selesai. NIP {nip} tidak ditemukan.")
            return False, None, "Slip gaji tidak ditemukan"

        # Generate filename
        nama_pegawai = names.get(nip, "")
        if nama_pegawai:
            filename = f"slip_gaji_{nip}_{nama_pegawai}_{bulan}.pdf"
        else:
            filename = f"slip_gaji_{nip}_{bulan}.pdf"

        # Save ke memory buffer
        buffer = io.BytesIO()
        out_doc.save(buffer)
        out_doc.close()
        buffer.seek(0)
        pdf_data = buffer.read()

        logging.info(f"Slip ditemukan. PDF size: {len(pdf_data)} bytes")
        return True, {"pdf_data": pdf_data, "filename": filename, "nama": nama_pegawai}, None

    except Exception as e:
        logging.error(f"Error saat mencari slip gaji: {e}")
        return False, None, f"Internal Server Error: {str(e)}"


def generate_slip_filename(nip, nama_pegawai, bulan):
    """
    Generate nama file slip gaji yang konsisten
    """
    if nama_pegawai:
        return f"slip_gaji_{nip}_{nama_pegawai}_{bulan}.pdf"
    else:
        return f"slip_gaji_{nip}_{bulan}.pdf"
