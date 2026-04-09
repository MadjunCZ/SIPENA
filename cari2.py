import os
import re
import time
import pdfplumber
from tqdm import tqdm
from io import BytesIO
from reportlab.pdfgen import canvas
from PyPDF2 import PdfReader, PdfWriter

BASE_FOLDER = "slips"

# ======================
# INPUT NIP
# ======================
nip_input = input("Masukkan NIP (18 digit):\n").strip()
nips = set(re.findall(r"\d{18}", nip_input))

if not nips:
    print("❌ NIP tidak valid")
    exit()

# ======================
# INPUT BULAN
# ======================
while True:
    bulan_input = input("Masukkan bulan (mm-yyyy, pisahkan koma): ").strip()
    bulan_list = [b.strip() for b in bulan_input.split(",") if b.strip()]

    if not bulan_list:
        print("❌ Tidak boleh kosong")
        continue

    valid = True
    for b in bulan_list:
        if not re.fullmatch(r"\d{2}-\d{4}", b):
            print(f"❌ Format salah: {b}")
            valid = False
            break
        if not os.path.isdir(os.path.join(BASE_FOLDER, b)):
            print(f"❌ Folder tidak ada: {b}")
            valid = False
            break

    if valid:
        break

writers = {nip: PdfWriter() for nip in nips}
nama_map = {}

start = time.time()

# ======================
# PROSES
# ======================
for bulan in bulan_list:
    folder = os.path.join(BASE_FOLDER, bulan)
    files = [f for f in os.listdir(folder) if f.lower().endswith(".pdf")]

    print(f"\n🔍 Scan {bulan} ({len(files)} file)")

    for file in tqdm(files, desc=f"📂 {bulan}"):
        path = os.path.join(folder, file)

        try:
            plumber_pdf = pdfplumber.open(path)
            reader = PdfReader(path)
        except:
            continue

        for i, page in enumerate(plumber_pdf.pages):
            text = page.extract_text()
            if not text:
                continue

            found_nips = set(re.findall(r"\d{18}", text)) & nips
            if not found_nips:
                continue

            words = page.extract_words()

            packet = BytesIO()
            c = canvas.Canvas(packet, pagesize=(page.width, page.height))

            # masking NIP lain
            for w in words:
                if re.fullmatch(r"\d{18}", w["text"]):
                    if w["text"] not in found_nips:
                        x0, top, x1, bottom = w["x0"], w["top"], w["x1"], w["bottom"]
                        c.rect(x0, page.height - bottom, x1 - x0, bottom - top, fill=1)

            ada_blur = False

            for w in words:
                if re.fullmatch(r"\d{18}", w["text"]):
                    if w["text"] not in found_nips:
                        x0, top, x1, bottom = w["x0"], w["top"], w["x1"], w["bottom"]
                        c.rect(x0, page.height - bottom, x1 - x0, bottom - top, fill=1)
                        ada_blur = True

            c.save()
            packet.seek(0)

            base_page = reader.pages[i]

            if ada_blur:
                overlay = PdfReader(packet)
                base_page.merge_page(overlay.pages[0])

            lines = [l.strip() for l in text.splitlines() if l.strip()]

            for nip in found_nips:
                writers[nip].add_page(base_page)

                if nip not in nama_map:
                    for idx, line in enumerate(lines):
                        if nip in line and idx >= 2:
                            nama_map[nip] = lines[idx - 2]
                            break

# ======================
# SIMPAN
# ======================
bulan_tag = "-".join(bulan_list)
hasil = 0

for nip, writer in writers.items():
    if writer.pages:
        nama = nama_map.get(nip, "TANPA_NAMA")
        nama = re.sub(r"[^\w ]", "", nama).replace(" ", "_")

        filename = f"slip_{nip}_{nama}_{bulan_tag}.pdf"

        with open(filename, "wb") as f:
            writer.write(f)

        hasil += 1

elapsed = time.time() - start

print("\n====================")
print(f"✅ Selesai: {hasil} file")
print(f"⏱️ Waktu: {elapsed:.2f} detik")
print("====================")