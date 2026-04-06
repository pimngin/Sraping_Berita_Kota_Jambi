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

# --- KONFIGURASI & FUNGSI UTILITAS SCRAPER ---
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept-Language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7'
}

BULAN_ID = {
    "januari": 1, "jan": 1, "februari": 2, "feb": 2, "maret": 3, "mar": 3,
    "april": 4, "apr": 4, "mei": 5, "juni": 6, "jun": 6, "juli": 7, "jul": 7,
    "agustus": 8, "agu": 8, "september": 9, "sep": 9, "oktober": 10, "okt": 10,
    "november": 11, "nov": 11, "desember": 12, "des": 12
}

def clean_text(text):
    if not text: return "-"
    return re.sub(r'\s+', ' ', text).strip()

def parse_general_date(date_str):
    now = datetime.now()
    date_str = str(date_str).lower().strip().replace('wib', '').replace(',', '')
    if "lalu" in date_str or "baru" in date_str:
        try:
            angka = int(re.search(r'\d+', date_str).group()) if re.search(r'\d+', date_str) else 0
            if "jam" in date_str: return now - timedelta(hours=angka)
            elif "menit" in date_str: return now - timedelta(minutes=angka)
            elif "hari" in date_str: return now - timedelta(days=angka)
            elif "detik" in date_str: return now - timedelta(seconds=angka)
        except: return now
        return now
    try:
        parts = date_str.split()
        day, month, year = None, None, None
        for i, part in enumerate(parts):
            if part in BULAN_ID:
                month = BULAN_ID[part]
                if i > 0 and parts[i-1].isdigit(): day = int(parts[i-1])
                if i < len(parts)-1 and parts[i+1].isdigit(): year = int(parts[i+1])
                break
        if day and month and year: return datetime(year, month, day)
    except: pass
    return None

def is_in_range(date_obj, start_date, end_date):
    """Mengecek apakah tanggal berita berada di dalam rentang waktu yang diminta."""
    if not date_obj: return False
    return start_date <= date_obj <= end_date

def is_older_than_start(date_obj, start_date):
    """Mengecek apakah tanggal berita lebih tua dari batas 'Dari Tanggal' untuk stop scraping."""
    if not date_obj: return False
    return date_obj < start_date

# --- FUNGSI SCRAPER ---
def scrape_jambikota(start_date, end_date, status_callback):
    base_url = "https://jambikota.go.id/informasi/berita"
    page = 1
    scraped_data = []
    status_callback("Memulai Scraping Pemkot Jambi...")
    while True:
        try:
            response = requests.get(f"{base_url}?page={page}", headers=HEADERS, timeout=10)
            if response.status_code != 200: break
            soup = BeautifulSoup(response.text, "html.parser")
            cards = soup.select("#berita-container a.content-card")
            if not cards: break
            stop_scraping = False
            for card in cards:
                title = clean_text(card.select_one("h2.card-title").get_text() if card.select_one("h2.card-title") else "")
                desc = clean_text(card.select_one("p").get_text() if card.select_one("p") else "")
                link = card.get("href")
                date_element = card.select_one(".card-actions")
                date_text = clean_text(date_element.get_text() if date_element else "")
                date_obj = parse_general_date(date_text)
                
                if is_in_range(date_obj, start_date, end_date):
                    scraped_data.append({"Sumber": "Pemkot Jambi", "Kategori": "Pemerintahan", "Judul": title, "Deskripsi": desc, "Tanggal": date_text, "Link": link})
                elif is_older_than_start(date_obj, start_date):
                    stop_scraping = True
                    break
            if stop_scraping: break
            page += 1
            time.sleep(1)
        except: break
    return scraped_data

def scrape_tribun_jambi(start_date, end_date, status_callback):
    url_base = "https://jambi.tribunnews.com/topic/berita-kota-jambi"
    scraped_data = []
    page = 1
    status_callback("Memulai Scraping Tribun Jambi...")
    while True:
        try:
            response = requests.get(f"{url_base}?page={page}", headers=HEADERS, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            articles = soup.find_all('li', class_='p2030') or soup.find_all('div', class_='fl mr15 pos_rel')
            if not articles: break 
            stop_scraping = False
            for article in articles:
                h3_tag = article.find('h3', class_='f20 ln24 fbo')
                if not h3_tag or not h3_tag.find('a'): continue
                a_tag = h3_tag.find('a')
                title = clean_text(a_tag.get('title') or a_tag.get_text())
                link = a_tag.get('href')
                time_tag = article.find('time', class_='grey pt5')
                date_text = clean_text(time_tag.get_text() if time_tag else "")
                date_obj = parse_general_date(date_text)
                
                if is_in_range(date_obj, start_date, end_date):
                    scraped_data.append({"Sumber": "Tribun Jambi", "Kategori": "Berita Kota", "Judul": title, "Deskripsi": "-", "Tanggal": date_text, "Link": link})
                elif is_older_than_start(date_obj, start_date):
                    stop_scraping = True
                    break
            if stop_scraping: break
            page += 1
            time.sleep(1)
        except: break
    return scraped_data

def scrape_jambi_update(start_date, end_date, status_callback):
    base_url = "https://www.jambiupdate.co"
    scraped_data = []
    status_callback("Memulai Scraping Jambi Update...")
    def extract_cards(soup, source_category):
        for article in soup.find_all('div', class_='media-body'):
            title_tag = article.find('h3')
            if not title_tag or not title_tag.find('a'): continue
            link_tag = title_tag.find('a')
            title = clean_text(link_tag.get_text())
            link = link_tag['href']
            if not link.startswith('http'): link = base_url + link
            desc_tag = article.find('p')
            description = clean_text(desc_tag.get_text() if desc_tag else "-")
            date_tag = article.find('div', class_='post-date') or article.find('span', class_='date')
            date_text = clean_text(date_tag.get_text() if date_tag else "Baru saja")
            date_obj = parse_general_date(date_text)
            
            if is_in_range(date_obj, start_date, end_date):
                if not any(d['Link'] == link for d in scraped_data):
                    scraped_data.append({"Sumber": "Jambi Update", "Kategori": source_category, "Judul": title, "Deskripsi": description, "Tanggal": date_text, "Link": link})
    try:
        res_home = requests.get(base_url, headers=HEADERS, timeout=10)
        soup_home = BeautifulSoup(res_home.text, 'html.parser')
        extract_cards(soup_home, "Terkini")
    except: pass
    return scraped_data

def scrape_jambi_one(start_date, end_date, status_callback):
    url = 'https://www.jambione.com/'
    scraped_data = []
    status_callback("Memulai Scraping Jambi One...")
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False})
    try:
        response = scraper.get(url, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        for item in soup.find_all('div', class_='latest__item'):
            kategori_elem = item.select_one('.latest__subtitle a')
            kategori = clean_text(kategori_elem.text) if kategori_elem else 'Lainnya'
            judul_elem = item.select_one('.latest__title a')
            if not judul_elem: continue 
            judul = clean_text(judul_elem.text)
            link = judul_elem.get('href', '')
            tanggal_elem = item.select_one('.latest__date')
            tanggal_str = clean_text(tanggal_elem.text) if tanggal_elem else ''
            date_obj = parse_general_date(tanggal_str)
            deskripsi_elem = item.select_one('.latest__summary') 
            deskripsi = clean_text(deskripsi_elem.text) if deskripsi_elem else '-'
            
            if is_in_range(date_obj, start_date, end_date):
                scraped_data.append({"Sumber": "Jambi One", "Kategori": kategori, "Judul": judul, "Deskripsi": deskripsi, "Tanggal": tanggal_str, "Link": link})
    except: pass
    return scraped_data

# --- GUI APPLICATION ---
class AplikasiScraper:
    def __init__(self, root):
        self.root = root
        self.root.title("Scraper Berita Jambi Real-Time")
        self.root.geometry("1100x650")
        self.root.configure(padx=10, pady=10)
        
        self.semua_berita = []
        self.berita_tampil = []

        # --- FRAME ATAS (Judul) ---
        frame_judul = tk.Frame(self.root)
        frame_judul.pack(fill=tk.X, pady=(0, 10))
        tk.Label(frame_judul, text="Portal Berita Jambi Scraper", font=("Arial", 16, "bold")).pack(side=tk.LEFT)

        # --- FRAME FILTER WAKTU & KONTROL ---
        frame_waktu = tk.Frame(self.root)
        frame_waktu.pack(fill=tk.X, pady=(0, 10))

        sekarang = datetime.now()
        bulan_lalu = sekarang.replace(day=1) # Default: Dari awal bulan ini

        hari_list = [str(i) for i in range(1, 32)]
        bulan_list = [str(i) for i in range(1, 13)]
        tahun_list = [str(i) for i in range(2020, sekarang.year + 2)]

        # --- Bagian "DARI" ---
        tk.Label(frame_waktu, text="Dari:", font=("Arial", 9, "bold")).pack(side=tk.LEFT)
        self.cb_d_hari = ttk.Combobox(frame_waktu, values=hari_list, width=3, state="readonly")
        self.cb_d_hari.set(str(bulan_lalu.day))
        self.cb_d_hari.pack(side=tk.LEFT, padx=2)
        
        self.cb_d_bulan = ttk.Combobox(frame_waktu, values=bulan_list, width=3, state="readonly")
        self.cb_d_bulan.set(str(bulan_lalu.month))
        self.cb_d_bulan.pack(side=tk.LEFT, padx=2)
        
        self.cb_d_tahun = ttk.Combobox(frame_waktu, values=tahun_list, width=5, state="readonly")
        self.cb_d_tahun.set(str(bulan_lalu.year))
        self.cb_d_tahun.pack(side=tk.LEFT, padx=(2, 15))

        # --- Bagian "SAMPAI" ---
        tk.Label(frame_waktu, text="Sampai:", font=("Arial", 9, "bold")).pack(side=tk.LEFT)
        self.cb_s_hari = ttk.Combobox(frame_waktu, values=hari_list, width=3, state="readonly")
        self.cb_s_hari.set(str(sekarang.day))
        self.cb_s_hari.pack(side=tk.LEFT, padx=2)
        
        self.cb_s_bulan = ttk.Combobox(frame_waktu, values=bulan_list, width=3, state="readonly")
        self.cb_s_bulan.set(str(sekarang.month))
        self.cb_s_bulan.pack(side=tk.LEFT, padx=2)
        
        self.cb_s_tahun = ttk.Combobox(frame_waktu, values=tahun_list, width=5, state="readonly")
        self.cb_s_tahun.set(str(sekarang.year))
        self.cb_s_tahun.pack(side=tk.LEFT, padx=(2, 15))

        # Tombol Mulai Scraping
        self.btn_scrape = tk.Button(frame_waktu, text="Mulai Scraping", bg="#4CAF50", fg="white", font=("Arial", 9, "bold"), command=self.mulai_scraping)
        self.btn_scrape.pack(side=tk.LEFT, padx=10)

        # Status
        self.lbl_status = tk.Label(frame_waktu, text="Status: Menunggu instruksi...", fg="blue")
        self.lbl_status.pack(side=tk.RIGHT, padx=5)

        # --- FRAME TENGAH (Pencarian & Export) ---
        frame_tengah = tk.Frame(self.root)
        frame_tengah.pack(fill=tk.X, pady=(0, 10))

        tk.Label(frame_tengah, text="Cari (Dipisahkan spasi):").pack(side=tk.LEFT)
        self.entry_cari = tk.Entry(frame_tengah, width=50)
        self.entry_cari.pack(side=tk.LEFT, padx=5)
        self.entry_cari.bind("<KeyRelease>", self.cari_data)

        self.btn_export = tk.Button(frame_tengah, text="Export CSV", bg="#2196F3", fg="white", font=("Arial", 9, "bold"), command=self.export_csv)
        self.btn_export.pack(side=tk.RIGHT)

        # --- FRAME BAWAH (Tabel Data) ---
        frame_bawah = tk.Frame(self.root)
        frame_bawah.pack(fill=tk.BOTH, expand=True)

        kolom = ("Sumber", "Kategori", "Judul", "Deskripsi", "Tanggal", "Link")
        self.tree = ttk.Treeview(frame_bawah, columns=kolom, show="headings")
        
        for col in kolom:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120, anchor=tk.W)
        self.tree.column("Deskripsi", width=250)
        self.tree.column("Judul", width=300)

        scrollbar_y = ttk.Scrollbar(frame_bawah, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar_x = ttk.Scrollbar(frame_bawah, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)

        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def update_status(self, pesan):
        self.root.after(0, lambda: self.lbl_status.config(text=f"Status: {pesan}"))

    def mulai_scraping(self):
        # Validasi Tanggal
        try:
            start_date = datetime(int(self.cb_d_tahun.get()), int(self.cb_d_bulan.get()), int(self.cb_d_hari.get()))
            # End date diset ke 23:59:59 pada hari tersebut agar berita di hari "sampai" tetap masuk
            end_date = datetime(int(self.cb_s_tahun.get()), int(self.cb_s_bulan.get()), int(self.cb_s_hari.get()), 23, 59, 59)
            
            if start_date > end_date:
                messagebox.showerror("Error Waktu", "'Dari Tanggal' tidak boleh lebih baru dari 'Sampai Tanggal'!")
                return
        except ValueError:
            messagebox.showerror("Error Waktu", "Format tanggal tidak valid! (Contoh salah: 31 Februari)")
            return

        self.btn_scrape.config(state=tk.DISABLED)
        self.semua_berita.clear()
        self.tree.delete(*self.tree.get_children())
        
        thread = threading.Thread(target=self.proses_scraping, args=(start_date, end_date))
        thread.daemon = True
        thread.start()

    def proses_scraping(self, start_date, end_date):
        pesan_waktu = f"{start_date.strftime('%d/%m/%Y')} s/d {end_date.strftime('%d/%m/%Y')}"
        self.update_status(f"Menyiapkan Scraping: {pesan_waktu}...")
        
        d1 = scrape_jambikota(start_date, end_date, self.update_status)
        d2 = scrape_tribun_jambi(start_date, end_date, self.update_status)
        d3 = scrape_jambi_update(start_date, end_date, self.update_status)
        d4 = scrape_jambi_one(start_date, end_date, self.update_status)

        self.semua_berita = d1 + d2 + d3 + d4
        self.berita_tampil = self.semua_berita.copy()

        self.root.after(0, self.tampilkan_data)
        self.update_status(f"Selesai! Ditemukan {len(self.semua_berita)} berita.")
        self.root.after(0, lambda: self.btn_scrape.config(state=tk.NORMAL))

    def tampilkan_data(self):
        self.tree.delete(*self.tree.get_children())
        for item in self.berita_tampil:
            self.tree.insert("", tk.END, values=(
                item["Sumber"], item["Kategori"], item["Judul"], 
                item["Deskripsi"], item["Tanggal"], item["Link"]
            ))

    def cari_data(self, event=None):
        query = self.entry_cari.get().lower()
        if not query:
            self.berita_tampil = self.semua_berita.copy()
        else:
            keywords = query.split()
            self.berita_tampil = []
            for baris in self.semua_berita:
                teks_baris = " ".join(str(val) for val in baris.values()).lower()
                if all(kw in teks_baris for kw in keywords):
                    self.berita_tampil.append(baris)
                    
        self.tampilkan_data()

    def export_csv(self):
        if not self.berita_tampil:
            messagebox.showwarning("Perhatian", "Tidak ada data untuk diexport!")
            return
            
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            title="Simpan Data Berita",
            initialfile=f"Data_Berita_{datetime.now().strftime('%d_%m_%Y')}.csv"
        )
        
        if file_path:
            try:
                with open(file_path, "w", newline="", encoding="utf-8") as f:
                    fieldnames = ["Sumber", "Kategori", "Judul", "Deskripsi", "Tanggal", "Link"]
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(self.berita_tampil)
                messagebox.showinfo("Sukses", f"Data berhasil disimpan di:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Gagal menyimpan file:\n{e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = AplikasiScraper(root)
    root.mainloop()