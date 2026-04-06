import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time

def parse_indonesian_date(date_str):
    """Konversi tanggal teks Indonesia ke objek datetime"""
    months = {
        'Januari': 1, 'Februari': 2, 'Maret': 3, 'April': 4, 'Mei': 5, 'Juni': 6,
        'Juli': 7, 'Agustus': 8, 'September': 9, 'Oktober': 10, 'November': 11, 'Desember': 12
    }
    try:
        parts = date_str.replace('WIB', '').strip().split()
        if len(parts) >= 3:
            day = int(parts[0])
            month = months.get(parts[1], 1)
            year = int(parts[2])
            return datetime(year, month, day)
    except:
        return None
    return None

def extract_news_data(soup, limit_date, source_label):
    """Fungsi ekstraksi data dengan format yang sama"""
    # Mencari blok berita berdasarkan gambar (media-body atau post-item)
    articles = soup.find_all('div', class_='media-body')
    
    found_count = 0
    for article in articles:
        title_tag = article.find('h3')
        if not title_tag: continue
        
        link_tag = title_tag.find('a')
        if not link_tag: continue
        
        title = link_tag.get_text(strip=True)
        link = link_tag['href']
        if not link.startswith('http'):
            link = "https://www.jambiupdate.co" + link
            
        desc_tag = article.find('p')
        description = desc_tag.get_text(strip=True) if desc_tag else "Tidak ada deskripsi."
        
        date_tag = article.find('div', class_='post-date') or article.find('span', class_='date')
        date_text = date_tag.get_text(strip=True) if date_tag else "Baru saja"
        
        # Validasi Tanggal (Filter 1 Bulan)
        news_date = parse_indonesian_date(date_text)
        if news_date and news_date < limit_date:
            continue

        print(f"[{source_label}]")
        print(f"Judul     : {title}")
        print(f"Tanggal   : {date_text}")
        print(f"Deskripsi : {description[:120]}...")
        print(f"Link      : {link}")
        print("-" * 50)
        found_count += 1
    
    return found_count

def scrape_full_jambi_update():
    base_url = "https://www.jambiupdate.co"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36'
    }
    limit_date = datetime.now() - timedelta(days=30)

    try:
        # --- BAGIAN 1: HALAMAN AWAL (UPDATE TERKINI) ---
        print(f"--- MENGAMBIL BERITA TERKINI DARI HALAMAN UTAMA ---")
        res_home = requests.get(base_url, headers=headers, timeout=10)
        soup_home = BeautifulSoup(res_home.text, 'html.parser')
        
        home_count = extract_news_data(soup_home, limit_date, "HOME / TERKINI")
        if home_count == 0:
            print("Tidak ditemukan berita baru di halaman utama.")

        # --- BAGIAN 2: BERDASARKAN KATEGORI ---
        print(f"\n--- MENGAMBIL BERITA DARI SETIAP KATEGORI ---")
        nav_menu = soup_home.find('ul', class_='navbar-nav') or soup_home.find('ul', class_='nav')
        
        if nav_menu:
            categories = []
            for link in nav_menu.find_all('a'):
                href = link.get('href')
                name = link.get_text(strip=True)
                if href and "/kategori/" in href:
                    full_url = href if href.startswith('http') else base_url + href
                    categories.append({'name': name, 'url': full_url})

            for cat in categories:
                time.sleep(1) # Jeda agar aman
                cat_res = requests.get(cat['url'], headers=headers, timeout=10)
                cat_soup = BeautifulSoup(cat_res.text, 'html.parser')
                extract_news_data(cat_soup, limit_date, f"KATEGORI: {cat['name']}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    scrape_full_jambi_update()