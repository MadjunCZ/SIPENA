# Slip Gaji API Documentation

REST API untuk mengambil slip gaji secara programmatic.

## Base URL

```
http://localhost:5000
```

## Authentication

Semua endpoint API memerlukan header `X-API-KEY`.

| Header | Value | Required |
|--------|-------|----------|
| X-API-KEY | `sipena-secret` | Ya |

Jika API key tidak valid, response:

```json
{
  "success": false,
  "message": "Unauthorized: Invalid API Key"
}
```

**HTTP Status:** `401 Unauthorized`

---

## Endpoints

### 1. Ambil Slip Gaji

Ambil slip gaji dalam format PDF.

**Endpoint:** `POST /api/slip`

**Headers:**
```
X-API-KEY: sipena-secret
Content-Type: application/json
```

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `nip` | string | Ya | NIP 18 digit |
| `bulan` | string | Ya | Format YYYY-MM (contoh: 2026-05) |
| `unit_kerja` | string | Tidak | Satuan kerja (untuk logging) |
| `keperluan` | string | Tidak | Keperluan (untuk logging) |

**Contoh Request:**

```bash
curl -X POST http://localhost:5000/api/slip \
  -H "X-API-KEY: sipena-secret" \
  -H "Content-Type: application/json" \
  -d '{
    "nip": "198609012019031008",
    "bulan": "2026-05",
    "unit_kerja": "BKD",
    "keperluan": "API"
  }'
```

**Response Berhasil:**

- **HTTP Status:** `200 OK`
- **Content-Type:** `application/pdf`
- **Content-Disposition:** `attachment; filename="slip_gaji_{nip}_{nama}_{bulan}.pdf"`

**Response Gagal:**

```json
{
  "success": false,
  "message": "NIP harus 18 digit"
}
```

| HTTP Status | Kondisi |
|-------------|---------|
| `400` | NIP tidak valid / Format bulan salah |
| `401` | API key tidak valid |
| `404` | Slip gaji tidak ditemukan |
| `500` | Internal server error |

---

### 2. Daftar Satuan Kerja

Ambil daftar satuan kerja yang tersedia.

**Endpoint:** `GET /api/satuan-kerja`

**Headers:**
```
X-API-KEY: sipena-secret
```

**Contoh Request:**

```bash
curl http://localhost:5000/api/satuan-kerja \
  -H "X-API-KEY: sipena-secret"
```

**Response:**

```json
{
  "success": true,
  "data": [
    "Sub Bagian Tata Usaha",
    "Seksi Pendidikan Agama Islam",
    "Seksi Bimbingan Masyarakat Islam",
    "Seksi Pendidikan Diniyah dan Pondok Pesantren",
    "Seksi Pendidikan Madrasah",
    "Penyelenggara Zakat dan Wakaf",
    "Kantor Urusan Agama Bagor",
    "Kantor Urusan Agama Baron",
    "Kantor Urusan Agama Berbek",
    "Kantor Urusan Agama Gondang",
    "Kantor Urusan Agama Jatikalen",
    "Kantor Urusan Agama Kertosono",
    "Kantor Urusan Agama Lengkong",
    "Kantor Urusan Agama Loceret",
    "Kantor Urusan Agama Nganjuk",
    "Kantor Urusan Agama Ngetos",
    "Kantor Urusan Agama Ngluyu",
    "Kantor Urusan Agama Ngronggot",
    "Kantor Urusan Agama Pace",
    "Kantor Urusan Agama Patianrowo",
    "Kantor Urusan Agama Prambon",
    "Kantor Urusan Agama Rejoso",
    "Kantor Urusan Agama Sawahan",
    "Kantor Urusan Agama Sukomoro",
    "Kantor Urusan Agama Tanjunganom",
    "Kantor Urusan Agama Wilangan",
    "MAN 1 Nganjuk",
    "MAN 2 Nganjuk",
    "MAN 3 Nganjuk",
    "MIN 1 Nganjuk",
    "MIN 10 Nganjuk",
    "MIN 11 Nganjuk",
    "MIN 2 Nganjuk",
    "MIN 3 Nganjuk",
    "MIN 4 Nganjuk",
    "MIN 5 Nganjuk",
    "MIN 6 Nganjuk",
    "MIN 7 Nganjuk",
    "MIN 8 Nganjuk",
    "MIN 9 Nganjuk",
    "MTsN 1 Nganjuk",
    "MTsN 10 Nganjuk",
    "MTsN 2 Nganjuk",
    "MTsN 3 Nganjuk",
    "MTsN 4 Nganjuk",
    "MTsN 5 Nganjuk",
    "MTsN 6 Nganjuk",
    "MTsN 7 Nganjuk",
    "MTsN 8 Nganjuk",
    "MTsN 9 Nganjuk",
    "Lainnya"
  ]
}
```

---

### 3. Daftar Keperluan

Ambil daftar keperluan slip gaji.

**Endpoint:** `GET /api/keperluan`

**Headers:**
```
X-API-KEY: sipena-secret
```

**Contoh Request:**

```bash
curl http://localhost:5000/api/keperluan \
  -H "X-API-KEY: sipena-secret"
```

**Response:**

```json
{
  "success": true,
  "data": [
    "Pengajuan Bank",
    "BPJS",
    "Kredit",
    "Administrasi",
    "Lainnya"
  ]
}
```

---

## Format Bulan

Format bulan yang digunakan: `YYYY-MM`

| API Input | Folder Name | Contoh |
|-----------|-------------|--------|
| `2026-01` | `01-2026` | Januari 2026 |
| `2026-05` | `05-2026` | Mei 2026 |
| `2026-12` | `12-2026` | Desember 2026 |

---

## Error Responses

Semua endpoint mengembalikan format error yang konsisten:

```json
{
  "success": false,
  "message": "Deskripsi error"
}
```

### Daftar Error

| Message | HTTP Status | Penyebab |
|---------|-------------|----------|
| `Unauthorized: Missing API Key` | 401 | Header X-API-KEY tidak ada |
| `Unauthorized: Invalid API Key` | 401 | API key salah |
| `Content-Type harus application/json` | 400 | Header Content-Type salah |
| `NIP tidak boleh kosong` | 400 | Field nip kosong |
| `NIP harus berisi hanya angka` | 400 | NIP mengandung karakter non-angka |
| `NIP harus 18 digit` | 400 | Panjang NIP bukan 18 |
| `Format bulan harus YYYY-MM` | 400 | Format bulan salah |
| `Data bulan {bulan} tidak ditemukan` | 404 | Folder bulan tidak ada |
| `Slip gaji tidak ditemukan` | 404 | NIP tidak ada di database |
| `Internal Server Error` | 500 | Error tidak terduga |

---

## Contoh Penggunaan (Python)

### Install Dependencies

```bash
pip install requests
```

### Ambil Slip Gaji

```python
import requests

url = "http://localhost:5000/api/slip"
headers = {
    "X-API-KEY": "sipena-secret",
    "Content-Type": "application/json"
}
data = {
    "nip": "198609012019031008",
    "bulan": "2026-05",
    "unit_kerja": "BKD",
    "keperluan": "API"
}

response = requests.post(url, headers=headers, json=data)

if response.status_code == 200:
    # Simpan PDF
    with open("slip_gaji.pdf", "wb") as f:
        f.write(response.content)
    print("PDF berhasil diunduh")
else:
    print(f"Error: {response.json()}")
```

### Ambil Daftar Satuan Kerja

```python
import requests

url = "http://localhost:5000/api/satuan-kerja"
headers = {"X-API-KEY": "sipena-secret"}

response = requests.get(url, headers=headers)

if response.status_code == 200:
    data = response.json()
    for item in data["data"]:
        print(f"- {item}")
else:
    print(f"Error: {response.json()}")
```

### Ambil Daftar Keperluan

```python
import requests

url = "http://localhost:5000/api/keperluan"
headers = {"X-API-KEY": "sipena-secret"}

response = requests.get(url, headers=headers)

if response.status_code == 200:
    data = response.json()
    for item in data["data"]:
        print(f"- {item}")
else:
    print(f"Error: {response.json()}")
```

---

## Integrasi dengan Aplikasi Lain

### Laravel

```php
$response = Http::withHeaders([
    'X-API-KEY' => 'sipena-secret',
])->post('http://localhost:5000/api/slip', [
    'nip' => '198609012019031008',
    'bulan' => '2026-05',
]);

if ($response->successful()) {
    Storage::put('slip_gaji.pdf', $response->body());
}
```

### React / NextJS

```javascript
const response = await fetch('http://localhost:5000/api/slip', {
  method: 'POST',
  headers: {
    'X-API-KEY': 'sipena-secret',
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    nip: '198609012019031008',
    bulan: '2026-05',
  }),
});

if (response.ok) {
  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  // Download file
}
```

### Flutter / Mobile

```dart
final response = await http.post(
  Uri.parse('http://localhost:5000/api/slip'),
  headers: {
    'X-API-KEY': 'sipena-secret',
    'Content-Type': 'application/json',
  },
  body: jsonEncode({
    'nip': '198609012019031008',
    'bulan': '2026-05',
  }),
);

if (response.statusCode == 200) {
  // Simpan atau tampilkan PDF
}
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `API_KEY` | `sipena-secret` | API authentication key |
| `ENABLE_SENSOR` | `True` | Enable/disable sensor fitur |
| `TELEGRAM_TOKEN_SIPENA` | - | Telegram bot token (optional) |
| `TELEGRAM_CHAT_ID_SIPENA` | - | Telegram chat ID (optional) |

---

## Catatan Keamanan

1. **API Key:** Jangan expose API key di client-side code
2. **HTTPS:** Untuk production, gunakan HTTPS
3. **Rate Limiting:** Implementasi rate limiting disarankan untuk production
4. **CORS:** CORS sudah di-enable untuk semua origin

---

## Support CORS

API ini mendukung Cross-Origin Resource Sharing (CORS) sehingga dapat dipanggil dari:

- Web applications (React, Vue, Angular, NextJS)
- Mobile apps (Flutter, React Native, Android/iOS)
- Desktop apps (Electron, etc.)
- Backend services (Laravel, Django, Node.js, etc.)
