# app/core/scrape_runner.py
import threading
from app.scrappers import SCRAPER_REGISTRY


def jalankan_scraping(
    selected_keys: list, start_date, end_date, keywords, status_callback, on_done
):
    """
    Jalankan semua scraper di background thread agar UI tidak freeze.
    """

    def _run_all():
        threads = []
        results = {}

        def run_one(key, scraper_class):
            try:
                instance = scraper_class()
                results[key] = instance.scrape(
                    start_date, end_date, keywords, status_callback
                )
            except Exception as e:
                status_callback(f"⚠️ Error pada {key}: {e}")
                results[key] = []

        for key in selected_keys:
            scraper_class = SCRAPER_REGISTRY.get(key)
            if not scraper_class:
                continue
            t = threading.Thread(target=run_one, args=(key, scraper_class))
            t.daemon = True
            threads.append(t)

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        from app.core.data_parser import parse_general_date
        from datetime import datetime
        
        all_data = []
        for key in selected_keys:
            items = results.get(key, [])
            for item in items:
                date_str = item.get("Tanggal", "")
                date_obj = parse_general_date(date_str)
                
                item["_date_obj"] = date_obj
                
                if date_obj:
                    item["Tanggal"] = date_obj.strftime("%d-%m-%Y")
            all_data.extend(items)

        # Tanggal Terbaru
        all_data.sort(key=lambda x: x.get("_date_obj") or datetime.min, reverse=True)

        # Hapus kunci sementara _date_obj
        for item in all_data:
            item.pop("_date_obj", None)

        on_done(all_data)

    # Satu wrapper thread agar UI bebas sama sekali
    wrapper = threading.Thread(target=_run_all)
    wrapper.daemon = True
    wrapper.start()
