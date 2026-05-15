# app/scrappers/jambi_update.py
import requests
import time
from bs4 import BeautifulSoup

from config import HEADERS
from app.core.teks_utils import clean_text, keyword_match
from app.core.data_parser import parse_general_date, is_in_range, is_older_than_start
from app.scrappers.base import BaseScraper


class JambiUpdateScraper(BaseScraper):
    nama_sumber = "Jambi Update"

    def scrape(self, start_date, end_date, keywords, status_callback):
        url_base = "https://www.jambiupdate.co/kategori/bisnis"
        scraped_data = []
        link_terscrape = set()
        page = 1
        status_callback("🔍 Jambi Update: Mencari berita...")

        while True:
            try:
                url = url_base if page == 1 else f"{url_base}/{page}"
                response = requests.get(url, headers=HEADERS, timeout=10)
                if response.status_code != 200:
                    break

                soup = BeautifulSoup(response.text, "html.parser")
                stop_scraping = False
                artikel_baru_di_halaman_ini = 0

                # --- Struktur 1: div.media ---
                articles_s1 = soup.find_all("div", class_="media")
                if articles_s1:
                    for article in articles_s1:
                        media_body = article.find("div", class_="media-body")
                        if not media_body:
                            continue
                        h3_tag = media_body.find("h3", class_="category-title")
                        if not h3_tag:
                            continue
                        a_tag = h3_tag.find("a")
                        if not a_tag:
                            continue

                        title = clean_text(a_tag.get_text())
                        link = a_tag.get("href", "")
                        if not link or link in link_terscrape:
                            continue

                        p_tag = media_body.find("p")
                        desc = clean_text(p_tag.get_text()) if p_tag else "-"

                        date_text = "-"
                        author_info = media_body.find("div", class_="author-info")
                        if author_info:
                            span_date = author_info.find("span", class_="post-author")
                            if span_date:
                                date_text = clean_text(span_date.get_text())

                        date_obj = parse_general_date(date_text)

                        if is_in_range(date_obj, start_date, end_date):
                            link_terscrape.add(link)
                            artikel_baru_di_halaman_ini += 1
                            if keyword_match(f"{title} {desc}", keywords):
                                scraped_data.append(
                                    {
                                        "Sumber": "Jambi Update",
                                        "Kategori": "Bisnis",
                                        "Judul": title,
                                        "Deskripsi": desc,
                                        "Tanggal": date_text,
                                        "Link": link,
                                    }
                                )
                        elif is_older_than_start(date_obj, start_date):
                            stop_scraping = True
                            break

                # --- Struktur 2: a.news-list ---
                else:
                    articles_s2 = soup.find_all("a", class_="news-list")
                    if not articles_s2:
                        break

                    for article in articles_s2:
                        link = article.get("href", "")
                        if not link or link in link_terscrape:
                            continue

                        title_el = article.find("div", class_="title")
                        if not title_el:
                            continue
                        title = clean_text(title_el.get_text())

                        date_text = "-"
                        author_el = article.find("div", class_="author")
                        if author_el:
                            date_text = clean_text(author_el.get_text())

                        date_obj = parse_general_date(date_text)
                        desc = "-"

                        if is_in_range(date_obj, start_date, end_date):
                            link_terscrape.add(link)
                            artikel_baru_di_halaman_ini += 1
                            if keyword_match(title, keywords):
                                scraped_data.append(
                                    {
                                        "Sumber": "Jambi Update",
                                        "Kategori": "Bisnis",
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
                if artikel_baru_di_halaman_ini == 0:
                    break

                page += 1
                status_callback(
                    f"🔍 Jambi Update: Halaman {page}... ({len(scraped_data)} ditemukan)"
                )
                time.sleep(1)

            except Exception as e:
                status_callback(f"⚠️ Jambi Update error: {e}")
                break

        status_callback(f"✅ Jambi Update: {len(scraped_data)} berita ditemukan.")
        return scraped_data
