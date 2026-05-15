# app/core/teks_utils.py
import re


def clean_text(text):
    if not text:
        return "-"
    return re.sub(r"\s+", " ", text).strip()


def keyword_match(text, keywords):
    """Mengecek apakah teks mengandung SEMUA kata kunci (case-insensitive)."""
    if not keywords:
        return True
    text_lower = text.lower()
    return all(kw.lower() in text_lower for kw in keywords)


def normalize_link(url):
    """Normalisasi URL untuk pengecekan duplikat.
    Menghapus trailing slash, query parameter, dan fragment."""
    return url.rstrip("/").split("?")[0].split("#")[0]
