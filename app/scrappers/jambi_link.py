# app/scrappers/jambi_link.py
import requests
import time
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote_plus
from datetime import datetime

from config import HEADERS
from app.core.teks_utils import clean_text, keyword_match
from app.core.data_parser import is_in_range
from app.scrappers.base import BaseScraper


def _fetch_jambilink_meta(url):
    date_text_tampil, date_obj, kategori = "-", None, "-"
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        
        # --- Ekstrak Tanggal ---
        time_tag = soup.find("time", class_="datetime")
        if time_tag:
            dt_attr = time_tag.get("datetime")
            if dt_attr:
                date_str = dt_attr.split("T")[0]
                date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                date_text_tampil = time_tag.get_text(strip=True) + " WIB"

        # --- Ekstrak Kategori ---
        kat_div = soup.find("div", class_="field--name-field-kategori")
        if kat_div and kat_div.find("a"):
            kategori = clean_text(kat_div.find("a").get_text())
            
    except:
        pass
    return date_text_tampil, date_obj, kategori


class JambiLinkScraper(BaseScraper):
    nama_sumber = "Jambilink"

    def scrape(self, start_date, end_date, keywords, status_callback):
        if not keywords:
            status_callback("⏭️ Jambilink diabaikan (Hanya jalan jika ada kata kunci).")
            return []

        query_url = quote_plus(" ".join(keywords))
        base_url = f"https://www.jambilink.id/search/node?keys={query_url}"

        scraped_data = []
        link_terscrape = set()
        page = 1
        max_pages = 20

        status_callback(f"🔍 Jambilink: Mencari '{' '.join(keywords)}'...")

        while page <= max_pages:
            try:
                url = (
                    base_url
                    if page == 1
                    else f"{base_url}&page={page-1}%2C0%2C0%2C0%2C0%2C0%2C0%2C0%2C0%2C0%2C0"
                )

                response = requests.get(url, headers=HEADERS, timeout=10)
                if response.status_code != 200:
                    break

                soup = BeautifulSoup(response.text, "html.parser")
                h3_tags = soup.find_all("h3", class_="search-result__title")
                if not h3_tags:
                    break

                kandidat = []
                for h3 in h3_tags:
                    a_tag = h3.find("a")
                    if not a_tag:
                        continue
                    link = a_tag.get("href", "")
                    if not link or link in link_terscrape:
                        continue

                    title = clean_text(a_tag.get_text())
                    parent_li = h3.find_parent("li")
                    snippet_tag = (
                        parent_li.find("p", class_="search-result__snippet")
                        if parent_li
                        else None
                    )
                    desc = clean_text(snippet_tag.get_text()) if snippet_tag else "-"

                    gabungan = f"{title} {desc}"
                    if keywords and not keyword_match(gabungan, keywords):
                        continue

                    kandidat.append(
                        {"link": link, "title": title, "desc": desc, "kategori": "-"}
                    )

                if not kandidat:
                    break

                status_callback(
                    f"🔍 Jambilink: Hal. {page} | Fetch tanggal {len(kandidat)} artikel..."
                )

                def fetch_with_meta(item):
                    date_text, date_obj, kategori = _fetch_jambilink_meta(item["link"])
                    return {**item, "date_text": date_text, "date_obj": date_obj, "kategori": kategori}

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

                for hasil in hasil_fetch:
                    link = hasil["link"]
                    date_obj = hasil["date_obj"]
                    if link in link_terscrape:
                        continue
                    if is_in_range(date_obj, start_date, end_date):
                        link_terscrape.add(link)
                        scraped_data.append(
                            {
                                "Sumber": "Jambilink",
                                "Kategori": hasil["kategori"],
                                "Judul": hasil["title"],
                                "Deskripsi": hasil["desc"],
                                "Tanggal": date_obj.strftime("%d-%m-%Y") if date_obj else hasil["date_text"],
                                "Link": link,
                            }
                        )

                page += 1
                status_callback(
                    f"🔍 Jambilink: Halaman {page}... ({len(scraped_data)} ditemukan)"
                )
                time.sleep(1)

            except Exception as e:
                status_callback(f"⚠️ Jambilink error: {e}")
                break

        status_callback(f"✅ Jambilink: {len(scraped_data)} berita ditemukan.")
        return scraped_data
