# app/scrappers/jambi_ekspress.py
import requests
import time
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote_plus

from config import HEADERS
from app.core.teks_utils import clean_text, keyword_match
from app.core.data_parser import parse_general_date, is_in_range, is_older_than_start
from app.scrappers.base import BaseScraper


def _fetch_jambiekspres_meta(url):
    date_text, date_obj, desc = "-", None, "-"
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Ekstrak Tanggal
        post_info = soup.find("div", class_="post-info")
        if post_info:
            span_date = post_info.find("span", class_="date")
            if span_date:
                date_text = clean_text(span_date.get_text())
                date_obj = parse_general_date(date_text)
                
        # Ekstrak Deskripsi
        post_content = soup.find("div", class_="post")
        if post_content:
            for p in post_content.find_all("p", recursive=False):
                # Buang tag strong agar teks awalan seperti lokasi/koran tidak ikut terbawa
                for strong in p.find_all("strong"):
                    strong.decompose()
                
                teks = clean_text(p.get_text())
                # Hapus awalan "-" (termasuk en-dash dan em-dash) atau spasi sisa
                teks = teks.lstrip("-—– ").strip()
                if len(teks) > 20:
                    desc = teks
                    break
    except:
        pass
    return date_text, date_obj, desc


class JambiEkspressScraper(BaseScraper):
    nama_sumber = "Jambi Ekspres"

    def scrape(self, start_date, end_date, keywords, status_callback):
        scraped_data = []
        link_terscrape = set()
        page = 1

        use_search = bool(keywords)
        if use_search:
            query = " ".join(keywords)
            query_url = quote_plus(query)
            status_callback(f"🔍 Jambi Ekspres: Mencari '{query}'...")
        else:
            status_callback("🔍 Jambi Ekspres: Mengambil berita kategori Ekonomi...")

        while True:
            try:
                offset = (page - 1) * 30
                if use_search:
                    url = (
                        f"https://jambiekspres.disway.id/search/kata/?c={query_url}"
                        if page == 1
                        else f"https://jambiekspres.disway.id/search/kata/{offset}/{offset}/?c={query_url}&num="
                    )
                else:
                    url = (
                        "https://jambiekspres.disway.id/kategori/ekonomi"
                        if page == 1
                        else f"https://jambiekspres.disway.id/kategori/ekonomi/{offset}"
                    )

                response = requests.get(url, headers=HEADERS, timeout=10)
                if response.status_code != 200:
                    break

                soup = BeautifulSoup(response.text, "html.parser")
                articles = soup.find_all("div", class_="media-content")
                if not articles:
                    break

                kandidat = []
                for article in articles:
                    h2_tag = article.find("h2", class_="media-heading")
                    if not h2_tag:
                        continue
                    a_tag = h2_tag.find("a")
                    if not a_tag:
                        continue

                    link = a_tag.get("href", "")
                    if not link or link in link_terscrape:
                        continue

                    title = clean_text(a_tag.get_text())
                    kategori_el = article.find("p", class_="text-uppercase")
                    kategori = (
                        clean_text(kategori_el.get_text())
                        if kategori_el
                        else "Berita Jambi Ekspres"
                    )

                    if keywords and not keyword_match(title, keywords):
                        continue

                    kandidat.append(
                        {"link": link, "title": title, "kategori": kategori}
                    )

                if not kandidat:
                    page += 1
                    if page > 50:
                        break
                    time.sleep(1)
                    continue

                status_callback(
                    f"🔍 Jambi Ekspres: Hal. {page} | Fetch tanggal {len(kandidat)} artikel..."
                )

                def fetch_with_meta(item):
                    date_text, date_obj, desc = _fetch_jambiekspres_meta(item["link"])
                    return {**item, "date_text": date_text, "date_obj": date_obj, "deskripsi": desc}

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
                                "Sumber": "Jambi Ekspres",
                                "Kategori": hasil["kategori"],
                                "Judul": hasil["title"],
                                "Deskripsi": hasil["deskripsi"],
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
                    f"🔍 Jambi Ekspres: Halaman {page}... ({len(scraped_data)} ditemukan)"
                )
                time.sleep(1)

            except Exception as e:
                status_callback(f"⚠️ Jambi Ekspres error: {e}")
                break

        status_callback(f"✅ Jambi Ekspres: {len(scraped_data)} berita ditemukan.")
        return scraped_data
