# app/scrappers/jambi_one.py
import time
import cloudscraper
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.core.teks_utils import clean_text, keyword_match
from app.core.data_parser import parse_general_date, is_in_range, is_older_than_start
from app.scrappers.base import BaseScraper


def _fetch_jambione_desc(url, scraper):
    desc = "-"
    try:
        resp = scraper.get(url, timeout=15)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            article_div = soup.find("article", class_="read__content")
            if article_div:
                for p in article_div.find_all("p"):
                    teks = clean_text(p.get_text())
                    if len(teks) > 20 and "baca juga" not in teks.lower():
                        desc = teks
                        break
    except:
        pass
    return desc


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
                kandidat_valid = []

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
                        kandidat_valid.append({
                            "judul": judul,
                            "kategori": kategori,
                            "date_text": date_text,
                            "link": link
                        })
                    elif is_older_than_start(date_obj, start_date):
                        stop_scraping = True
                        break

                def fetch_desc(item):
                    desc = _fetch_jambione_desc(item["link"], scraper)
                    return {**item, "deskripsi": desc}

                hasil_fetch = []
                with ThreadPoolExecutor(max_workers=2) as executor:
                    futures = {executor.submit(fetch_desc, k): k for k in kandidat_valid}
                    for future in as_completed(futures):
                        try:
                            hasil_fetch.append(future.result())
                        except:
                            pass

                hasil_fetch.sort(
                    key=lambda x: kandidat_valid.index(
                        next(k for k in kandidat_valid if k["link"] == x["link"])
                    )
                )

                for hasil in hasil_fetch:
                    gabungan = f"{hasil['judul']} {hasil['deskripsi']}"
                    if not keywords or keyword_match(gabungan, keywords):
                        scraped_data.append(
                            {
                                "Sumber": "Jambi One",
                                "Kategori": hasil["kategori"],
                                "Judul": hasil["judul"],
                                "Deskripsi": hasil["deskripsi"],
                                "Tanggal": hasil["date_text"],
                                "Link": hasil["link"],
                            }
                        )

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
