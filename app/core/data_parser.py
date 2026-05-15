# app/core/data_parser.py
import re
from datetime import datetime, timedelta
from config import BULAN_ID


def parse_general_date(date_str):
    now = datetime.now()
    date_str = str(date_str).lower().strip().replace("wib", "").replace(",", "")

    if "lalu" in date_str or "baru" in date_str:
        try:
            angka = (
                int(re.search(r"\d+", date_str).group())
                if re.search(r"\d+", date_str)
                else 0
            )
            if "jam" in date_str:
                return now - timedelta(hours=angka)
            elif "menit" in date_str:
                return now - timedelta(minutes=angka)
            elif "hari" in date_str:
                return now - timedelta(days=angka)
            elif "detik" in date_str:
                return now - timedelta(seconds=angka)
        except:
            return now
        return now

    try:
        parts = date_str.split()
        day, month, year = None, None, None
        for i, part in enumerate(parts):
            if part in BULAN_ID:
                month = BULAN_ID[part]
                if i > 0 and parts[i - 1].isdigit():
                    day = int(parts[i - 1])
                if i < len(parts) - 1 and parts[i + 1].isdigit():
                    year = int(parts[i + 1])
                break
        if day and month and year:
            return datetime(year, month, day)
    except:
        pass

    # Format numerik DD-MM-YYYY (contoh: "12-04-2026" dari Jambi Ekspres)
    try:
        match = re.search(r"(\d{1,2})-(\d{1,2})-(\d{4})", date_str)
        if match:
            day, month, year = match.groups()
            return datetime(int(year), int(month), int(day))
    except:
        pass

    return None


def is_in_range(date_obj, start_date, end_date):
    """Mengecek apakah tanggal berita berada di dalam rentang waktu."""
    if not date_obj:
        return False
    return start_date <= date_obj <= end_date


def is_older_than_start(date_obj, start_date):
    """Mengecek apakah tanggal berita lebih tua dari batas start untuk stop scraping."""
    if not date_obj:
        return False
    return date_obj < start_date
