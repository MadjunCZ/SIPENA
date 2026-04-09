# SIPENA - Sistem Pengelolaan Slip Gaji ASN

Aplikasi Python untuk mencari, memisahkan (split), dan mengelola slip gaji ASN berdasarkan NIP secara otomatis.

---

## 🚀 Fitur Utama

* 🔍 Cari slip berdasarkan NIP (18 digit)
* 📄 Split PDF otomatis per NIP
* 📂 Support multi bulan (`mm-yyyy`)
* 👥 Support multiple NIP sekaligus
* ⚡ Progress bar (tqdm)
* 🧾 Ambil nama pegawai otomatis (2 baris di atas NIP)
* 📁 Output otomatis ke folder `output/`
* 🔒 (Opsional) Masking NIP lain (kotak hitam)

---

## 📂 Struktur Folder

```
SIPENA/
├── slips/              # sumber file PDF (per bulan)
│   ├── 01-2025/
│   ├── 02-2025/
│   └── ...
├── output/             # hasil file (otomatis)
├── cari.py             # script utama
├── .gitignore
└── README.md
```

---

## ⚙️ Persiapan

### 1. Install Python

Minimal Python 3.8+

Cek versi:

```
python --version
```

---

### 2. Install Library

```
pip install PyPDF2 tqdm
```

#### (Opsional - untuk fitur blur NIP)

```
pip install pdfplumber reportlab
```

---

## ▶️ Cara Penggunaan

### 1. Jalankan Script

```
python cari.py
```

---

### 2. Input NIP

Bisa satu atau banyak:

```
19931224202511059
```

atau:

```
19931224202511059,197606062025212000
```

---

### 3. Input Bulan

Format:

```
mm-yyyy
```

Contoh:

```
01-2025
```

Multi bulan:

```
01-2025,02-2025
```

---

### 4. Proses

* Sistem akan scan folder `slips/`
* Mencari NIP di setiap halaman PDF
* Mengumpulkan halaman sesuai NIP

---

### 5. Hasil

File akan tersimpan di folder:

```
output/
```

Format nama file:

```
slip_<nip>_<nama>_<bulan>.pdf
```

Contoh:

```
slip_198006102002121001_YADIANTO_01-2025.pdf
```

---

## ⚠️ Catatan Penting

* NIP harus **18 digit**
* PDF harus **text-based** (bisa di-copy)
* Jika PDF hasil scan → perlu OCR
* 1 halaman bisa berisi beberapa NIP (akan diproses semua)

---

## 🔒 Keamanan

* Folder `slips/` dan `output/` tidak diupload ke Git
* Disarankan repo dalam mode **private**
* Jangan menyimpan data sensitif di repository

---

## 🧠 Tips

* Gunakan struktur folder per bulan untuk performa lebih cepat
* Gunakan SSD untuk proses ribuan file
* Gunakan sedikit NIP untuk pencarian lebih cepat

---

## 🔧 Troubleshooting

### ❌ Module tidak ditemukan

```
ModuleNotFoundError
```

Solusi:

```
pip install nama_module
```

---

### ❌ NIP tidak ditemukan

* Pastikan NIP benar
* Pastikan ada di PDF
* Coba buka PDF dan copy teks

---

### ❌ PDF tidak terbaca

* Kemungkinan file scan (gambar)
* Solusi: gunakan OCR

---

## 📌 Versi

v1.0 - Fitur dasar (split NIP)
v1.1 - Multi NIP & multi bulan
v1.2 - Output folder + optimasi
v1.3 - Masking NIP lain

---

## 👨‍💻 Pengembang

Dikembangkan untuk kebutuhan internal pengelolaan slip gaji ASN.

---

## ⭐ Lisensi

Internal use only.
