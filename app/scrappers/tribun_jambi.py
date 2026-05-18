# app/scrappers/tribun_jambi.py
import requests
import time
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

from config import HEADERS
from app.core.teks_utils import clean_text, keyword_match
from app.core.data_parser import parse_general_date, is_in_range, is_older_than_start
from app.scrappers.base import BaseScraper


def _fetch_tribun_article_meta(url):
    """Fetch tanggal dan deskripsi dari halaman detail artikel Tribun."""
    date_text, date_obj, desc = "-", None, "-"
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Ekstrak Tanggal
        content_date = soup.find("div", class_="content-date")
        if content_date:
            span = content_date.find("span")
            if span:
                date_text = clean_text(span.get_text())
                date_obj = parse_general_date(date_text)
                
        # Ekstrak Deskripsi
        content_text = soup.find("div", class_="content-text")
        if content_text:
            p_tags = content_text.find_all("p")
            for p in p_tags:
                teks_p = clean_text(p.get_text())
                if len(teks_p) > 15:  # Abaikan paragraf kosong (&nbsp;) atau yang terlalu pendek
                    desc = teks_p
                    break
                
    except:
        pass
    return date_text, date_obj, desc


class TribunJambiScraper(BaseScraper):
    nama_sumber = "Tribun Jambi"

    def scrape(self, start_date, end_date, keywords, status_callback):
        url_base = "https://jambi.tribunnews.com/kota-jambi-bahagia/artikel"
        scraped_data = []
        link_terscrape = set()
        page = 1
        status_callback("🔍 Tribun Jambi: Mencari berita...")

        while True:
            try:
                url = url_base if page == 1 else f"{url_base}/?page={page}"
                response = requests.get(url, headers=HEADERS, timeout=10)
                if response.status_code != 200:
                    break

                soup = BeautifulSoup(response.text, "html.parser")
                articles = soup.find_all("div", class_="artikel-item")
                if not articles:
                    break

                kandidat = []
                for article in articles:
                    a_tag = article.find("a")
                    if not a_tag:
                        continue
                    link = a_tag.get("href", "")
                    if not link or link in link_terscrape:
                        continue
                    title_el = a_tag.find("div", class_="artikel-title")
                    title = clean_text(
                        title_el.find("p").get_text()
                        if title_el and title_el.find("p")
                        else a_tag.get_text()
                    )
                    kategori_el = a_tag.find("div", class_="artikel-sub")
                    kategori = (
                        clean_text(kategori_el.get_text())
                        if kategori_el
                        else "Berita Kota"
                    )

                    if keywords and not keyword_match(title, keywords):
                        continue
                    kandidat.append(
                        {"link": link, "title": title, "kategori": kategori}
                    )

                if not kandidat:
                    page += 1
                    time.sleep(1)
                    if page > 50:
                        break
                    continue

                status_callback(
                    f"🔍 Tribun Jambi: Hal. {page} | Fetch tanggal {len(kandidat)} artikel..."
                )

                def fetch_with_meta(item):
                    date_text, date_obj, desc = _fetch_tribun_article_meta(item["link"])
                    return {**item, "date_text": date_text, "date_obj": date_obj, "desc": desc}

                hasil_fetch = []
                with ThreadPoolExecutor(max_workers=5) as executor:
                    futures = {executor.submit(fetch_with_meta, k): k for k in kandidat}
                    for future in as_completed(futures):
                        try:
                            hasil_fetch.append(future.result())
                        except:
                            pass

                hasil_fetch.sort(
                    key=lambda x: kandidat.index(
                        next(k for k in kandidat if k["link"] == x["link"])
                    )
                )

                stop_scraping = False
                artikel_baru_di_halaman_ini = 0

                for hasil in hasil_fetch:
                    link = hasil["link"]
                    if link in link_terscrape:
                        continue
                    date_obj = hasil["date_obj"]
                    if is_in_range(date_obj, start_date, end_date):
                        link_terscrape.add(link)
                        artikel_baru_di_halaman_ini += 1
                        scraped_data.append(
                            {
                                "Sumber": "Tribun Jambi",
                                "Kategori": hasil["kategori"],
                                "Judul": hasil["title"],
                                "Deskripsi": hasil["desc"],
                                "Tanggal": hasil["date_text"],
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
                    f"🔍 Tribun Jambi: Halaman {page}... ({len(scraped_data)} ditemukan)"
                )
                time.sleep(1)

            except Exception as e:
                status_callback(f"⚠️ Tribun Jambi error: {e}")
                break

        status_callback(f"✅ Tribun Jambi: {len(scraped_data)} berita ditemukan.")
        return scraped_data
