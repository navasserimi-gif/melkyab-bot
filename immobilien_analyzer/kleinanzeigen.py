"""
Scraper für Kleinanzeigen.de (private Verkäufer, Grundstücke & Wohnungen zum Kauf).

Hinweis: Die CSS-Selektoren und die URL-Struktur basieren auf dem seit
Jahren stabilen Kleinanzeigen-Layout (Karten mit der Klasse "aditem").
Sollte Kleinanzeigen sein HTML ändern, liefert fetch_listings() einfach
0 Ergebnisse statt eines Fehlers — bei 0 Treffern zuerst hier die
Selektoren/URL-Parameter prüfen.
"""
import logging
import re
import time
from dataclasses import dataclass
from typing import Optional
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

BASE_URL = "https://www.kleinanzeigen.de"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "de-DE,de;q=0.9",
}

# "kaufen" grenzt Mietangebote weitgehend aus; zusätzliche Absicherung
# per Keyword-Filter weiter unten.
QUERY_SLUGS = {
    "wohnung": "wohnung-kaufen",
    "grundstueck": "grundstueck-kaufen",
}

RENTAL_KEYWORDS = ("miete", "mieten", "kaltmiete", "warmmiete", "wg-zimmer")
COMMERCIAL_KEYWORDS = (
    "makler", "provision", "käuferprovision", "immobilien gmbh",
    "immobilienbüro", "vermittlung durch", "gewerblich",
    "fertighaus", "massivhaus", "typenhaus", "bausatzhaus",
    "musterhaus", "hausbaufirma", "bauunternehmen",
    # bekannte Fertighaus-Hersteller/-Vertriebe, die auf Kleinanzeigen
    # wie Privatangebote wirkende Werbeanzeigen schalten
    "allkauf", "town & country", "town and country", "streif haus",
    "weberhaus", "bien-zenker", "davinci haus", "living haus",
    "okal", "fingerhaus", "kern-haus", "heinz von heiden",
)

# Kleinanzeigens Orts-/Radius-Parameter werden nicht immer zuverlässig
# angewendet (in der Praxis beobachtet: Preis-Filter greift, Orts-Filter
# nicht). Deshalb zusätzlich clientseitig anhand der PLZ auf die Region
# Köln/Düsseldorf (~30-40 km) eingrenzen. Grobe, aber verlässliche
# Absicherung gegen bundesweite Treffer.
REGION_PLZ_PREFIXES = {"40", "41", "42", "45", "47", "50", "51", "53"}
_PLZ_RE = re.compile(r"\b(\d{5})\b")
# Verneinte/positive Erwähnungen ("kein Makler", "provisionsfrei",
# "maklerfrei") sind gerade das Gegenteil eines gewerblichen Hinweises
# und dürfen den Treffer nicht ausschließen.
_NEGATED_COMMERCIAL_RE = re.compile(
    r"\b(?:provisionsfrei|maklerfrei)\w*"
    r"|\b(?:kein|keine|keiner|ohne)\w*(?:\s+\w+){0,2}\s+\b(?:makler|provision)\w*",
    re.IGNORECASE,
)

_UMLAUT_MAP = str.maketrans({"ü": "ue", "ö": "oe", "ä": "ae", "ß": "ss"})


@dataclass
class Listing:
    title: str
    url: str
    price_eur: Optional[float]
    location: str
    size_sqm: Optional[float]
    property_type: str
    source: str = "kleinanzeigen"
    is_private: bool = True
    description_snippet: str = ""


def _to_float(text: str) -> Optional[float]:
    if not text:
        return None
    cleaned = re.sub(r"[^\d,.]", "", text)
    if not cleaned:
        return None
    cleaned = cleaned.replace(".", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _extract_size_sqm(text: str) -> Optional[float]:
    if not text:
        return None
    match = re.search(r"(\d[\d.]*)\s*m²", text)
    if not match:
        return None
    return _to_float(match.group(1))


def _looks_commercial(text: str) -> bool:
    cleaned = _NEGATED_COMMERCIAL_RE.sub(" ", text)
    lowered = cleaned.lower()
    return any(kw in lowered for kw in COMMERCIAL_KEYWORDS)


def _looks_like_rental(text: str) -> bool:
    lowered = text.lower()
    return any(kw in lowered for kw in RENTAL_KEYWORDS)


def _in_target_region(location: str) -> bool:
    match = _PLZ_RE.search(location or "")
    if not match:
        # Keine PLZ erkennbar - im Zweifel nicht ausschließen.
        return True
    return match.group(1)[:2] in REGION_PLZ_PREFIXES


def _city_slug(city: str) -> str:
    return quote(city.lower().translate(_UMLAUT_MAP).replace(" ", "-"))


def _build_search_url(property_type: str, city: str, max_price: int, min_price: int, radius_km: int) -> str:
    slug = QUERY_SLUGS[property_type]
    return (
        f"{BASE_URL}/s-{_city_slug(city)}/{slug}/k0"
        f"?maxPrice={max_price}&minPrice={min_price}&radius={radius_km}"
    )


def fetch_listings(
    city: str,
    property_type: str,
    max_price: int,
    min_price: int = 15000,
    radius_km: int = 30,
    max_pages: int = 2,
    request_delay_s: float = 2.0,
) -> list[Listing]:
    """Holt Angebote von Kleinanzeigen.de und filtert Miete/Gewerbe grob raus."""
    listings: list[Listing] = []
    base_url = _build_search_url(property_type, city, max_price, min_price, radius_km)

    for page in range(1, max_pages + 1):
        page_url = base_url if page == 1 else f"{base_url}&page={page}"
        try:
            resp = requests.get(page_url, headers=HEADERS, timeout=20)
        except requests.RequestException as exc:
            logger.warning("Kleinanzeigen-Anfrage fehlgeschlagen (%s, %s): %s", city, property_type, exc)
            break

        if resp.status_code != 200:
            logger.warning("Kleinanzeigen antwortete mit Status %s für %s", resp.status_code, page_url)
            break

        if resp.url != page_url:
            logger.info("Kleinanzeigen hat umgeleitet: %s -> %s", page_url, resp.url)

        soup = BeautifulSoup(resp.text, "lxml")
        cards = soup.select("article.aditem")
        if not cards:
            logger.info("Keine Angebotskarten gefunden auf %s (Seite %d)", page_url, page)
            break

        skipped_out_of_region = 0
        for card in cards:
            listing = _parse_card(card, city, property_type)
            if listing is None:
                continue
            haystack = f"{listing.title} {listing.description_snippet}"
            if _looks_like_rental(haystack):
                continue
            if _looks_commercial(haystack):
                continue
            if not _in_target_region(listing.location):
                skipped_out_of_region += 1
                continue
            listings.append(listing)

        if skipped_out_of_region:
            logger.info(
                "%d Treffer außerhalb der Zielregion (Köln/Düsseldorf) übersprungen.",
                skipped_out_of_region,
            )

        time.sleep(request_delay_s)

    return listings


def _parse_card(card, city: str, property_type: str) -> Optional[Listing]:
    try:
        link_el = card.select_one("a.ellipsis") or card.find("a", href=True)
        if link_el is None or not link_el.get("href"):
            return None
        href = link_el["href"]
        url = href if href.startswith("http") else f"{BASE_URL}{href}"
        title = link_el.get_text(strip=True)
        if not title:
            return None

        price_el = (
            card.select_one(".aditem-main--middle--price-shipping--price")
            or card.select_one(".aditem-main--top--right")
        )
        price_text = price_el.get_text(strip=True) if price_el else ""
        price = _to_float(price_text)

        desc_el = card.select_one(".aditem-main--middle--description")
        description = desc_el.get_text(" ", strip=True) if desc_el else ""

        location_el = card.select_one(".aditem-main--top--left")
        location = location_el.get_text(" ", strip=True) if location_el else city

        size = _extract_size_sqm(title) or _extract_size_sqm(description)

        commercial_badge = card.select_one(".badge-hint-pro-small-srp") is not None

        return Listing(
            title=title,
            url=url,
            price_eur=price,
            location=location,
            size_sqm=size,
            property_type=property_type,
            is_private=not commercial_badge,
            description_snippet=description[:300],
        )
    except Exception as exc:  # defensiv: eine kaputte Karte darf den ganzen Lauf nicht stoppen
        logger.debug("Konnte Angebotskarte nicht parsen: %s", exc)
        return None
