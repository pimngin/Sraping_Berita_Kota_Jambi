# app/ui/result_table.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime

from app.exporters.excel_exporter import export_excel
from app.exporters.csv_exporter import export_csv


class ResultTable(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.semua_berita = []
        self.berita_tampil = []
        self._build()

    def _build(self):
        # --- Frame filter & export ---
        frame_tengah = tk.Frame(self)
        frame_tengah.pack(fill=tk.X, pady=(0, 5))

        tk.Label(frame_tengah, text="Filter Tabel:").pack(side=tk.LEFT)
        self.entry_cari = tk.Entry(frame_tengah, width=40)
        self.entry_cari.pack(side=tk.LEFT, padx=5)
        self.entry_cari.bind("<KeyRelease>", self._cari_data)

        self.lbl_total = tk.Label(
            frame_tengah, text="Total: 0 berita", font=("Arial", 9, "bold"), fg="#333"
        )
        self.lbl_total.pack(side=tk.LEFT, padx=15)

        self.btn_export = tk.Button(
            frame_tengah,
            text="📥 Export Excel",
            bg="#2196F3",
            fg="white",
            font=("Arial", 9, "bold"),
            command=self._export,
        )
        self.btn_export.pack(side=tk.RIGHT)

        # --- Tabel ---
        frame_bawah = tk.Frame(self)
        frame_bawah.pack(fill=tk.BOTH, expand=True)

        kolom = ("Sumber", "Kategori", "Judul", "Deskripsi", "Tanggal", "Link")
        self.tree = ttk.Treeview(frame_bawah, columns=kolom, show="headings")
        for col in kolom:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120, anchor=tk.W)
        self.tree.column("Judul", width=300)
        self.tree.column("Deskripsi", width=250)

        scrollbar_y = ttk.Scrollbar(
            frame_bawah, orient=tk.VERTICAL, command=self.tree.yview
        )
        scrollbar_x = ttk.Scrollbar(
            frame_bawah, orient=tk.HORIZONTAL, command=self.tree.xview
        )
        self.tree.configure(
            yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set
        )

        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def tampilkan(self, data: list):
        self.semua_berita = data
        self.berita_tampil = data.copy()
        self._render()

    def _render(self):
        self.tree.delete(*self.tree.get_children())
        for item in self.berita_tampil:
            self.tree.insert(
                "",
                tk.END,
                values=(
                    item["Sumber"],
                    item["Kategori"],
                    item["Judul"],
                    item["Deskripsi"],
                    item["Tanggal"],
                    item["Link"],
                ),
            )
        self.lbl_total.config(text=f"Total: {len(self.berita_tampil)} berita")

    def reset(self):
        self.semua_berita.clear()
        self.berita_tampil.clear()
        self.tree.delete(*self.tree.get_children())
        self.lbl_total.config(text="Total: 0 berita")

    def _cari_data(self, event=None):
        query = self.entry_cari.get().lower()
        if not query:
            self.berita_tampil = self.semua_berita.copy()
        else:
            kws = query.split()
            self.berita_tampil = [
                b
                for b in self.semua_berita
                if all(kw in " ".join(str(v) for v in b.values()).lower() for kw in kws)
            ]
        self._render()

    def _export(self):
        if not self.berita_tampil:
            messagebox.showwarning("Perhatian", "Tidak ada data untuk diexport!")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx"), ("CSV files", "*.csv")],
            title="Simpan Data Berita",
            initialfile=f"Data_Berita_{datetime.now().strftime('%d_%m_%Y')}.xlsx",
        )
        if not file_path:
            return

        try:
            if file_path.lower().endswith(".csv"):
                export_csv(self.berita_tampil, file_path)
            else:
                export_excel(self.berita_tampil, file_path)
            messagebox.showinfo("Sukses", f"Data berhasil disimpan di:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Gagal menyimpan file:\n{e}")
