"""
Einstiegspunkt der täglichen Immobilien-Analyse.

Sucht auf Kleinanzeigen.de (und, falls konfiguriert, über die
ImmoScout24-API) nach Grundstücken und Wohnungen von Privatanbietern
in Köln, Düsseldorf und Umgebung, bewertet sie und verschickt die
attraktivsten Treffer per E-Mail.

Aufruf: python -m immobilien_analyzer.run_analysis
"""
import logging
import sys
from pathlib import Path

from . import config
from .emailer import build_html, send_email
from .immoscout24 import ImmoScout24Client
from .kleinanzeigen import fetch_listings
from .scoring import rank_listings, score_listing
from .site_output import write_site_data

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main() -> int:
    is24 = ImmoScout24Client(config.IS24_CLIENT_ID, config.IS24_CLIENT_SECRET)
    all_scored = []
    seen_urls: set[str] = set()

    for city in config.CITIES:
        for property_type in config.PROPERTY_TYPES:
            logger.info("Suche %s in %s ...", property_type, city)

            listings = fetch_listings(
                city=city,
                property_type=property_type,
                max_price=config.MAX_PRICE,
                min_price=config.MIN_PRICE,
                radius_km=config.RADIUS_KM,
                max_pages=config.MAX_PAGES_PER_SEARCH,
            )
            listings += is24.search(city, property_type, config.MAX_PRICE, config.RADIUS_KM)

            new_listings = [l for l in listings if l.url not in seen_urls]
            seen_urls.update(l.url for l in new_listings)
            logger.info(
                "  -> %d Angebote gefunden (%d neu, %d bereits über andere Stadt gefunden)",
                len(listings), len(new_listings), len(listings) - len(new_listings),
            )

            all_scored.extend(score_listing(listing, city) for listing in new_listings)

    top = rank_listings(all_scored, config.TOP_N)
    subject = (
        f"🏡 Real Estate Analyzer – {len(top)} Top-Angebote"
        if top
        else "🏡 Real Estate Analyzer – keine neuen Treffer"
    )

    write_site_data(Path(config.SITE_DATA_PATH), top)

    if config.SMTP_USER and config.SMTP_PASSWORD:
        html = build_html(top, config.CITIES, config.MAX_PRICE)
        send_email(
            smtp_host=config.SMTP_HOST,
            smtp_port=config.SMTP_PORT,
            smtp_user=config.SMTP_USER,
            smtp_password=config.SMTP_PASSWORD,
            recipient=config.RECIPIENT_EMAIL,
            subject=subject,
            html_body=html,
        )
        logger.info("E-Mail an %s gesendet (%d Treffer).", config.RECIPIENT_EMAIL, len(top))
    else:
        logger.info("SMTP_USER/SMTP_PASSWORD nicht gesetzt — E-Mail-Versand übersprungen.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
