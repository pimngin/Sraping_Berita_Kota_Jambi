# app/scrappers/antara_jambi.py
import re
import requests
import time
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote_plus

from config import HEADERS, BATCH_SIZE, BULAN_ID
from app.core.teks_utils import clean_text, keyword_match, normalize_link
from app.core.data_parser import parse_general_date, is_in_range, is_older_than_start
from app.scrappers.base import BaseScraper


def fetch_page(url):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        return url, resp
    except:
        return url, None


def _fetch_antara_desc(url):
    desc = "-"
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        
        content_div = soup.find("div", class_="wrap__article-detail-content")
        if content_div:
            first_p = content_div.find("p")
            if first_p:
                lines = first_p.get_text(separator="\n").split("\n")
                for line in lines:
                    clean_line = clean_text(line)
                    if len(clean_line) > 20:
                        desc = clean_line
                        break
    except:
        pass
    return desc


class AntaraJambiScraper(BaseScraper):
    nama_sumber = "Antara News Jambi"

    def scrape(self, start_date, end_date, keywords, status_callback):
        scraped_data = []
        seen = set()
        base_domain = "https://jambi.antaranews.com"

        use_search = bool(keywords)
        if use_search:
            query = " ".join(keywords)
            query_url = quote_plus(query)
            status_callback(f"🔍 Antara News: Mencari '{query}'...")
        else:
            status_callback("🔍 Antara News: Mengambil berita terkini...")

        max_pages = 100
        stop_all = False

        def make_url(page):
            if use_search:
                return (
                    f"{base_domain}/search?q={query_url}"
                    if page == 1
                    else f"{base_domain}/search/{query_url}/{page}"
                )
            else:
                return (
                    f"{base_domain}/terkini"
                    if page == 1
                    else f"{base_domain}/terkini/{page}"
                )

        def process_page(html):
            results = []
            should_stop = False
            soup = BeautifulSoup(html, "html.parser")
            kandidat_valid = []

            for h_tag in soup.find_all(["h2", "h3"]):
                a_tag = h_tag.find("a", href=re.compile(r"/berita/\d+/"))
                if not a_tag:
                    continue

                judul = clean_text(a_tag.get_text())
                link = a_tag.get("href", "")
                if not link.startswith("http"):
                    link = base_domain + link

                nl = normalize_link(link)
                if nl in seen:
                    continue

                date_text = "-"
                kategori = "Berita"

                container = h_tag.find_parent(
                    "div",
                    class_=re.compile(
                        r"card__post__content|card__post_content|list-article"
                    ),
                )
                if not container:
                    container = h_tag.find_parent()

                if container:
                    for el in container.find_all(["span", "li", "time"]):
                        txt = clean_text(el.get_text())
                        if txt and len(txt) < 80:
                            if (
                                any(
                                    b in txt.lower() for b in list(BULAN_ID.keys())[:24]
                                )
                                or "lalu" in txt.lower()
                                or "baru saja" in txt.lower()
                            ):
                                date_text = txt
                                break

                date_obj = parse_general_date(date_text)

                if is_in_range(date_obj, start_date, end_date):
                    kandidat_valid.append({
                        "judul": judul,
                        "link": link,
                        "nl": nl,
                        "date_text": date_text,
                        "kategori": kategori
                    })
                elif is_older_than_start(date_obj, start_date):
                    should_stop = True
                    break

            def fetch_desc(item):
                desc = _fetch_antara_desc(item["link"])
                return {**item, "deskripsi": desc}

            hasil_fetch = []
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = {executor.submit(fetch_desc, k): k for k in kandidat_valid}
                for future in as_completed(futures):
                    try:
                        hasil_fetch.append(future.result())
                    except:
                        pass

            # Kembalikan urutan sesuai kandidat awal
            hasil_fetch.sort(
                key=lambda x: kandidat_valid.index(
                    next(k for k in kandidat_valid if k["link"] == x["link"])
                )
            )

            for hasil in hasil_fetch:
                gabungan = f"{hasil['judul']} {hasil['deskripsi']}"
                if not keywords or keyword_match(gabungan, keywords):
                    seen.add(hasil["nl"])
                    results.append(
                        {
                            "Sumber": "Antara News Jambi",
                            "Kategori": hasil["kategori"],
                            "Judul": hasil["judul"],
                            "Deskripsi": hasil["deskripsi"],
                            "Tanggal": hasil["date_text"],
                            "Link": hasil["link"],
                        }
                    )

            return results, should_stop

        page = 1
        consecutive_empty = 0

        while page <= max_pages and not stop_all:
            urls = [
                (make_url(p), p)
                for p in range(page, min(page + BATCH_SIZE, max_pages + 1))
            ]

            with ThreadPoolExecutor(max_workers=BATCH_SIZE) as executor:
                futures = {}
                for u, p in urls:
                    futures[executor.submit(fetch_page, u)] = p
                page_results = {}
                for future in as_completed(futures):
                    p = futures[future]
                    url_result, resp = future.result()
                    page_results[p] = resp

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
            status_callback(
                f"🔍 Antara News: {len(scraped_data)} berita ({mode_label}, hlm {page - 1})"
            )

        status_callback(f"✅ Antara News Jambi: {len(scraped_data)} berita ditemukan.")
        return scraped_data
