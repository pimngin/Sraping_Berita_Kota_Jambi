# app/scrappers/base.py
from abc import ABC, abstractmethod


class BaseScraper(ABC):
    """Abstract class yang wajib diikuti semua scraper."""

    nama_sumber = ""  # Contoh: "Tribun Jambi"

    @abstractmethod
    def scrape(self, start_date, end_date, keywords, status_callback) -> list:
        """
        Jalankan scraping dan kembalikan list of dict dengan format:
        {
            "Sumber"    : str,
            "Kategori"  : str,
            "Judul"     : str,
            "Deskripsi" : str,
            "Tanggal"   : str,
            "Link"      : str,
        }
        """
        pass
