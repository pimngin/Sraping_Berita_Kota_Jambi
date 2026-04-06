import requests
from bs4 import BeautifulSoup
from datetime import datetime

BASE_URL = "https://jambikota.go.id/informasi/berita"

headers = {
    "User-Agent": "Mozilla/5.0"
}

page = 1
all_data = []

# Target bulan
target_bulan = 2
target_tahun = 2026

while True:

    url = f"{BASE_URL}?page={page}"
    print(f"Scraping page {page}...")

    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        break

    soup = BeautifulSoup(response.text, "html.parser")

    cards = soup.select("#berita-container a.content-card")

    if not cards:
        break

    stop = False

    for card in cards:

        title = card.select_one("h2.card-title").get_text(strip=True)
        desc = card.select_one("p").get_text(strip=True)
        link = card.get("href")

        date_text = card.select_one(".card-actions").get_text(strip=True)

        # convert tanggal
        try:
            date_obj = datetime.strptime(date_text, "%d %b %Y")
        except:
            continue

        # cek bulan dan tahun
        if date_obj.month == target_bulan and date_obj.year == target_tahun:

            data = {
                "judul": title,
                "deskripsi": desc,
                "tanggal": date_text,
                "link": link
            }

            all_data.append(data)

            print(title)
            print(date_text)
            print(link)
            print("-"*50)

        # jika sudah lewat bulan target → stop
        elif date_obj.year < target_tahun or date_obj.month < target_bulan:
            stop = True
            break

    if stop:
        break

    page += 1


print("\nTotal berita bulan ini:", len(all_data))

import csv

with open("berita_bulan_ini.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["Judul", "Deskripsi", "Tanggal", "Link"])

    for d in all_data:
        writer.writerow([d["judul"], d["deskripsi"], d["tanggal"], d["link"]])
print("Data berhasil disimpan ke berita_bulan_ini.csv")