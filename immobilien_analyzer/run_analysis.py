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

from . import config
from .emailer import build_html, send_email
from .immoscout24 import ImmoScout24Client
from .ingest import push_to_webapp
from .kleinanzeigen import fetch_listings
from .scoring import rank_listings, score_listing

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main() -> int:
    is24 = ImmoScout24Client(config.IS24_CLIENT_ID, config.IS24_CLIENT_SECRET)
    all_scored = []

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
            logger.info("  -> %d Angebote gefunden", len(listings))

            all_scored.extend(score_listing(listing, city) for listing in listings)

    top = rank_listings(all_scored, config.TOP_N)
    subject = (
        f"🏡 Real Estate Analyzer – {len(top)} Top-Angebote"
        if top
        else "🏡 Real Estate Analyzer – keine neuen Treffer"
    )

    delivered = False

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
        delivered = True
    else:
        logger.info("SMTP_USER/SMTP_PASSWORD nicht gesetzt — E-Mail-Versand übersprungen.")

    if config.WEBAPP_INGEST_URL and config.WEBAPP_INGEST_TOKEN:
        if push_to_webapp(config.WEBAPP_INGEST_URL, config.WEBAPP_INGEST_TOKEN, top):
            logger.info("Ergebnisse an Web-App gesendet (%d Treffer).", len(top))
            delivered = True
    else:
        logger.info("WEBAPP_INGEST_URL/WEBAPP_INGEST_TOKEN nicht gesetzt — Web-App-Push übersprungen.")

    if not delivered:
        logger.error("Weder E-Mail noch Web-App konfiguriert — Ergebnisse gehen nur ins Log.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
