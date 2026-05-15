# app/ui/main_window.py
import tkinter as tk
from app.ui.toolbar import Toolbar
from app.ui.result_table import ResultTable
from app.core.scrape_runner import jalankan_scraping


class MainWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("Scraper Berita Jambi - Pencarian Berdasarkan Topik")
        self.root.geometry("1150x700")
        self.root.configure(padx=10, pady=10)

        self.toolbar = Toolbar(self.root, on_scrape_clicked=self._mulai_scraping)
        self.toolbar.pack(fill=tk.X)

        self.result_table = ResultTable(self.root)
        self.result_table.pack(fill=tk.BOTH, expand=True)

    def _mulai_scraping(self, start_date, end_date, keywords, selected_keys):
        self.result_table.reset()

        kw_text = f"'{' '.join(keywords)}'" if keywords else "semua berita"
        pesan_waktu = (
            f"{start_date.strftime('%d/%m/%Y')} s/d {end_date.strftime('%d/%m/%Y')}"
        )
        self._update_status(f"Mencari {kw_text} | {pesan_waktu}...")

        jalankan_scraping(
            selected_keys=selected_keys,
            start_date=start_date,
            end_date=end_date,
            keywords=keywords,
            status_callback=self._update_status,
            on_done=self._selesai,
        )

    def _selesai(self, all_data):
        self.root.after(0, lambda: self.result_table.tampilkan(all_data))
        self.root.after(
            0,
            lambda: self._update_status(
                f"🎉 Selesai! Ditemukan {len(all_data)} berita."
            ),
        )
        self.root.after(0, self.toolbar.enable_btn_scrape)

    def _update_status(self, pesan):
        self.root.after(0, lambda: self.toolbar.set_status(pesan))
