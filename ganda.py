import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import requests
import cloudscraper
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import csv
import re
import time
from urllib.parse import quote_plus
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- KONFIGURASI ---
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}

BULAN_ID = {
    "januari": 1, "jan": 1, "februari": 2, "feb": 2, "maret": 3, "mar": 3,
    "april": 4, "apr": 4, "mei": 5, "juni": 6, "jun": 6, "juli": 7, "jul": 7,
    "agustus": 8, "agu": 8, "ags": 8, "september": 9, "sep": 9, "oktober": 10, "okt": 10,
    "november": 11, "nov": 11, "nop": 11, "desember": 12, "des": 12
}
HARI_ID = {"senin", "selasa", "rabu", "kamis", "jumat", "sabtu", "minggu"}

# Jumlah halaman yang diambil sekaligus per batch
BATCH_SIZE = 5

# --- FUNGSI UTILITAS ---

def clean_text(text):
    if not text:
        return "-"
    text = text.replace('\xa0', ' ')
    text = re.sub(r'\s+', ' ', text).strip()
    return text if text else "-"

def parse_general_date(date_str):
    if not date_str or date_str == "-":
        return None
    now = datetime.now()
    raw = str(date_str).lower().strip()
    raw = raw.replace('wib', '').replace('wit', '').replace('wita', '').replace(',', ' ').replace('-', ' ').strip()
    raw = re.sub(r'\s+', ' ', raw).strip()

    # Format relatif
    if "lalu" in raw or "baru" in raw:
        angka_match = re.search(r'(\d+)', raw)
        angka = int(angka_match.group(1)) if angka_match else 0
        if "detik" in raw: return now - timedelta(seconds=angka)
        elif "menit" in raw: return now - timedelta(minutes=angka)
        elif "jam" in raw: return now - timedelta(hours=angka)
        elif "hari" in raw: return now - timedelta(days=angka)
        elif "minggu" in raw: return now - timedelta(weeks=angka)
        elif "bulan" in raw: return now - timedelta(days=angka * 30)
        return now

    # Format absolut
    parts = raw.split()
    if parts and parts[0] in HARI_ID:
        parts = parts[1:]

    day, month, year = None, None, None
    hour, minute = 0, 0
    for i, part in enumerate(parts):
        if part in BULAN_ID:
            month = BULAN_ID[part]
            if i > 0 and parts[i - 1].isdigit(): day = int(parts[i - 1])
            if i < len(parts) - 1 and parts[i + 1].isdigit() and len(parts[i + 1]) == 4:
                year = int(parts[i + 1])
            if i < len(parts) - 2:
                tc = parts[i + 2] if len(parts) > i + 2 else ""
                if ':' in tc:
                    tp = tc.split(':')
                    try: hour, minute = int(tp[0]), int(tp[1]) if len(tp) > 1 else 0
                    except ValueError: pass
            break
    if day and month and year:
        try: return datetime(year, month, day, hour, minute)
        except ValueError: pass
    return None

def is_in_range(date_obj, start_date, end_date):
    if not date_obj: return False
    return start_date <= date_obj <= end_date

def is_older_than_start(date_obj, start_date):
    if not date_obj: return False
    return date_obj < start_date

def keyword_match(text, keywords):
    if not keywords: return True
    text_lower = text.lower()
    return all(kw.lower() in text_lower for kw in keywords)

def normalize_link(link):
    if not link: return ""
    link = link.split('#')[0].split('?')[0].rstrip('/')
    return link.lower()

def fetch_page(url, session=None, timeout=12):
    """Ambil satu halaman, return (url, response) atau (url, None) jika gagal."""
    try:
        if session:
            resp = session.get(url, timeout=timeout)
        else:
            resp = requests.get(url, headers=HEADERS, timeout=timeout)
        if resp.status_code == 200:
            return (url, resp)
    except:
        pass
    return (url, None)


# ============================================================
# SCRAPER 1: PEMKOT JAMBI (jambikota.go.id)
# ============================================================
def scrape_jambikota(start_date, end_date, keywords, status_callback):
    scraped_data = []
    seen = set()
    status_callback("[Pemkot Jambi] Memulai...")

    # Pertama ambil halaman 1 untuk tahu apakah masih ada data
    base = "https://jambikota.go.id/informasi/berita?page={}"
    max_pages = 80
    stop_all = False

    def process_page(html, page_num):
        nonlocal stop_all
        results = []
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select("#berita-container a.content-card")
        if not cards:
            return results, True  # no more pages

        should_stop = False
        for card in cards:
            title_el = card.select_one("h2.card-title")
            title = clean_text(title_el.get_text()) if title_el else "-"
            desc_el = card.select_one("p")
            desc = clean_text(desc_el.get_text()) if desc_el else "-"
            link = card.get("href", "")
            if link and not link.startswith("http"):
                link = "https://jambikota.go.id" + link
            date_el = card.select_one(".card-actions")
            date_text = clean_text(date_el.get_text()) if date_el else ""
            date_obj = parse_general_date(date_text)

            nl = normalize_link(link)
            if nl in seen:
                continue

            if is_in_range(date_obj, start_date, end_date):
                if keyword_match(f"{title} {desc}", keywords):
                    seen.add(nl)
                    results.append({"Sumber": "Pemkot Jambi", "Kategori": "Pemerintahan",
                                    "Judul": title, "Deskripsi": desc, "Tanggal": date_text, "Link": link})
            elif is_older_than_start(date_obj, start_date):
                should_stop = True
                break
        return results, should_stop

    page = 1
    while page <= max_pages and not stop_all:
        # Ambil BATCH_SIZE halaman sekaligus
        urls = [base.format(p) for p in range(page, min(page + BATCH_SIZE, max_pages + 1))]
        with ThreadPoolExecutor(max_workers=BATCH_SIZE) as executor:
            futures = {executor.submit(fetch_page, u): u for u in urls}
            page_results = {}
            for future in as_completed(futures):
                u, resp = future.result()
                page_results[u] = resp

        # Proses hasil secara berurutan (agar logika stop benar)
        for p in range(page, min(page + BATCH_SIZE, max_pages + 1)):
            u = base.format(p)
            resp = page_results.get(u)
            if not resp:
                stop_all = True
                break
            items, should_stop = process_page(resp.text, p)
            scraped_data.extend(items)
            if should_stop:
                stop_all = True
                break

        page += BATCH_SIZE
        status_callback(f"[Pemkot Jambi] {len(scraped_data)} berita... (hlm {page-1})")

    status_callback(f"[Pemkot Jambi] Selesai: {len(scraped_data)} berita.")
    return scraped_data


# ============================================================
# SCRAPER 2: TRIBUN JAMBI (jambi.tribunnews.com)
# ============================================================
def scrape_tribun_jambi(start_date, end_date, keywords, status_callback):
    scraped_data = []
    seen = set()
    status_callback("[Tribun Jambi] Memulai...")

    session = requests.Session()
    session.headers.update(HEADERS)

    base = "https://jambi.tribunnews.com/topic/berita-kota-jambi?page={}"
    max_pages = 50
    stop_all = False

    def process_page(html):
        nonlocal stop_all
        results = []
        soup = BeautifulSoup(html, 'html.parser')
        articles = soup.find_all('li', class_='p2030')
        if not articles:
            articles = soup.find_all('div', class_='fl mr15 pos_rel')
        if not articles:
            return results, True

        should_stop = False
        for article in articles:
            h3 = article.find('h3', class_='f20 ln24 fbo')
            if not h3: continue
            a = h3.find('a')
            if not a: continue
            title = clean_text(a.get('title') or a.get_text())
            link = a.get('href', '')
            time_tag = article.find('time', class_='grey pt5')
            date_text = clean_text(time_tag.get_text()) if time_tag else ""
            date_obj = parse_general_date(date_text)

            nl = normalize_link(link)
            if nl in seen: continue

            if is_in_range(date_obj, start_date, end_date):
                if keyword_match(title, keywords):
                    seen.add(nl)
                    results.append({"Sumber": "Tribun Jambi", "Kategori": "Berita Kota",
                                    "Judul": title, "Deskripsi": "-", "Tanggal": date_text, "Link": link})
            elif is_older_than_start(date_obj, start_date):
                should_stop = True
                break
        return results, should_stop

    page = 1
    while page <= max_pages and not stop_all:
        urls = [base.format(p) for p in range(page, min(page + BATCH_SIZE, max_pages + 1))]
        with ThreadPoolExecutor(max_workers=BATCH_SIZE) as executor:
            futures = {executor.submit(fetch_page, u, session): u for u in urls}
            page_results = {}
            for future in as_completed(futures):
                u, resp = future.result()
                page_results[u] = resp

        for p in range(page, min(page + BATCH_SIZE, max_pages + 1)):
            u = base.format(p)
            resp = page_results.get(u)
            if not resp:
                stop_all = True
                break
            items, should_stop = process_page(resp.text)
            scraped_data.extend(items)
            if should_stop:
                stop_all = True
                break

        page += BATCH_SIZE
        status_callback(f"[Tribun Jambi] {len(scraped_data)} berita... (hlm {page-1})")

    status_callback(f"[Tribun Jambi] Selesai: {len(scraped_data)} berita.")
    return scraped_data


# ============================================================
# SCRAPER 3: JAMBI UPDATE (jambiupdate.co)
# ============================================================
def scrape_jambi_update(start_date, end_date, keywords, status_callback):
    base_url = "https://www.jambiupdate.co"
    scraped_data = []
    seen = set()
    status_callback("[Jambi Update] Memulai...")

    def parse_date_from_url(url):
        m = re.search(r'/read/(\d{4})/(\d{2})/(\d{2})/', url)
        if m:
            try: return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            except: pass
        return None

    def extract_from_soup(soup, kategori_label):
        results = []
        # Cari semua link berita /read/YYYY/MM/DD/
        all_links = soup.find_all('a', href=re.compile(r'/read/\d{4}/\d{2}/\d{2}/'))
        processed = set()
        for a_tag in all_links:
            link = a_tag.get('href', '')
            if not link.startswith('http'):
                link = base_url + link
            nl = normalize_link(link)
            if nl in seen or nl in processed:
                continue
            processed.add(nl)

            title = clean_text(a_tag.get_text())
            if len(title) < 15:
                continue

            date_obj = parse_date_from_url(link)
            date_text = date_obj.strftime("%d %B %Y") if date_obj else "-"

            # Deskripsi: cari teks panjang di sekitar link
            desc = "-"
            parent = a_tag.find_parent()
            if parent:
                for sibling in parent.find_next_siblings():
                    t = clean_text(sibling.get_text())
                    if t and len(t) > 30 and t != title:
                        desc = t[:200]
                        break

            if date_obj and is_in_range(date_obj, start_date, end_date):
                if keyword_match(f"{title} {desc}", keywords):
                    seen.add(nl)
                    results.append({"Sumber": "Jambi Update", "Kategori": kategori_label,
                                    "Judul": title, "Deskripsi": desc, "Tanggal": date_text, "Link": link})
        return results

    try:
        # Ambil homepage
        resp = requests.get(base_url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            status_callback("[Jambi Update] Gagal akses homepage.")
            return scraped_data

        soup_home = BeautifulSoup(resp.text, 'html.parser')
        scraped_data.extend(extract_from_soup(soup_home, "Terkini"))

        # Kumpulkan semua URL kategori
        kategori_urls = []
        for a in soup_home.find_all('a', href=re.compile(r'/kategori/')):
            href = a.get('href', '')
            if not href.startswith('http'):
                href = base_url + href
            name = clean_text(a.get_text())
            if name and len(name) > 2 and href not in [k['url'] for k in kategori_urls]:
                kategori_urls.append({'name': name, 'url': href})

        # Juga tambah URL daerah
        for a in soup_home.find_all('a', href=re.compile(r'/daerah/')):
            href = a.get('href', '')
            if not href.startswith('http'):
                href = base_url + href
            name = clean_text(a.get_text())
            if name and len(name) > 2 and href not in [k['url'] for k in kategori_urls]:
                kategori_urls.append({'name': name, 'url': href})

        # Ambil SEMUA kategori sekaligus (paralel)
        if kategori_urls:
            status_callback(f"[Jambi Update] Mengambil {len(kategori_urls)} kategori sekaligus...")
            with ThreadPoolExecutor(max_workers=8) as executor:
                futures = {}
                for kat in kategori_urls:
                    futures[executor.submit(fetch_page, kat['url'])] = kat['name']

                for future in as_completed(futures):
                    kat_name = futures[future]
                    url, resp = future.result()
                    if resp:
                        s = BeautifulSoup(resp.text, 'html.parser')
                        items = extract_from_soup(s, kat_name)
                        scraped_data.extend(items)

        # Ambil juga halaman indeks (pagination berita terbaru)
        # jambiupdate.co/indeks biasanya punya halaman
        indeks_urls = [f"{base_url}/indeks?page={p}" for p in range(1, 6)]
        status_callback("[Jambi Update] Mengambil halaman indeks...")
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(fetch_page, u): u for u in indeks_urls}
            for future in as_completed(futures):
                u, resp = future.result()
                if resp:
                    s = BeautifulSoup(resp.text, 'html.parser')
                    items = extract_from_soup(s, "Indeks")
                    scraped_data.extend(items)

    except Exception as e:
        status_callback(f"[Jambi Update] Error: {str(e)[:60]}")

    status_callback(f"[Jambi Update] Selesai: {len(scraped_data)} berita.")
    return scraped_data


# ============================================================
# SCRAPER 4: JAMBI ONE (jambione.com)
# ============================================================
def scrape_jambi_one(start_date, end_date, keywords, status_callback):
    scraped_data = []
    seen = set()
    status_callback("[Jambi One] Memulai...")

    scraper = cloudscraper.create_scraper(
        browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False}
    )

    # Coba ambil halaman utama + beberapa sub-halaman
    urls_to_try = [
        ('https://www.jambione.com/', 'Terkini'),
        ('https://www.jambione.com/category/jambi/', 'Jambi'),
        ('https://www.jambione.com/category/nasional/', 'Nasional'),
        ('https://www.jambione.com/category/politik/', 'Politik'),
        ('https://www.jambione.com/category/hukum/', 'Hukum'),
        ('https://www.jambione.com/category/ekonomi/', 'Ekonomi'),
    ]

    def process_jambione(html, kategori_default):
        results = []
        soup = BeautifulSoup(html, 'html.parser')
        for item in soup.find_all('div', class_='latest__item'):
            kat_el = item.select_one('.latest__subtitle a')
            kategori = clean_text(kat_el.text) if kat_el else kategori_default
            judul_el = item.select_one('.latest__title a')
            if not judul_el: continue
            judul = clean_text(judul_el.text)
            link = judul_el.get('href', '')
            tgl_el = item.select_one('.latest__date')
            tgl_str = clean_text(tgl_el.text) if tgl_el else ''
            date_obj = parse_general_date(tgl_str)
            desc_el = item.select_one('.latest__summary')
            deskripsi = clean_text(desc_el.text) if desc_el else '-'

            nl = normalize_link(link)
            if nl in seen: continue

            if is_in_range(date_obj, start_date, end_date):
                if keyword_match(f"{judul} {deskripsi}", keywords):
                    seen.add(nl)
                    results.append({"Sumber": "Jambi One", "Kategori": kategori,
                                    "Judul": judul, "Deskripsi": deskripsi, "Tanggal": tgl_str, "Link": link})

        # Juga cari format artikel lain (article tag, post card, dsb)
        for article in soup.find_all(['article', 'div'], class_=re.compile(r'post|article|card')):
            a_tag = article.find('a', href=True)
            if not a_tag: continue
            title_tag = article.find(['h2', 'h3', 'h4'])
            if not title_tag: continue
            judul = clean_text(title_tag.get_text())
            if len(judul) < 10: continue
            link = a_tag.get('href', '')

            nl = normalize_link(link)
            if nl in seen: continue

            tgl_tag = article.find(['time', 'span'], class_=re.compile(r'date|time|meta'))
            tgl_str = clean_text(tgl_tag.get_text()) if tgl_tag else ''
            date_obj = parse_general_date(tgl_str)
            desc = '-'
            p_tag = article.find('p')
            if p_tag:
                desc = clean_text(p_tag.get_text())[:200]

            if is_in_range(date_obj, start_date, end_date):
                if keyword_match(f"{judul} {desc}", keywords):
                    seen.add(nl)
                    results.append({"Sumber": "Jambi One", "Kategori": kategori_default,
                                    "Judul": judul, "Deskripsi": desc, "Tanggal": tgl_str, "Link": link})
        return results

    # Ambil semua URL sekaligus menggunakan cloudscraper dalam thread pool
    def fetch_jambione(url_kat):
        url, kat = url_kat
        try:
            resp = scraper.get(url, timeout=20)
            if resp.status_code == 200:
                return (resp.text, kat)
        except:
            pass
        return (None, kat)

    # Karena cloudscraper tidak thread-safe secara penuh, kita fetch satu-satu tapi cepat
    for url, kat in urls_to_try:
        try:
            resp = scraper.get(url, timeout=20)
            if resp.status_code == 200:
                items = process_jambione(resp.text, kat)
                scraped_data.extend(items)
                status_callback(f"[Jambi One] {kat}: +{len(items)} berita")
        except Exception as e:
            status_callback(f"[Jambi One] Error {kat}: {str(e)[:40]}")

    status_callback(f"[Jambi One] Selesai: {len(scraped_data)} berita.")
    return scraped_data


# ============================================================
# SCRAPER 5: ANTARA NEWS JAMBI (jambi.antaranews.com)
# - Dengan keyword  → endpoint /search?q=keyword (pagination: /search/keyword/2)
# - Tanpa keyword   → endpoint /terkini (pagination: /terkini/2, /terkini/3, ...)
# - Selector artikel: article > header > h2|h3 > a (judul+link)
# - Kategori: header > p.simple-share > a
# - Tanggal:  header > p.simple-share > span
# ============================================================
def scrape_antara_jambi(start_date, end_date, keywords, status_callback):
    scraped_data = []
    seen = set()
    base_domain = "https://jambi.antaranews.com"

    use_search = bool(keywords)
    if use_search:
        query = " ".join(keywords)
        query_url = quote_plus(query)
        status_callback(f"[Antara News] Mencari '{query}'...")
    else:
        status_callback("[Antara News] Mengambil berita terkini...")

    max_pages = 50
    stop_all = False

    def make_url(page):
        if use_search:
            if page == 1:
                return f"{base_domain}/search?q={query_url}"
            return f"{base_domain}/search/{query_url}/{page}"
        else:
            if page == 1:
                return f"{base_domain}/terkini"
            return f"{base_domain}/terkini/{page}"

    def process_page(html):
        results = []
        should_stop = False
        soup = BeautifulSoup(html, 'html.parser')

        # Cari semua judul berita (biasanya di h2 atau h3 yang ada link ke /berita/)
        for h_tag in soup.find_all(['h2', 'h3']):
            a_tag = h_tag.find('a', href=re.compile(r'/berita/\d+/'))
            if not a_tag:
                continue

            judul = clean_text(a_tag.get_text())
            link = a_tag.get('href', '')
            if not link.startswith('http'):
                link = base_domain + link

            nl = normalize_link(link)
            if nl in seen:
                continue

            date_text = "-"
            deskripsi = "-"
            kategori = "Berita"

            # Ambil container utama untuk memudahkan pencarian tanggal & desc
            container = h_tag.find_parent('div', class_=re.compile(r'card__post__content|card__post_content|list-article'))
            if not container:
                container = h_tag.find_parent()

            if container:
                # Cari tanggal (biasanya di tag span, li, atau div di deket judul)
                for el in container.find_all(['span', 'li', 'time']):
                    txt = clean_text(el.get_text())
                    if txt and len(txt) < 80:
                        # Cek apakah ini text tanggal
                        if any(b in txt.lower() for b in list(BULAN_ID.keys())[:24]) or 'lalu' in txt.lower() or 'baru saja' in txt.lower():
                            date_text = txt
                            break

                # Cari deskripsi (paragraf yang teksnya lumayan panjang)
                for p_tag in container.find_all('p'):
                    txt = clean_text(p_tag.get_text())
                    if len(txt) > 20 and txt != judul:
                        deskripsi = txt[:200]
                        break

            date_obj = parse_general_date(date_text)

            if is_in_range(date_obj, start_date, end_date):
                gabungan = f"{judul} {deskripsi}"
                # Jika mode terkini, filter by keyword (jika tidak ada keyword otomatis True)
                if keyword_match(gabungan, keywords):
                    seen.add(nl)
                    results.append({
                        "Sumber": "Antara News Jambi",
                        "Kategori": kategori,
                        "Judul": judul,
                        "Deskripsi": deskripsi,
                        "Tanggal": date_text,
                        "Link": link
                    })
            elif is_older_than_start(date_obj, start_date):
                should_stop = True
                break

        return results, should_stop

    page = 1
    consecutive_empty = 0

    while page <= max_pages and not stop_all:
        # Ambil BATCH_SIZE halaman sekaligus
        urls = [(make_url(p), p) for p in range(page, min(page + BATCH_SIZE, max_pages + 1))]

        with ThreadPoolExecutor(max_workers=BATCH_SIZE) as executor:
            futures = {}
            for u, p in urls:
                futures[executor.submit(fetch_page, u)] = p
            page_results = {}
            for future in as_completed(futures):
                p = futures[future]
                url_result, resp = future.result()
                page_results[p] = resp

        # Proses berurutan (agar logika stop berdasarkan tanggal benar)
        for p in range(page, min(page + BATCH_SIZE, max_pages + 1)):
            resp = page_results.get(p)
            if not resp:
                stop_all = True
                break
            items, should_stop = process_page(resp.text)
            scraped_data.extend(items)
            if should_stop:
                stop_all = True
                break
            if not items:
                consecutive_empty += 1
                if consecutive_empty >= 3:
                    stop_all = True
                    break
            else:
                consecutive_empty = 0

        page += BATCH_SIZE
        mode_label = "search" if use_search else "terkini"
        status_callback(f"[Antara News] {len(scraped_data)} berita ({mode_label}, hlm {page-1})")

    status_callback(f"[Antara News] Selesai: {len(scraped_data)} berita.")
    return scraped_data


# ============================================================
# GUI APPLICATION
# ============================================================
class AplikasiScraper:
    def __init__(self, root):
        self.root = root
        self.root.title("Scraper Berita Jambi - Pencarian Cepat & Detail")
        self.root.geometry("1200x720")
        self.root.configure(padx=10, pady=10)
        self.root.minsize(900, 600)

        self.semua_berita = []
        self.berita_tampil = []

        # --- JUDUL ---
        f = tk.Frame(self.root); f.pack(fill=tk.X, pady=(0, 8))
        tk.Label(f, text="Portal Berita Jambi - Scraper Cepat", font=("Arial", 16, "bold")).pack(side=tk.LEFT)

        # --- KATA KUNCI ---
        f = tk.Frame(self.root); f.pack(fill=tk.X, pady=(0, 5))
        tk.Label(f, text="Kata Kunci:", font=("Arial", 10, "bold")).pack(side=tk.LEFT)
        self.entry_keyword = tk.Entry(f, width=45, font=("Arial", 11))
        self.entry_keyword.pack(side=tk.LEFT, padx=(8, 5))
        tk.Label(f, text="(contoh: banjir, pembangunan jalan)", fg="gray", font=("Arial", 9)).pack(side=tk.LEFT)

        # --- WAKTU ---
        f = tk.Frame(self.root); f.pack(fill=tk.X, pady=(3, 5))
        sekarang = datetime.now()
        awal_bulan = sekarang.replace(day=1)
        hari_list = [str(i) for i in range(1, 32)]
        bulan_list = [str(i) for i in range(1, 13)]
        tahun_list = [str(i) for i in range(2020, sekarang.year + 2)]

        tk.Label(f, text="Dari:", font=("Arial", 9, "bold")).pack(side=tk.LEFT)
        self.cb_d_hari = ttk.Combobox(f, values=hari_list, width=3, state="readonly"); self.cb_d_hari.set(str(awal_bulan.day)); self.cb_d_hari.pack(side=tk.LEFT, padx=2)
        self.cb_d_bulan = ttk.Combobox(f, values=bulan_list, width=3, state="readonly"); self.cb_d_bulan.set(str(awal_bulan.month)); self.cb_d_bulan.pack(side=tk.LEFT, padx=2)
        self.cb_d_tahun = ttk.Combobox(f, values=tahun_list, width=5, state="readonly"); self.cb_d_tahun.set(str(awal_bulan.year)); self.cb_d_tahun.pack(side=tk.LEFT, padx=(2, 15))

        tk.Label(f, text="Sampai:", font=("Arial", 9, "bold")).pack(side=tk.LEFT)
        self.cb_s_hari = ttk.Combobox(f, values=hari_list, width=3, state="readonly"); self.cb_s_hari.set(str(sekarang.day)); self.cb_s_hari.pack(side=tk.LEFT, padx=2)
        self.cb_s_bulan = ttk.Combobox(f, values=bulan_list, width=3, state="readonly"); self.cb_s_bulan.set(str(sekarang.month)); self.cb_s_bulan.pack(side=tk.LEFT, padx=2)
        self.cb_s_tahun = ttk.Combobox(f, values=tahun_list, width=5, state="readonly"); self.cb_s_tahun.set(str(sekarang.year)); self.cb_s_tahun.pack(side=tk.LEFT, padx=(2, 15))

        self.btn_scrape = tk.Button(f, text="Mulai Cari Berita", bg="#4CAF50", fg="white",
                                    font=("Arial", 10, "bold"), command=self.mulai_scraping, padx=15)
        self.btn_scrape.pack(side=tk.LEFT, padx=10)

        # --- SUMBER ---
        f = tk.Frame(self.root); f.pack(fill=tk.X, pady=(0, 5))
        tk.Label(f, text="Sumber:", font=("Arial", 9, "bold")).pack(side=tk.LEFT)
        self.var_pemkot = tk.BooleanVar(value=True)
        self.var_tribun = tk.BooleanVar(value=True)
        self.var_jambupdate = tk.BooleanVar(value=True)
        self.var_jambione = tk.BooleanVar(value=True)
        self.var_antara = tk.BooleanVar(value=True)
        tk.Checkbutton(f, text="Pemkot Jambi", variable=self.var_pemkot).pack(side=tk.LEFT, padx=5)
        tk.Checkbutton(f, text="Tribun Jambi", variable=self.var_tribun).pack(side=tk.LEFT, padx=5)
        tk.Checkbutton(f, text="Jambi Update", variable=self.var_jambupdate).pack(side=tk.LEFT, padx=5)
        tk.Checkbutton(f, text="Jambi One", variable=self.var_jambione).pack(side=tk.LEFT, padx=5)
        tk.Checkbutton(f, text="Antara News", variable=self.var_antara).pack(side=tk.LEFT, padx=5)
        self.lbl_status = tk.Label(f, text="Status: Menunggu...", fg="blue", font=("Arial", 9))
        self.lbl_status.pack(side=tk.RIGHT, padx=5)

        # --- FILTER & EXPORT ---
        f = tk.Frame(self.root); f.pack(fill=tk.X, pady=(0, 5))
        tk.Label(f, text="Filter Tabel:").pack(side=tk.LEFT)
        self.entry_cari = tk.Entry(f, width=35)
        self.entry_cari.pack(side=tk.LEFT, padx=5)
        self.entry_cari.bind("<KeyRelease>", self.cari_data)
        self.lbl_total = tk.Label(f, text="Total: 0 berita", font=("Arial", 9, "bold"), fg="#333")
        self.lbl_total.pack(side=tk.LEFT, padx=15)
        self.btn_export = tk.Button(f, text="Export CSV", bg="#2196F3", fg="white",
                                    font=("Arial", 9, "bold"), command=self.export_csv)
        self.btn_export.pack(side=tk.RIGHT)

        # --- TABEL ---
        f = tk.Frame(self.root); f.pack(fill=tk.BOTH, expand=True)
        kolom = ("Sumber", "Kategori", "Judul", "Deskripsi", "Tanggal", "Link")
        self.tree = ttk.Treeview(f, columns=kolom, show="headings")
        widths = {"Sumber": 120, "Kategori": 100, "Judul": 320, "Deskripsi": 250, "Tanggal": 120, "Link": 200}
        for col in kolom:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=widths[col], anchor=tk.W)
        sy = ttk.Scrollbar(f, orient=tk.VERTICAL, command=self.tree.yview)
        sx = ttk.Scrollbar(f, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
        sy.pack(side=tk.RIGHT, fill=tk.Y)
        sx.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def update_status(self, pesan):
        self.root.after(0, lambda: self.lbl_status.config(text=f"Status: {pesan}"))

    def mulai_scraping(self):
        keyword_text = self.entry_keyword.get().strip()
        keywords = keyword_text.split() if keyword_text else []
        if not keywords:
            if not messagebox.askyesno("Tanpa Kata Kunci",
                "Tidak ada kata kunci.\nAmbil SEMUA berita dalam rentang waktu?"):
                return
        try:
            start_date = datetime(int(self.cb_d_tahun.get()), int(self.cb_d_bulan.get()), int(self.cb_d_hari.get()))
            end_date = datetime(int(self.cb_s_tahun.get()), int(self.cb_s_bulan.get()), int(self.cb_s_hari.get()), 23, 59, 59)
            if start_date > end_date:
                messagebox.showerror("Error", "'Dari' harus sebelum 'Sampai'!")
                return
        except ValueError:
            messagebox.showerror("Error", "Tanggal tidak valid!")
            return

        self.btn_scrape.config(state=tk.DISABLED, text="Sedang Mencari...")
        self.semua_berita.clear()
        self.tree.delete(*self.tree.get_children())
        self.lbl_total.config(text="Total: 0 berita")
        threading.Thread(target=self.proses_scraping, args=(start_date, end_date, keywords), daemon=True).start()

    def proses_scraping(self, start_date, end_date, keywords):
        kw = f"'{' '.join(keywords)}'" if keywords else "semua"
        self.update_status(f"Mencari {kw}...")

        threads = []
        results = {}
        lock = threading.Lock()

        def run(name, func):
            try:
                data = func(start_date, end_date, keywords, self.update_status)
                with lock: results[name] = data
            except Exception as e:
                self.update_status(f"Error {name}: {str(e)[:50]}")
                with lock: results[name] = []

        scraper_map = {
            "pemkot": (self.var_pemkot, scrape_jambikota),
            "tribun": (self.var_tribun, scrape_tribun_jambi),
            "jambupdate": (self.var_jambupdate, scrape_jambi_update),
            "jambione": (self.var_jambione, scrape_jambi_one),
            "antara": (self.var_antara, scrape_antara_jambi),
        }
        for name, (var, func) in scraper_map.items():
            if var.get():
                t = threading.Thread(target=run, args=(name, func), daemon=True)
                threads.append(t); t.start()
        for t in threads:
            t.join()

        # DEDUP GLOBAL
        all_data = []
        global_seen = set()
        for data in results.values():
            for item in data:
                nl = normalize_link(item.get("Link", ""))
                if nl and nl not in global_seen:
                    global_seen.add(nl)
                    all_data.append(item)

        self.semua_berita = all_data
        self.berita_tampil = self.semua_berita.copy()
        self.root.after(0, self.tampilkan_data)
        self.update_status(f"Selesai! {len(self.semua_berita)} berita untuk {kw}.")
        self.root.after(0, lambda: self.btn_scrape.config(state=tk.NORMAL, text="Mulai Cari Berita"))

    def tampilkan_data(self):
        self.tree.delete(*self.tree.get_children())
        for item in self.berita_tampil:
            self.tree.insert("", tk.END, values=(
                item["Sumber"], item["Kategori"], item["Judul"],
                item["Deskripsi"], item["Tanggal"], item["Link"]))
        self.lbl_total.config(text=f"Total: {len(self.berita_tampil)} berita")

    def cari_data(self, event=None):
        q = self.entry_cari.get().lower().strip()
        if not q:
            self.berita_tampil = self.semua_berita.copy()
        else:
            kws = q.split()
            self.berita_tampil = [b for b in self.semua_berita
                                  if all(k in " ".join(str(v) for v in b.values()).lower() for k in kws)]
        self.tampilkan_data()

    def export_csv(self):
        if not self.berita_tampil:
            messagebox.showwarning("Perhatian", "Tidak ada data!")
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")],
            initialfile=f"Berita_Jambi_{datetime.now().strftime('%d_%m_%Y')}.csv")
        if path:
            try:
                with open(path, "w", newline="", encoding="utf-8-sig") as f:
                    w = csv.DictWriter(f, fieldnames=["Sumber", "Kategori", "Judul", "Deskripsi", "Tanggal", "Link"])
                    w.writeheader(); w.writerows(self.berita_tampil)
                messagebox.showinfo("Sukses", f"Tersimpan:\n{path}")
            except Exception as e:
                messagebox.showerror("Error", f"Gagal:\n{e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = AplikasiScraper(root)
    root.mainloop()