# app/ui/toolbar.py
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime


class Toolbar(tk.Frame):
    def __init__(self, parent, on_scrape_clicked):
        super().__init__(parent)
        self._on_scrape_clicked = on_scrape_clicked
        self._build()

    def _build(self):
        # --- Judul ---
        frame_judul = tk.Frame(self)
        frame_judul.pack(fill=tk.X, pady=(0, 10))
        tk.Label(
            frame_judul,
            text="🔎 Portal Berita Jambi - Pencarian Topik",
            font=("Arial", 16, "bold"),
        ).pack(side=tk.LEFT)

        # --- Kata Kunci ---
        frame_keyword = tk.Frame(self)
        frame_keyword.pack(fill=tk.X, pady=(0, 5))
        tk.Label(
            frame_keyword, text="Kata Kunci Berita:", font=("Arial", 10, "bold")
        ).pack(side=tk.LEFT)
        self.entry_keyword = tk.Entry(frame_keyword, width=50, font=("Arial", 11))
        self.entry_keyword.pack(side=tk.LEFT, padx=10)
        tk.Label(
            frame_keyword,
            text="(contoh: Harga Cabai, atau: Hotel)",
            fg="gray",
            font=("Arial", 9),
        ).pack(side=tk.LEFT)

        # --- Filter Waktu ---
        frame_waktu = tk.Frame(self)
        frame_waktu.pack(fill=tk.X, pady=(5, 10))

        sekarang = datetime.now()
        bulan_lalu = sekarang.replace(day=1)
        hari_list = [str(i) for i in range(1, 32)]
        bulan_list = [str(i) for i in range(1, 13)]
        tahun_list = [str(i) for i in range(sekarang.year - 5, sekarang.year + 1)]

        tk.Label(frame_waktu, text="Dari:", font=("Arial", 9, "bold")).pack(
            side=tk.LEFT
        )
        self.cb_d_hari = ttk.Combobox(
            frame_waktu, values=hari_list, width=3, state="readonly"
        )
        self.cb_d_hari.set(str(bulan_lalu.day))
        self.cb_d_hari.pack(side=tk.LEFT, padx=2)

        self.cb_d_bulan = ttk.Combobox(
            frame_waktu, values=bulan_list, width=3, state="readonly"
        )
        self.cb_d_bulan.set(str(bulan_lalu.month))
        self.cb_d_bulan.pack(side=tk.LEFT, padx=2)

        self.cb_d_tahun = ttk.Combobox(
            frame_waktu, values=tahun_list, width=5, state="readonly"
        )
        self.cb_d_tahun.set(str(bulan_lalu.year))
        self.cb_d_tahun.pack(side=tk.LEFT, padx=(2, 15))

        tk.Label(frame_waktu, text="Sampai:", font=("Arial", 9, "bold")).pack(
            side=tk.LEFT
        )
        self.cb_s_hari = ttk.Combobox(
            frame_waktu, values=hari_list, width=3, state="readonly"
        )
        self.cb_s_hari.set(str(sekarang.day))
        self.cb_s_hari.pack(side=tk.LEFT, padx=2)

        self.cb_s_bulan = ttk.Combobox(
            frame_waktu, values=bulan_list, width=3, state="readonly"
        )
        self.cb_s_bulan.set(str(sekarang.month))
        self.cb_s_bulan.pack(side=tk.LEFT, padx=2)

        self.cb_s_tahun = ttk.Combobox(
            frame_waktu, values=tahun_list, width=5, state="readonly"
        )
        self.cb_s_tahun.set(str(sekarang.year))
        self.cb_s_tahun.pack(side=tk.LEFT, padx=(2, 15))

        self.btn_scrape = tk.Button(
            frame_waktu,
            text="Mulai Cari Berita",
            bg="#4CAF50",
            fg="white",
            font=("Arial", 10, "bold"),
            command=self._handle_scrape,
        )
        self.btn_scrape.pack(side=tk.LEFT, padx=10)

        # --- Checkbox Sumber ---
        frame_sumber = tk.Frame(self)
        frame_sumber.pack(fill=tk.X, pady=(0, 5))
        tk.Label(frame_sumber, text="Sumber:", font=("Arial", 9, "bold")).pack(
            side=tk.LEFT
        )

        self.var_pemkot = tk.BooleanVar(value=True)
        self.var_tribun = tk.BooleanVar(value=True)
        self.var_jambupdate = tk.BooleanVar(value=True)
        self.var_jambione = tk.BooleanVar(value=True)
        self.var_antara = tk.BooleanVar(value=True)
        self.var_jambiekspres = tk.BooleanVar(value=True)
        self.var_jambilink = tk.BooleanVar(value=True)

        sumber_list = [
            ("Pemkot Jambi", self.var_pemkot),
            ("Tribun Jambi", self.var_tribun),
            ("Jambi Update", self.var_jambupdate),
            ("Jambi One", self.var_jambione),
            ("Antara News Jambi", self.var_antara),
            ("Jambi Ekspres", self.var_jambiekspres),
            ("Jambi Link", self.var_jambilink),
        ]
        for label, var in sumber_list:
            tk.Checkbutton(frame_sumber, text=label, variable=var).pack(
                side=tk.LEFT, padx=5
            )

        self.lbl_status = tk.Label(
            frame_sumber, text="Status: Menunggu instruksi...", fg="blue"
        )
        self.lbl_status.pack(side=tk.RIGHT, padx=5)

    def _handle_scrape(self):
        keyword_text = self.entry_keyword.get().strip()
        keywords = keyword_text.split() if keyword_text else []

        if not keywords:
            jawab = messagebox.askyesno(
                "Tanpa Kata Kunci",
                "Anda tidak memasukkan kata kunci pencarian.\n\n"
                "Apakah ingin mengambil SEMUA berita dalam rentang waktu tersebut?\n\n"
                "(Ini mungkin memakan waktu lebih lama)",
            )
            if not jawab:
                return

        try:
            start_date = datetime(
                int(self.cb_d_tahun.get()),
                int(self.cb_d_bulan.get()),
                int(self.cb_d_hari.get()),
            )
            end_date = datetime(
                int(self.cb_s_tahun.get()),
                int(self.cb_s_bulan.get()),
                int(self.cb_s_hari.get()),
                23,
                59,
                59,
            )
            if start_date > end_date:
                messagebox.showerror(
                    "Error Waktu",
                    "'Dari Tanggal' tidak boleh lebih baru dari 'Sampai Tanggal'!",
                )
                return
        except ValueError:
            messagebox.showerror(
                "Error Waktu", "Format tanggal tidak valid! (Contoh salah: 31 Februari)"
            )
            return

        # Kumpulkan key scraper yang dicentang
        selected_keys = []
        mapping = {
            "pemkot": self.var_pemkot,
            "tribun": self.var_tribun,
            "jambupdate": self.var_jambupdate,
            "jambione": self.var_jambione,
            "antara": self.var_antara,
            "jambiekspres": self.var_jambiekspres,
            "jambilink": self.var_jambilink,
        }
        for key, var in mapping.items():
            if var.get():
                selected_keys.append(key)

        self.btn_scrape.config(state=tk.DISABLED)
        self._on_scrape_clicked(start_date, end_date, keywords, selected_keys)

    def set_status(self, pesan):
        self.lbl_status.config(text=f"Status: {pesan}")

    def enable_btn_scrape(self):
        self.btn_scrape.config(state=tk.NORMAL)
