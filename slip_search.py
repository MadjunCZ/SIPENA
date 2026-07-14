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


def extract_name_from_text(text, nip):
    """
    Ekstrak nama pegawai dari teks PDF di sekitar baris yang memuat NIP.
    Cocok untuk pola nama yang terpisah menjadi beberapa baris, misalnya:
    "MOCHAMAD MAULUDI"
    "S.Pd.I"
    "NIP 198301042005011003"
    """
    if not text or not nip:
        return ""

    lines = [line.strip() for line in text.splitlines()]
    for idx, line in enumerate(lines):
        if nip not in line:
            continue

        candidates = []
        for prev_idx in range(idx - 1, max(-1, idx - 4), -1):
            prev_line = lines[prev_idx].strip()
            if not prev_line:
                continue

            if re.search(r"\d", prev_line):
                continue

            lowered = prev_line.lower()
            if lowered in {"nama", "name", "pegawai", "nip"} or lowered.startswith("nama") or lowered.startswith("nip"):
                continue

            candidates.append(prev_line)
            if len(candidates) >= 3:
                break

        if not candidates:
            return ""

        candidates = list(reversed(candidates))
        if len(candidates) >= 2:
            last = candidates[-1]
            if re.fullmatch(r"[A-Za-z.\s]+", last) and "." in last and len(last.split()) <= 2:
                return f"{' '.join(candidates[:-1])}, {last}"

        return " ".join(candidates)

    return ""


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

                    raw_nama = extract_name_from_text(text, nip)
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
