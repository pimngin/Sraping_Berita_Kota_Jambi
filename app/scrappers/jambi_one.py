# app/scrappers/jambi_one.py
import time
import cloudscraper
from bs4 import BeautifulSoup

from app.core.teks_utils import clean_text, keyword_match
from app.core.data_parser import parse_general_date, is_in_range, is_older_than_start
from app.scrappers.base import BaseScraper


class JambiOneScraper(BaseScraper):
    nama_sumber = "Jambi One"

    def scrape(self, start_date, end_date, keywords, status_callback):
        url_base = "https://www.jambione.com/tag/ekonomi"
        scraped_data = []
        link_terscrape = set()
        page = 1
        status_callback("🔍 Jambi One: Mencari berita...")

        scraper = cloudscraper.create_scraper(
            browser={"browser": "chrome", "platform": "windows", "mobile": False}
        )

        while True:
            try:
                if page % 10 == 0:
                    scraper = cloudscraper.create_scraper(
                        browser={
                            "browser": "chrome",
                            "platform": "windows",
                            "mobile": False,
                        }
                    )
                    status_callback(
                        f"🔄 Jambi One: Refresh session (halaman {page})..."
                    )

                url = url_base if page == 1 else f"{url_base}?page={page}"
                response = scraper.get(url, timeout=15)
                if response.status_code != 200:
                    break

                soup = BeautifulSoup(response.text, "html.parser")
                articles = soup.find_all("div", class_="latest__item")
                if not articles:
                    break

                stop_scraping = False
                artikel_baru_di_halaman_ini = 0

                for article in articles:
                    judul_el = article.select_one("h2.latest__title a.latest__link")
                    if not judul_el:
                        continue

                    judul = clean_text(judul_el.get_text())
                    link = judul_el.get("href", "")
                    if not link or link in link_terscrape:
                        continue

                    kategori_el = article.select_one("h4.latest__subtitle a")
                    kategori = (
                        clean_text(kategori_el.get_text()) if kategori_el else "Lainnya"
                    )

                    date_text = "-"
                    date_el = article.select_one("date.latest__date")
                    if date_el:
                        date_text = (
                            clean_text(date_el.get_text()).replace("|", "").strip()
                        )

                    date_obj = parse_general_date(date_text)

                    if is_in_range(date_obj, start_date, end_date):
                        link_terscrape.add(link)
                        artikel_baru_di_halaman_ini += 1
                        if keyword_match(judul, keywords):
                            scraped_data.append(
                                {
                                    "Sumber": "Jambi One",
                                    "Kategori": kategori,
                                    "Judul": judul,
                                    "Deskripsi": "-",
                                    "Tanggal": date_text,
                                    "Link": link,
                                }
                            )
                    elif is_older_than_start(date_obj, start_date):
                        stop_scraping = True
                        break

                if stop_scraping:
                    break
                if artikel_baru_di_halaman_ini == 0:
                    break

                page += 1
                status_callback(
                    f"🔍 Jambi One: Halaman {page}... ({len(scraped_data)} ditemukan)"
                )
                time.sleep(1)

            except Exception as e:
                status_callback(f"⚠️ Jambi One error: {e}")
                break

        status_callback(f"✅ Jambi One: {len(scraped_data)} berita ditemukan.")
        return scraped_data
