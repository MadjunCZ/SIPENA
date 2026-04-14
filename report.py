import os
import json
import time
import urllib.request
import logging
from datetime import datetime

REPORT_FILE = "laporan_pengunduhan.xlsx"

# Konfigurasi Telegram
TELEGRAM_TOKEN_SIPENA = os.getenv("TELEGRAM_TOKEN_SIPENA", "")
TELEGRAM_CHAT_ID_SIPENA = os.getenv("TELEGRAM_CHAT_ID_SIPENA", "")

print(TELEGRAM_TOKEN_SIPENA)
print(TELEGRAM_CHAT_ID_SIPENA)

def send_telegram_notification(nama_pemohon, unit_kerja, keperluan, nip_dicari, bulan, status):
    if not TELEGRAM_TOKEN_SIPENA or not TELEGRAM_CHAT_ID_SIPENA:
        return
    
    text = (
        f"🔔 *Notifikasi SIPENA - Log Slip Gaji*\n\n"
        f"👤 *Pemohon:* {nama_pemohon}\n"
        f"🏢 *Unit Kerja:* {unit_kerja}\n"
        f"📌 *Keperluan:* {keperluan}\n"
        f"📄 *NIP:* {nip_dicari}\n"
        f"📅 *Bulan:* {bulan}\n"
        f"ℹ️ *Status:* {status}"
    )
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN_SIPENA}/sendMessage"
    data = json.dumps({
        "chat_id": TELEGRAM_CHAT_ID_SIPENA,
        "text": text,
        "parse_mode": "Markdown"
    }).encode("utf-8")
    
    try:
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        logging.error(f"Gagal mengirim notif Telegram: {e}")

def poll_telegram_updates():
    if not TELEGRAM_TOKEN_SIPENA:
        return
    offset = 0
    url_base = f"https://api.telegram.org/bot{TELEGRAM_TOKEN_SIPENA}"
    
    # Mendaftarkan Menu (/ commands) ke sistem Telegram
    try:
        commands_url = f"{url_base}/setMyCommands"
        commands_data = json.dumps({
            "commands": [
                {"command": "get_laporan", "description": "Unduh log dari pendaftar slip gaji ter-update (Excel)"}
            ]
        }).encode("utf-8")
        commands_req = urllib.request.Request(commands_url, data=commands_data, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(commands_req, timeout=10)
    except Exception as e:
        logging.error(f"Gagal mengatur menu Telegram: {e}")
    
    while True:
        try:
            get_updates_url = f"{url_base}/getUpdates?offset={offset}&timeout=30"
            req = urllib.request.Request(get_updates_url)
            with urllib.request.urlopen(req, timeout=35) as response:
                result = json.loads(response.read())
            
            if result.get("ok"):
                for update in result.get("result", []):
                    offset = update["update_id"] + 1
                    message = update.get("message")
                    if message and message.get("text", "").strip() == "/get_laporan":
                        chat_id = message["chat"]["id"]
                        
                        if os.path.exists(REPORT_FILE):
                            import uuid
                            boundary = uuid.uuid4().hex
                            with open(REPORT_FILE, "rb") as f:
                                file_data = f.read()
                            filename = os.path.basename(REPORT_FILE)
                            
                            body = [
                                f'--{boundary}\r\n'.encode('utf-8'),
                                b'Content-Disposition: form-data; name="chat_id"\r\n\r\n',
                                f'{chat_id}\r\n'.encode('utf-8'),
                                f'--{boundary}\r\n'.encode('utf-8'),
                                f'Content-Disposition: form-data; name="document"; filename="{filename}"\r\n'.encode('utf-8'),
                                b'Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet\r\n\r\n',
                                file_data,
                                b'\r\n',
                                f'--{boundary}\r\n'.encode('utf-8'),
                                b'Content-Disposition: form-data; name="caption"\r\n\r\n',
                                b'Berikut adalah laporan pengunduhan slip gaji terkini.\r\n',
                                f'--{boundary}--\r\n'.encode('utf-8')
                            ]
                            body_data = b''.join(body)
                            url_send = f"{url_base}/sendDocument"
                            req_send = urllib.request.Request(url_send, data=body_data)
                            req_send.add_header('Content-Type', f'multipart/form-data; boundary={boundary}')
                            urllib.request.urlopen(req_send, timeout=10)
                        else:
                            url_send = f"{url_base}/sendMessage"
                            send_data = json.dumps({"chat_id": chat_id, "text": "Laporan belum tersedia (belum ada unduhan)."}).encode("utf-8")
                            req_send = urllib.request.Request(url_send, data=send_data, headers={"Content-Type": "application/json"})
                            urllib.request.urlopen(req_send, timeout=10)
        except urllib.error.URLError:
            time.sleep(2)  # Abaikan error timeout/koneksi
        except Exception as e:
            logging.error(f"Telegram Bot Polling Error: {e}")
            time.sleep(5)

def log_report(nama_pemohon, unit_kerja, keperluan, nip_dicari, bulan, status):
    import openpyxl
    try:
        file_exists = os.path.isfile(REPORT_FILE)
        if file_exists:
            wb = openpyxl.load_workbook(REPORT_FILE)
            ws = wb.active
        else:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Laporan Pengunduhan"
            # Tulis Header jika file baru dibuat
            ws.append(['Waktu', 'Nama Pemohon', 'Unit Kerja', 'Keperluan', 'NIP', 'Bulan', 'Status'])
            
        waktu = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ws.append([waktu, nama_pemohon, unit_kerja, keperluan, nip_dicari, bulan, status])
        
        # Sesuaikan otomatis panjang kolom dengan isi teks
        for col in ws.columns:
            max_length = 0
            column_letter = col[0].column_letter
            for cell in col:
                if cell.value:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
            # Tambahkan sedikit spasi ekstra (padding)
            ws.column_dimensions[column_letter].width = max_length + 2

        wb.save(REPORT_FILE)
    except Exception as e:
        logging.error(f"Gagal menulis ke laporan Excel: {e}")

    # Kirim notifikasi Telegram
    send_telegram_notification(nama_pemohon, unit_kerja, keperluan, nip_dicari, bulan, status)




