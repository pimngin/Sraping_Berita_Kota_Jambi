import cloudscraper
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from collections import defaultdict
import csv  # Menggunakan modul csv

def parse_indonesian_date(date_str):
    """Fungsi untuk mengubah string tanggal bahasa Indonesia menjadi objek datetime."""
    if not date_str:
        return None
        
    clean_str = date_str.replace(' WIB', '').replace(',', '').strip()
    
    bulan_map = {
        'Januari': 1, 'Februari': 2, 'Maret': 3, 'April': 4,
        'Mei': 5, 'Juni': 6, 'Juli': 7, 'Agustus': 8,
        'September': 9, 'Oktober': 10, 'November': 11, 'Desember': 12
    }
    
    try:
        parts = clean_str.split()
        if len(parts) >= 4:
            hari = int(parts[0])
            bulan = bulan_map.get(parts[1], 1)
            tahun = int(parts[2])
            waktu = parts[3].split(':')
            jam = int(waktu[0])
            menit = int(waktu[1])
            
            return datetime(tahun, bulan, hari, jam, menit)
    except Exception as e:
        print(f"Gagal parsing tanggal: '{date_str}' -> {e}")
    
    return None

def scrape_jambi_one_sebulan_terakhir():
    url = 'https://www.jambione.com/'
    
    print("Mencoba mengakses web Jambi One...")
    
    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'mobile': False
        }
    )
    
    try:
        response = scraper.get(url)
        
        if response.status_code != 200:
            print(f"Gagal mengakses web. Status code: {response.status_code}")
            return
            
        print("Berhasil mengakses web! Memulai ekstraksi data...\n")
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        batas_waktu = datetime.now() - timedelta(days=30)
        
        berita_per_kategori = defaultdict(list)
        
        daftar_berita = soup.find_all('div', class_='latest__item')
        
        if not daftar_berita:
             print("Peringatan: Tidak menemukan elemen berita. Mungkin struktur HTML web telah berubah.")
             return

        for item in daftar_berita:
            kategori_elem = item.select_one('.latest__subtitle a')
            kategori = kategori_elem.text.strip() if kategori_elem else 'Lainnya'
            
            judul_elem = item.select_one('.latest__title a')
            if not judul_elem:
                continue 
                
            judul = judul_elem.text.strip()
            link = judul_elem.get('href', '')
            
            tanggal_elem = item.select_one('.latest__date')
            tanggal_str = tanggal_elem.text.strip() if tanggal_elem else ''
            tanggal_obj = parse_indonesian_date(tanggal_str)
            
            deskripsi_elem = item.select_one('.latest__summary') 
            deskripsi = deskripsi_elem.text.strip() if deskripsi_elem else 'Tidak ada deskripsi singkat.'
            
            if tanggal_obj and tanggal_obj >= batas_waktu:
                data_berita = {
                    'judul': judul,
                    'link': link,
                    'tanggal': tanggal_str,
                    'deskripsi': deskripsi
                }
                berita_per_kategori[kategori].append(data_berita)

        # --- Menampilkan Output di Terminal ---
        total_berita = 0
        for kategori, berita_list in berita_per_kategori.items():
            total_berita += len(berita_list)
            
        print(f"Total berita berhasil dikumpulkan: {total_berita}")

        # --- Menyimpan Output ke File CSV ---
        if total_berita > 0:
            nama_file = 'berita_jambi.csv'
            
            # Tambahkan newline='' agar tidak ada baris kosong ekstra di Windows
            with open(nama_file, mode='w', newline='', encoding='utf-8') as file_csv:
                writer = csv.writer(file_csv)
                
                # Menulis Header (Baris Pertama CSV)
                writer.writerow(['Kategori', 'Judul', 'Tanggal', 'Deskripsi', 'Link'])
                
                # Menulis Data
                for kategori, berita_list in berita_per_kategori.items():
                    for berita in berita_list:
                        writer.writerow([
                            kategori, 
                            berita['judul'], 
                            berita['tanggal'], 
                            berita['deskripsi'], 
                            berita['link']
                        ])
                        
            print(f"\nData sukses diekspor ke dalam file: {nama_file}")
            print("Anda bisa membuka file tersebut menggunakan Microsoft Excel.")

    except Exception as e:
         print(f"Terjadi kesalahan saat menjalankan script: {e}")

# Menjalankan fungsi utama
if __name__ == "__main__":
    scrape_jambi_one_sebulan_terakhir()