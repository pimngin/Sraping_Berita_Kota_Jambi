import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
import csv

def parse_tanggal_indonesia(tanggal_str):
    """
    Mengubah string tanggal Indonesia (termasuk format relatif 'jam lalu') 
    menjadi objek datetime.
    """
    tanggal_str = tanggal_str.lower().strip()
    now = datetime.now()
    
    # Menangani format waktu relatif (misal: "4 jam lalu", "30 menit lalu")
    if 'lalu' in tanggal_str:
        match = re.search(r'(\d+)\s+(menit|jam|hari)', tanggal_str)
        if match:
            angka = int(match.group(1))
            satuan = match.group(2)
            if satuan == 'menit':
                return now - timedelta(minutes=angka)
            elif satuan == 'jam':
                return now - timedelta(hours=angka)
            elif satuan == 'hari':
                return now - timedelta(days=angka)
        return now

    # Menangani format tanggal absolut (misal: "Selasa, 10 Februari 2026")
    bulan_map = {
        'januari': 1, 'februari': 2, 'maret': 3, 'april': 4,
        'mei': 5, 'juni': 6, 'juli': 7, 'agustus': 8,
        'september': 9, 'oktober': 10, 'november': 11, 'desember': 12
    }
    
    if ',' in tanggal_str:
        tanggal_str = tanggal_str.split(',')[1].strip()
        
    match = re.search(r'(\d+)\s+([a-z]+)\s+(\d{4})', tanggal_str)
    if match:
        hari = int(match.group(1))
        bulan_str = match.group(2)
        tahun = int(match.group(3))
        bulan = bulan_map.get(bulan_str, 1)
        return datetime(tahun, bulan, hari)
    
    return now 

def scrape_berita_jambi():
    base_url = "https://jambi.antaranews.com/terkini"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    berita_terkumpul = []
    halaman = 1
    lanjut_scraping = True
    
    print("Memulai ekstraksi SEMUA berita: Judul, Tanggal, Kategori, Link...\n")

    while lanjut_scraping:
        url = base_url if halaman == 1 else f"{base_url}/{halaman}"
        
        try:
            response = requests.get(url, headers=headers)
        except Exception as e:
            print(f"Koneksi gagal pada halaman {halaman}: {e}")
            break

        if response.status_code != 200:
            break
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Sesuai screenshot, list artikel dibungkus tag article
        articles = soup.find_all('article')
        
        if not articles:
            break

        for article in articles:
            header = article.find('header')
            if not header:
                continue
                
            # 1. Judul & Link
            h3_tag = header.find(['h2', 'h3'])
            if not h3_tag or not h3_tag.find('a'):
                continue
                
            a_tag = h3_tag.find('a')
            judul = a_tag.text.strip()
            link = a_tag['href']
            
            # 2. Kategori & Tanggal (berada di dalam <p class="simple-share">)
            share_p = header.find('p', class_='simple-share')
            kategori = "Umum" # Default fallback
            tanggal_str = ""
            
            if share_p:
                # Kategori biasanya ada di tag <a> pertama dalam share_p
                a_kategori = share_p.find('a')
                if a_kategori:
                    kategori = a_kategori.text.strip()
                    
                # Tanggal ada di dalam tag <span>
                span_date = share_p.find('span')
                if span_date:
                    tanggal_str = span_date.text.strip()
            
            berita_terkumpul.append({
                'Judul': judul,
                'Tanggal': tanggal_str,
                'Kategori': kategori,
                'Link': link
            })
            
        print(f"Halaman {halaman} selesai diproses. Total: {len(berita_terkumpul)} berita")
        halaman += 1

    print("\nScraping selesai. Tidak ada halaman lagi atau batas telah tercapai.")

    return berita_terkumpul

if __name__ == "__main__":
    data = scrape_berita_jambi()
    
    nama_file = 'semua_berita_antaranews_jambi.csv'
    
    if data:
        with open(nama_file, mode='w', newline='', encoding='utf-8') as file:
            # Sesuaikan fieldnames dengan data yang diekstrak
            fieldnames = ['Judul', 'Tanggal', 'Kategori', 'Link']
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            
            writer.writeheader()
            writer.writerows(data)
            
        print(f"\nBerhasil menyimpan {len(data)} berita ke dalam file '{nama_file}'.")
    else:
        print("\nTidak ada data berita yang ditemukan pada rentang waktu dan halaman tersebut.")