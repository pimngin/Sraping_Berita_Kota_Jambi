# app/scrappers/pemkot_jambi.py
import requests
import time
from bs4 import BeautifulSoup

from config import HEADERS
from app.core.teks_utils import clean_text, keyword_match
from app.core.data_parser import parse_general_date, is_in_range, is_older_than_start
from app.scrappers.base import BaseScraper


class PemkotJambiScraper(BaseScraper):
    nama_sumber = "Pemkot Jambi"

    def scrape(self, start_date, end_date, keywords, status_callback):
        base_url = "https://jambikota.go.id/informasi/berita"
        page = 1
        scraped_data = []
        status_callback("🔍 Pemkot Jambi: Mencari berita...")

        while True:
            try:
                response = requests.get(
                    f"{base_url}?page={page}", headers=HEADERS, timeout=10
                )
                if response.status_code != 200:
                    break

                soup = BeautifulSoup(response.text, "html.parser")
                cards = soup.select("#berita-container a.content-card")
                if not cards:
                    break

                stop_scraping = False
                for card in cards:
                    title = clean_text(
                        card.select_one("h2.card-title").get_text()
                        if card.select_one("h2.card-title")
                        else ""
                    )
                    desc = clean_text(
                        card.select_one("p").get_text() if card.select_one("p") else ""
                    )
                    link = card.get("href")
                    date_element = card.select_one(".card-actions")
                    date_text = clean_text(
                        date_element.get_text() if date_element else ""
                    )
                    date_obj = parse_general_date(date_text)

                    if is_in_range(date_obj, start_date, end_date):
                        gabungan = f"{title} {desc}"
                        if keyword_match(gabungan, keywords):
                            scraped_data.append(
                                {
                                    "Sumber": "Pemkot Jambi",
                                    "Kategori": "Pemerintahan",
                                    "Judul": title,
                                    "Deskripsi": desc,
                                    "Tanggal": date_text,
                                    "Link": link,
                                }
                            )
                    elif is_older_than_start(date_obj, start_date):
                        stop_scraping = True
                        break

                if stop_scraping:
                    break

                page += 1
                status_callback(
                    f"🔍 Pemkot Jambi: Halaman {page}... ({len(scraped_data)} ditemukan)"
                )
                time.sleep(1)

            except Exception as e:
                status_callback(f"⚠️ Pemkot Jambi error: {e}")
                break

        status_callback(f"✅ Pemkot Jambi: {len(scraped_data)} berita ditemukan.")
        return scraped_data
