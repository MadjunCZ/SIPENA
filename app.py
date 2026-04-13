import os
import re
import logging
from flask import Flask, request, render_template, send_file, flash
from PyPDF2 import PdfReader, PdfWriter

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
app.secret_key = "sipena"

BASE_FOLDER = "slips"
OUTPUT_FOLDER = "output"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        nip_input = request.form.get("nip", "")
        bulan_input = request.form.get("bulan", "")

        nips = set(re.findall(r"\d{18}", nip_input))
        bulan_list = [b.strip() for b in bulan_input.split(",") if b.strip()]

        if not nips:
            flash("NIP tidak valid")
            return render_template("index.html")
        if len(nips) > 1:
            flash("Hanya diperbolehkan mencari maksimal 1 NIP")
            return render_template("index.html")
        if len(bulan_list) > 1:
            flash("Hanya diperbolehkan mencari maksimal 1 Bulan")
            return render_template("index.html")

        writers = {nip: PdfWriter() for nip in nips}
        names = {nip: "" for nip in nips}

        logging.info(f"Memulai proses pencarian untuk NIP: {list(nips)[0]}, Bulan: {bulan_list[0]}")

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
                reader = PdfReader(pdf_path)

                for page_num, page in enumerate(reader.pages):
                    text = page.extract_text()
                    if not text:
                        continue

                    found = set(re.findall(r"\d{18}", text)) & nips

                    for nip in found:
                        writers[nip].add_page(page)
                        logging.info(f">> Halaman {page_num+1} mengandung NIP {nip}")
                        
                        # Ekstrak nama (Nama berada 2 baris di atas baris yang mengandung NIP)
                        lines = text.split('\n')
                        raw_nama = ""
                        for i, line in enumerate(lines):
                            if nip in line:
                                if i >= 2:
                                    raw_nama = lines[i-2].strip()
                                break

                        if raw_nama:
                            clean_nama = re.sub(r'[<>\:"/\\|?*]', '', raw_nama)
                            names[nip] = clean_nama.strip()[:50]

                        is_found = True
                        
                    if is_found:
                        break
                
                if is_found:
                    logging.info(f"Pencarian dihentikan karena slip NIP {list(nips)[0]} telah ditemukan.")
                    break
            
            if is_found:
                break

        # simpan & download (1 nip saja)
        nip = list(nips)[0]
        writer = writers[nip]

        if not writer.pages:
            logging.info(f"Pencarian selesai. NIP {nip} tidak ditemukan.")
            flash("Tidak ditemukan")
            return render_template("index.html")

        bulan = bulan_list[0] if bulan_list else "unknown"
        nama_pegawai = names.get(nip, "")
        if nama_pegawai:
            filename = f"slip_gaji_{nip}_{nama_pegawai}_{bulan}.pdf"
        else:
            filename = f"slip_gaji_{nip}_{bulan}.pdf"
            
        path = os.path.join(OUTPUT_FOLDER, filename)

        logging.info(f"Pencarian selesai. Menyimpan {len(writer.pages)} halaman ke {filename}")
        with open(path, "wb") as f:
            writer.write(f)

        logging.info(f"Mengirim file {filename} ke pengguna.")
        response = send_file(path, as_attachment=True)
        response.set_cookie('download_complete', '1', max_age=30)
        return response

    return render_template("index.html")

if __name__ == "__main__":
    app.run()