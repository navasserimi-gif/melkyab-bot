"""
Diagnose-Skript: testet mehrere Kleinanzeigen-URL-Varianten und protokolliert,
ob der Orts-/Radius-Filter tatsächlich greift (Debug-Zweck, kein Teil der
täglichen Analyse).
"""
import logging

import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "de-DE,de;q=0.9",
}

CANDIDATES = [
    ("aktuell (bekannt kaputt)", "https://www.kleinanzeigen.de/s-koeln/wohnung-kaufen/k0?maxPrice=350000&minPrice=15000&radius=30"),
    ("nur Ortsslug, kein Keyword", "https://www.kleinanzeigen.de/s-koeln/k0"),
    ("Ortsslug vor k0, radius im Pfad", "https://www.kleinanzeigen.de/s-wohnung-kaufen/koeln/k0c196r30"),
    ("legacy suchanfrage.php", "https://www.kleinanzeigen.de/s-suchanfrage.php?keywords=wohnung+kaufen&locationStr=K%C3%B6ln&radius=30&maxPrice=350000"),
    ("Ortsslug + PLZ-Radius Pfadsegment", "https://www.kleinanzeigen.de/s-wohnung-kaufen/koeln/c196r30"),
]


def probe(label: str, url: str) -> None:
    logger.info("=== %s ===", label)
    logger.info("Angefragt: %s", url)
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20, allow_redirects=True)
    except requests.RequestException as exc:
        logger.error("Fehler: %s", exc)
        return

    logger.info("Status: %s | Finale URL: %s", resp.status_code, resp.url)
    if resp.status_code != 200:
        logger.info("Kein 200 - Body-Anfang: %s", resp.text[:300])
        return

    soup = BeautifulSoup(resp.text, "lxml")
    cards = soup.select("article.aditem")
    logger.info("Gefundene Karten: %d", len(cards))
    for card in cards[:5]:
        loc_el = card.select_one(".aditem-main--top--left")
        title_el = card.select_one("a.ellipsis") or card.find("a", href=True)
        loc = loc_el.get_text(" ", strip=True) if loc_el else "?"
        title = title_el.get_text(strip=True) if title_el else "?"
        logger.info("  - [%s] %s", loc, title[:70])


if __name__ == "__main__":
    for label, url in CANDIDATES:
        probe(label, url)
