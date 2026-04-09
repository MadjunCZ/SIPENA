import os
import re
import time
from tqdm import tqdm
from PyPDF2 import PdfReader, PdfWriter

BASE_FOLDER = "slips"

# =========================
# INPUT NIP
# =========================
nip_input = input("Masukkan NIP (18 digit, pisahkan koma / enter):\n").strip()
nips = set(re.findall(r"\d{18}", nip_input))

if not nips:
    print("❌ Tidak ada NIP valid (18 digit)")
    exit()

print(f"🎯 Total NIP: {len(nips)}")

# =========================
# INPUT BULAN (VALIDASI)
# =========================
while True:
    bulan_input = input("\nMasukkan bulan (mm-yyyy), bisa banyak (pisahkan koma): ").strip()

    bulan_list = [b.strip() for b in bulan_input.split(",") if b.strip()]
    if not bulan_list:
        print("❌ Bulan tidak boleh kosong")
        continue

    salah = False
    for bulan in bulan_list:
        if not re.fullmatch(r"\d{2}-\d{4}", bulan):
            print(f"❌ Format salah: {bulan}")
            salah = True
            break

        if not os.path.isdir(os.path.join(BASE_FOLDER, bulan)):
            print(f"❌ Folder tidak ditemukan: {bulan}")
            salah = True
            break

    if not salah:
        break

# =========================
# PREPARE
# =========================
writers = {nip: PdfWriter() for nip in nips}
nama_map = {}
bulan_tag = "-".join(bulan_list)

start = time.time()

# =========================
# SCAN PDF
# =========================
for bulan in bulan_list:
    folder = os.path.join(BASE_FOLDER, bulan)
    pdf_files = [f for f in os.listdir(folder) if f.lower().endswith(".pdf")]

    print(f"\n🔍 Scan folder {bulan} ({len(pdf_files)} file)")

    for file in tqdm(pdf_files, desc=f"📂 {bulan}"):
        pdf_path = os.path.join(folder, file)

        try:
            reader = PdfReader(pdf_path)
        except Exception:
            continue

        for page in reader.pages:
            text = page.extract_text()
            if not text:
                continue

            # cari semua NIP di halaman
            found_nips = set(re.findall(r"\d{18}", text)) & nips
            if not found_nips:
                continue

            lines = [l.strip() for l in text.splitlines() if l.strip()]

            for nip in found_nips:
                writers[nip].add_page(page)

                # ambil nama (2 baris di atas nip)
                if nip not in nama_map:
                    for i, line in enumerate(lines):
                        if nip in line and i >= 2:
                            nama_map[nip] = lines[i - 2]
                            break

# =========================
# SIMPAN HASIL
# =========================
hasil = 0
for nip, writer in writers.items():
    if writer.pages:
        nama = nama_map.get(nip, "TANPA_NAMA")
        nama = re.sub(r"[^\w ]", "", nama).replace(" ", "_")

        output_file = f"slip_{nip}_{nama}_{bulan_tag}.pdf"

        with open(output_file, "wb") as f:
            writer.write(f)

        hasil += 1

elapsed = time.time() - start

print("\n==============================")
print(f"✅ Selesai dalam {elapsed:.2f} detik")
print(f"📄 File berhasil dibuat: {hasil}")
print("==============================")
