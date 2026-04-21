# Tutorial Penggunaan Scraper Portal Berita Jambi

Dokumen ini berisi panduan lengkap untuk:
1. Menjalankan program (Script Python) di komputer asli.
2. Mengubah program Python menjadi file eksekutor (`.exe`).
3. Menjalankan file `.exe` di komputer atau perangkat lain.

---

## 1. Menjalankan Program dari Kode Python (Komputer Developer)

Jika Anda ingin menjalankan program langsung dari file `ganda.py`, pastikan komputer Anda memiliki perangkat lunak berikut:

### Persyaratan Sistem (Prerequisites)
1. **Python**: Pastikan Python (versi 3.8 atau lebih baru) sudah terinstal. [Download Python di sini](https://www.python.org/downloads/). 
   *Penting:* Saat instalasi, jangan lupa centang opsi **"Add Python to PATH"**.

### Instalasi Library (Modules)
Buka Terminal atau Command Prompt (CMD) di folder proyek Anda, lalu jalankan perintah berikut untuk menginstal semua kebutuhan library:

```bash
pip install requests beautifulsoup4 cloudscraper openpyxl
```

**Penjelasan Library:**
- `requests`: Untuk mengambil data HTML dari website.
- `beautifulsoup4` (bs4): Untuk membedah dan membaca struktur HTML.
- `cloudscraper`: Untuk menembus sistem keamanan Cloudflare pada situs tertentu (contoh: Jambi One).
- `openpyxl`: Untuk menyimpan hasil pencarian ke dalam format Excel (.xlsx) dengan kolom rapi dan otomatis menyesuaikan lebar (auto-fit).
- `tkinter` dan `csv`: Biasanya sudah bawaan (built-in) dari instalasi Python, jadi tidak perlu diinstal ulang.

### Cara Menjalankan
Buka Command Prompt (CMD) di dalam folder `Portal berita`, lalu ketik:
```bash
python ganda.py
```
Aplikasi GUI Scraper Berita akan langsung terbuka.

---

## 2. Mengubah Program Menjadi File `.exe`

Agar program dapat berjalan di komputer lain tanpa harus menginstal Python dan library yang banyak, Anda dapat merakitnya menjadi file `.exe` mandiri.

### Langkah 1: Instalasi PyInstaller
Buka Command Prompt (CMD) dan instal PyInstaller:
```bash
pip install pyinstaller
```

### Langkah 2: Build file `.exe`
Arahkan CMD ke folder proyek Anda (`d:\MATERI KULIAH\Magang\Portal berita\`), lalu jalankan perintah ini:
```bash
pyinstaller --noconsole --onefile ganda.py
```

**Penjelasan Perintah:**
- `--noconsole`: Agar saat aplikasi dibuka, layar hitam Command Prompt tidak ikut muncul (hanya tampilan GUI saja).
- `--onefile`: Untuk membungkus seluruh library dan file kode menjadi **satu buah** file `.exe` agar mudah dipindahkan.

### Langkah 3: Temukan File `.exe` Anda
Tunggu hingga proses selesai. Setelah selesai (muncul tulisan *Completed successfully*), folder baru bernama `dist` akan tercipta di dalam folder proyek Anda.
Masuk ke folder `dist`, file `ganda.exe` Anda berada di sana dan siap digunakan.

---

## 3. Menjalankan di Perangkat/Komputer Lain

File `.exe` yang dibuat dengan PyInstaller (`--onefile`) bersifat **Standalone** (Mandiri). 

### Apa yang harus disiapkan di Komputer Lain?
**TIDAK ADA.** 
Anda **TIDAK PERLU** menginstal Python, `pip`, atau library apapun (`requests`, `beautifulsoup4`, dll.) di komputer tujuan. Semuanya sudah "terbungkus" di dalam file `ganda.exe`.

### Syarat Wajib Komputer Tujuan:
1. **Sistem Operasi**: Windows (disarankan Windows 10 atau 11, harus 64-bit jika dikompilasi di Windows 64-bit).
2. **Koneksi Internet**: Wajib. Program membutuhkan jaringan internet stabil untuk melakukan penelusuran (scraping) berita di server publik.
3. (Opsional) **Microsoft Excel**: Jika pengguna ingin membuka file hasil ekspor (.xlsx) dengan semestinya.

### Langkah Menjalankan:
1. Salin (Copy) file `ganda.exe` dari folder `dist` tadi ke Flashdisk atau Google Drive.
2. Pindahkan ke komputer lain.
3. Klik ganda (Double-click) pada file `ganda.exe` untuk membukanya.
4. Program siap digunakan!

> **Catatan Tambahan untuk `.exe`:**
> Beberapa Antivirus (contoh: Windows Defender) terkadang menganggap file `.exe` hasil PyInstaller sebagai peringatan yang keliru (*False Positive*). Jika Windows mencegahnya berjalan (tampil popup biru "Windows protected your PC"), klik tulisan **More info** lalu klik tombol **Run anyway**.
