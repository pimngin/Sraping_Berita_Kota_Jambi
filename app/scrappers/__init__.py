# app/scrappers/__init__.py
from app.scrappers.pemkot_jambi import PemkotJambiScraper
from app.scrappers.tribun_jambi import TribunJambiScraper
from app.scrappers.jambi_update import JambiUpdateScraper
from app.scrappers.jambi_one import JambiOneScraper
from app.scrappers.jambi_ekspress import JambiEkspressScraper
from app.scrappers.antara_jambi import AntaraJambiScraper
from app.scrappers.jambi_link import JambiLinkScraper

# Kunci dict harus sama persis dengan nama yang dipakai di toolbar (var_* di UI)
SCRAPER_REGISTRY = {
    "pemkot": PemkotJambiScraper,
    "tribun": TribunJambiScraper,
    "jambupdate": JambiUpdateScraper,
    "jambione": JambiOneScraper,
    "jambiekspres": JambiEkspressScraper,
    "antara": AntaraJambiScraper,
    "jambilink": JambiLinkScraper,
}
