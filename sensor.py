import fitz
import re

def apply_sensor(page, target_nip, text):
    """
    Melakukan sensor blok hitam pada dokumen, secara khusus menyembunyikan
    data milik orang lain berdasarkan kedekatannya secara tata letak dengan NIP mereka.
    """
    # Ekstrak letak seluruh NIP pada halaman ini
    all_nips = set(re.findall(r"\b\d{18}\b", text))
    
    nip_centers = {}
    for n in all_nips:
        n_rects = page.search_for(n)
        if n_rects:
            cx = (n_rects[0].x0 + n_rects[0].x1) / 2
            cy = (n_rects[0].y0 + n_rects[0].y1) / 2
            nip_centers[n] = (cx, cy)

    # Kalau isi tabelnya cuma berisi 1 NIP (target saja) atau tidak ada target, biarkan
    if len(nip_centers) <= 1 or target_nip not in nip_centers:
        return page

    semua_y = [cy for cx, cy in nip_centers.values()]
    min_y = min(semua_y)
    max_y = max(semua_y)
    
    # Segala sesuatu yang letaknya di atas tinggi "Nama" orang pertama (sekitar 35pt di atas NIP pertama)
    header_limit = min_y - 30 
    
    # Batas aman luaran bawah tabel (diperbesar agar baris NPWP tidak luput dari sensor)
    footer_limit = max_y + 30

    words = page.get_text("words")

    # Pelacak dinamis berbasis list index untuk mendeteksi "JUMLAH LEMBAR" 
    # yang seringkali gagal ditangkap `search_for` akibat spasi ganda parsial PDF
    for i, w in enumerate(words):
        w_text = w[4].strip().upper()
        # Cari kombinasi kata JUMLAH dan LEMBAR yang berdekatan
        if "JUMLAH" in w_text:
            if i + 1 < len(words) and "LEMBAR" in words[i+1][4].strip().upper():
                wy_batas = w[1] # Ambil posisi y atap kata tersebut
                if wy_batas < footer_limit:
                    # Mundurkan garis aman hingga memproteksi baris JUMLAH LEMBAR ini
                    footer_limit = wy_batas - 15
                break

    for w in words:
        wy = (w[1] + w[3]) / 2
        
        # Abaikan teks yang letaknya di judul atas atau pada area footer paling bawah dokumen
        if wy < header_limit or wy > footer_limit:
            continue
        
        # Pengecualian mutlak: Jangan pernah sensor kata "NO." dan "URT" 
        if w[4].strip().upper() in ["NO.", "URT"]:
            continue
        
        wx = (w[0] + w[2]) / 2
        min_dist = float('inf')
        closest_nip = None
        
        # Clustering tiap teks ke NIP terdekatnya 
        # (Bobot Y lebih besar untuk memastikan satu baris ikut ke NIP yang sebaris)
        for n, (cx, cy) in nip_centers.items():
            dist = ((wx - cx)**2)*0.1 + ((wy - cy)**2)
            if dist < min_dist:
                min_dist = dist
                closest_nip = n
        
        # Sensor jika teks tersebut masuk 'wilayah' NIP orang lain
        if closest_nip != target_nip:
            # Tambahkan margin sedikit agar sensor menyatu solid
            rect = fitz.Rect(w[0]-1.5, w[1]-1.5, w[2]+1.5, w[3]+1.5)
            page.add_redact_annot(rect, fill=(0, 0, 0))
    
    page.apply_redactions()
    return page
