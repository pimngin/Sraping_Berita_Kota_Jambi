import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
import csv

def parse_tanggal_jambilink(tanggal_str):
    """
    Mengubah string tanggal dari JambiLink menjadi objek datetime.
    Format yang didukung:
    - Relatif: "8 minutes ago", "2 hours ago", "3 days ago", "1 week ago", dll.
    - Absolut dari halaman detail: "21/04/2026 10:20 WIB"
    """
    if not tanggal_str:
        return None, ""
    
    tanggal_str = tanggal_str.strip()
    now = datetime.now()
    
    # --- Format relatif (dari halaman indek) ---
    if 'ago' in tanggal_str.lower():
        match = re.search(r'(\d+)\s+(second|minute|hour|day|week|month)', tanggal_str.lower())
        if match:
            angka = int(match.group(1))
            satuan = match.group(2)
            if satuan == 'second':
                dt = now - timedelta(seconds=angka)
            elif satuan == 'minute':
                dt = now - timedelta(minutes=angka)
            elif satuan == 'hour':
                dt = now - timedelta(hours=angka)
            elif satuan == 'day':
                dt = now - timedelta(days=angka)
            elif satuan == 'week':
                dt = now - timedelta(weeks=angka)
            elif satuan == 'month':
                dt = now - timedelta(days=angka * 30)
            else:
                dt = now
            return dt, dt.strftime("%d/%m/%Y %H:%M")
        return now, now.strftime("%d/%m/%Y %H:%M")
    
    # --- Format absolut: "21/04/2026 10:20 WIB" ---
    clean = tanggal_str.replace("WIB", "").strip()
    try:
        dt = datetime.strptime(clean, "%d/%m/%Y %H:%M")
        return dt, tanggal_str.strip()
    except ValueError:
        pass
    
    return None, tanggal_str.strip()


def fetch_tanggal_detail(url, headers):
    """
    Mengambil tanggal publikasi dari halaman detail artikel JambiLink.
    Selektor: time.datetime (memiliki atribut 'datetime' format ISO)
    Fallback: span.views-field-created > span.field-content
    Mengembalikan string tanggal atau "".
    """
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return ""
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Cara 1: Dari atribut datetime di elemen <time>
        time_el = soup.find('time', class_='datetime')
        if time_el:
            # Atribut datetime berisi ISO: "2026-04-21T08:20:47+07:00"
            iso_str = time_el.get('datetime', '')
            if iso_str:
                try:
                    dt = datetime.fromisoformat(iso_str)
                    return dt.strftime("%d/%m/%Y %H:%M") + " WIB"
                except ValueError:
                    pass
            # Fallback ke teks: "21/04/2026 10:20"
            text = time_el.get_text().strip()
            if text:
                return text + " WIB"
        
        # Cara 2: Dari span.views-field-created
        date_span = soup.find('span', class_='views-field-created')
        if date_span:
            field_content = date_span.find('span', class_='field-content')
            if field_content:
                return field_content.get_text().strip()
        
    except Exception:
        pass
    
    return ""


def scrape_berita_jambilink(batas_halaman=50, ambil_tanggal_detail=True):
    """
    Scrape berita dari https://www.jambilink.id/indek
    
    Struktur halaman indek (Drupal views):
    - Tabel HTML: table.views-table > tbody > tr
    - Setiap tr berisi:
      - td.views-field-title:
        - <a href="/kategori">Kategori</a> | waktu relatif
        - <span class="judul"><a href="/post/...">Judul Berita</a></span>
        - <div class="bodyteks"><p>Deskripsi...</p></div>
    
    Pagination: ?page=0 (halaman 1), ?page=1 (halaman 2), dst.
    
    Parameter:
    - batas_halaman: Jumlah maksimal halaman yang akan di-scrape
    - ambil_tanggal_detail: Jika True, fetch halaman detail untuk mendapatkan 
                            tanggal absolut (lebih akurat tapi lebih lambat)
    """
    base_url = "https://www.jambilink.id/indek"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    berita_terkumpul = []
    halaman = 0  # Pagination dimulai dari 0
    
    print("Memulai ekstraksi berita dari JambiLink: Judul, Tanggal, Kategori, Link...\n")

    while halaman < batas_halaman:
        url = f"{base_url}?page={halaman}"
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
        except Exception as e:
            print(f"Koneksi gagal pada halaman {halaman + 1}: {e}")
            break

        if response.status_code != 200:
            print(f"Gagal mengakses halaman {halaman + 1}. Status code: {response.status_code}")
            break
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Cari tabel artikel
        table = soup.find('table', class_='views-table')
        if not table:
            print(f"Tabel tidak ditemukan di halaman {halaman + 1}. Berhenti.")
            break
        
        tbody = table.find('tbody')
        if not tbody:
            break
            
        rows = tbody.find_all('tr')
        if not rows:
            print(f"Tidak ada artikel di halaman {halaman + 1}. Berhenti.")
            break

        for row in rows:
            td = row.find('td', class_='views-field-title')
            if not td:
                continue
            
            # 1. Kategori: link pertama di dalam td
            first_a = td.find('a')
            if not first_a:
                continue
            kategori = first_a.get_text().strip()
            
            # 2. Waktu relatif: teks langsung di td setelah link kategori
            #    Format: "| 8 minutes ago"
            waktu_relatif = ""
            for child in td.children:
                if isinstance(child, str):
                    text = child.strip()
                    if text and text.startswith("|"):
                        waktu_relatif = text.lstrip("| ").strip()
                        break
            
            # 3. Judul & Link: span.judul > a
            span_judul = td.find('span', class_='judul')
            if not span_judul:
                continue
            a_judul = span_judul.find('a')
            if not a_judul:
                continue
            
            judul = a_judul.get_text().strip()
            link_path = a_judul.get('href', '')
            link = f"https://www.jambilink.id{link_path}" if link_path.startswith('/') else link_path
            
            # 4. Tanggal
            if ambil_tanggal_detail:
                # Fetch halaman detail untuk tanggal absolut
                tanggal_str_detail = fetch_tanggal_detail(link, headers)
                if tanggal_str_detail:
                    tanggal_str = tanggal_str_detail
                else:
                    # Fallback ke waktu relatif
                    _, tanggal_str = parse_tanggal_jambilink(waktu_relatif)
            else:
                # Konversi waktu relatif ke format tanggal
                _, tanggal_str = parse_tanggal_jambilink(waktu_relatif)
            
            berita_terkumpul.append({
                'Judul': judul,
                'Tanggal': tanggal_str,
                'Kategori': kategori,
                'Link': link
            })
            
        print(f"Halaman {halaman + 1} selesai diproses. Total sementara: {len(berita_terkumpul)} berita")
        
        # Cek apakah ada halaman berikutnya
        next_page = soup.find('li', class_='pager__item--next')
        if next_page and next_page.find('a'):
            halaman += 1
        else:
            break

    print("\nScraping selesai. Tidak ada halaman lagi atau batas telah tercapai.")

    return berita_terkumpul

if __name__ == "__main__":
    # Set ambil_tanggal_detail=False untuk scraping lebih cepat (tapi tanggal kurang akurat)
    data = scrape_berita_jambilink(batas_halaman=5, ambil_tanggal_detail=True)
    
    nama_file = 'semua_berita_jambilink.csv'
    
    if data:
        with open(nama_file, mode='w', newline='', encoding='utf-8') as file:
            fieldnames = ['Judul', 'Tanggal', 'Kategori', 'Link']
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            
            writer.writeheader()
            writer.writerows(data)
            
        print(f"\nBerhasil menyimpan {len(data)} berita ke dalam file '{nama_file}'.")
    else:
        print("\nTidak ada data berita yang ditemukan.")
