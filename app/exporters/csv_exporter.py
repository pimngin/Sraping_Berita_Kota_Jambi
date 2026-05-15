# app/exporters/csv_exporter.py
import csv

FIELDNAMES = ["Sumber", "Kategori", "Judul", "Deskripsi", "Tanggal", "Link"]


def export_csv(data: list, file_path: str):
    """Ekspor list of dict ke file .csv."""
    with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(data)
