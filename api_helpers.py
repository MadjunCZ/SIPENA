"""
API Helper Functions untuk Slip Gaji API
Modul ini berisi helper functions untuk REST API endpoint
"""
import os
import re
import logging
from functools import wraps
from flask import request, jsonify, Response
from slip_search import search_slip_in_folder, generate_slip_filename, convert_api_bulan_to_folder

# Konfigurasi API Key dari environment
API_KEY = os.getenv("API_KEY", "sipena-secret")

# Static data lists (diambil dari UI existing)
SATUAN_KERJA_LIST = [
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

KEPERLUAN_LIST = [
    "Pengajuan Bank",
    "BPJS",
    "Kredit",
    "Administrasi",
    "Lainnya"
]


def require_api_key(f):
    """
    Decorator untuk memvalidasi API Key pada endpoint /api/*
    Jika API key invalid, return 401 Unauthorized
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        provided_key = request.headers.get('X-API-KEY')
        
        if not provided_key:
            logging.warning(f"API request tanpa API key dari IP: {request.remote_addr}")
            return jsonify({
                "success": False,
                "message": "Unauthorized: Missing API Key"
            }), 401
        
        if provided_key != API_KEY:
            logging.warning(f"API request dengan API key invalid dari IP: {request.remote_addr}")
            return jsonify({
                "success": False,
                "message": "Unauthorized: Invalid API Key"
            }), 401
        
        return f(*args, **kwargs)
    return decorated_function


def json_response(success, message=None, data=None, status_code=200):
    """
    Helper untuk membuat response JSON konsisten
    """
    response = {"success": success}
    if message:
        response["message"] = message
    if data is not None:
        response["data"] = data
    return jsonify(response), status_code


def validate_nip(nip):
    """
    Validasi NIP harus 18 digit angka
    Return: (is_valid, error_message)
    """
    if not nip:
        return False, "NIP tidak boleh kosong"
    
    if not isinstance(nip, str):
        nip = str(nip)
    
    # Hapus spasi dan whitespace
    nip = nip.strip()
    
    # Cek apakah hanya berisi angka
    if not nip.isdigit():
        return False, "NIP harus berisi hanya angka"
    
    # Cek panjang 18 digit
    if len(nip) != 18:
        return False, f"NIP harus 18 digit, sekarang {len(nip)} digit"
    
    return True, None


def validate_bulan(bulan):
    """
    Validasi format bulan (YYYY-MM)
    Return: (is_valid, error_message)
    """
    if not bulan:
        return False, "Bulan tidak boleh kosong"
    
    bulan = bulan.strip()
    
    # Format yang diterima: YYYY-MM atau YYYY-M
    pattern = r'^\d{4}-(0[1-9]|1[0-2])$'
    if not re.match(pattern, bulan):
        return False, "Format bulan harus YYYY-MM (contoh: 2026-05)"
    
    return True, None


def get_satuan_kerja_list():
    """
    Return daftar satuan kerja
    """
    return SATUAN_KERJA_LIST


def get_keperluan_list():
    """
    Return daftar keperluan
    """
    return KEPERLUAN_LIST


# Alias for backward compatibility - menggunakan slip_search module
def search_slip_gaji(nip, bulan, apply_sensor_func=None):
    """
    Alias untuk search_slip_in_folder dari slip_search module.
    """
    return search_slip_in_folder(nip, bulan, apply_sensor_func)


def send_pdf_response(pdf_data, filename):
    """
    Helper untuk mengirim response PDF
    """
    response = Response(
        pdf_data,
        mimetype="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(pdf_data))
        }
    )
    return response
