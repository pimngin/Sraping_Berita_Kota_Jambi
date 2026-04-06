import requests
from bs4 import BeautifulSoup

def scrape_tribun_jambi(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    try:
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')

        # Mencari list berita berdasarkan class 'p2030' sesuai gambar Anda
        articles = soup.find_all('li', class_='p2030')

        print(f"--- Menampilkan Berita dari: {url} ---\n")

        if not articles:
            print("Data tidak ditemukan. Mencoba selektor alternatif...")
            # Alternatif jika class li berubah, mencari div pembungkus judul
            articles = soup.find_all('div', class_='fl mr15 pos_rel')

        for article in articles:
            # Berdasarkan gambar: Judul ada di h3 class 'f20 ln24 fbo'
            h3_tag = article.find('h3', class_='f20 ln24 fbo')
            
            if h3_tag:
                a_tag = h3_tag.find('a')
                if a_tag:
                    title = a_tag.get('title') or a_tag.get_text().strip()
                    link = a_tag.get('href')
                    
                    # Mengambil waktu dari tag <time>
                    time_tag = article.find('time', class_='grey pt5')
                    waktu = time_tag.get_text().strip() if time_tag else "Waktu tidak tersedia"

                    print(f"Judul : {title}")
                    print(f"Waktu : {waktu}")
                    print(f"Link  : {link}")
                    print("-" * 30)

    except Exception as e:
        print(f"Terjadi kesalahan: {e}")

# URL dari gambar Anda
url_target = "https://jambi.tribunnews.com/topic/berita-kota-jambi"
scrape_tribun_jambi(url_target)