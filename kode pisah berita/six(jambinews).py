import requests
from bs4 import BeautifulSoup
import csv

def scrape_berita_jambinews(batas_halaman=50):
    url = "https://www.jambinews.id/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    berita_terkumpul = []
    halaman = 1
    
    print("Memulai ekstraksi berita dari Jambi News: Judul, Tanggal, Kategori, Link...\n")

    while url and halaman <= batas_halaman:
        try:
            response = requests.get(url, headers=headers, timeout=10)
        except Exception as e:
            print(f"Koneksi gagal pada halaman {halaman}: {e}")
            break

        if response.status_code != 200:
            print(f"Gagal mengakses halaman {halaman}. Status code: {response.status_code}")
            break
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        articles = soup.find_all('div', class_='blog-post hentry index-post')
        
        if not articles:
            break

        for article in articles:
            h2_tag = article.find('h2', class_='post-title')
            
            if not h2_tag or not h2_tag.find('a'):
                continue
                
            # 1. Judul & Link
            a_tag = h2_tag.find('a')
            judul = a_tag.text.strip()
            link = a_tag['href']
            
            # 2. Kategori
            tag_span = article.find('span', class_='post-tag')
            kategori = tag_span.text.strip() if tag_span else "Umum"
                
            # 3. Tanggal
            date_span = article.find('span', class_='post-date')
            tanggal_str = date_span.text.strip() if date_span else ""
            
            berita_terkumpul.append({
                'Judul': judul,
                'Tanggal': tanggal_str,
                'Kategori': kategori,
                'Link': link
            })
            
        print(f"Halaman {halaman} selesai diproses. Total sementara: {len(berita_terkumpul)} berita")
        
        # Cek apakah ada tombol "Postingan Lama" atau Next Page
        next_page = soup.find('a', class_='blog-pager-older-link')
        if next_page and next_page.get('href'):
            url = next_page['href']
            halaman += 1
        else:
            url = None

    print("\nScraping selesai. Tidak ada halaman lagi atau batas telah tercapai.")

    return berita_terkumpul

if __name__ == "__main__":
    data = scrape_berita_jambinews(batas_halaman=10) # Set batas misal 10 halaman
    
    nama_file = 'semua_berita_jambinews.csv'
    
    if data:
        with open(nama_file, mode='w', newline='', encoding='utf-8') as file:
            fieldnames = ['Judul', 'Tanggal', 'Kategori', 'Link']
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            
            writer.writeheader()
            writer.writerows(data)
            
        print(f"\nBerhasil menyimpan {len(data)} berita ke dalam file '{nama_file}'.")
    else:
        print("\nTidak ada data berita yang ditemukan.")
