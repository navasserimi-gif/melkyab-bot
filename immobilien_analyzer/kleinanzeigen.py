"""
Scraper für Kleinanzeigen.de (private Verkäufer: Wohnungen/Grundstücke zum
Kauf, Geschäfte/Gastronomie zur Übernahme mit Ablöse).

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
from datetime import date, datetime, timedelta
from typing import Optional

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
# per Keyword-Filter weiter unten. "geschaeft" sucht gezielt nach
# Laden-/Gastro-Übernahmen mit Ablöse (kein Kauf, sondern Mietübernahme +
# Ablösesumme für Inventar/Einrichtung).
#
# Mehrere Suchbegriffe pro Kategorie, weil Kleinanzeigens Seiten-Blätterung
# nicht zuverlässig funktioniert (Seite 2 liefert oft dieselben Treffer wie
# Seite 1) - mehr unterschiedliche Suchanfragen sind der einzige Weg, mehr
# Rohtreffer zu bekommen, aus denen dann streng gefiltert wird.
QUERY_SLUGS = {
    "wohnung": ["wohnung-kaufen", "eigentumswohnung", "haus-kaufen", "eigentumswohnung-kaufen"],
    "grundstueck": ["grundstueck-kaufen", "baugrundstueck", "bauplatz", "grundstueck-privat"],
    "geschaeft": ["ablöse", "ladenlokal", "gastronomie-übernahme", "imbiss-übernahme"],
}

# Geschäfte/Ablöse-Übernahmen sollen NUR aus Köln oder Düsseldorf selbst
# kommen (kein Umkreis), Wohnungen/Grundstücke aus der weiteren Region.
STRICT_CITY_ONLY_TYPES = {"geschaeft"}

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

# Manche Anzeigen betreffen Immobilien im Ausland, obwohl das Konto/die
# Kontakt-PLZ in Deutschland liegt (z.B. Ferienhaus auf Kreta). Per
# Stichwort im Titel aussortieren, da die PLZ-Prüfung das nicht erkennt.
FOREIGN_LOCATION_KEYWORDS = (
    "kreta", "mallorca", "türkei", "spanien", "italien", "griechenland",
    "kroatien", "bulgarien", "ungarn", "frankreich", "österreich",
    "schweiz", "portugal", "zypern", "thailand", "dubai",
)

# Kleinanzeigens Orts-Parameter in der Such-URL wird nachweislich komplett
# ignoriert (Suchen für "Köln" und "Düsseldorf" liefern byte-identische
# bundesweite Ergebnisse). Deshalb wird nur noch EINMAL pro Suchbegriff
# gesucht (nicht mehr pro Stadt dupliziert) und jeder Treffer anschließend
# clientseitig anhand der PLZ einer Stadt zugeordnet bzw. verworfen.
# Für Wohnungen/Grundstücke: grobe Region um Köln/Düsseldorf (~50 km).
REGION_PLZ_PREFIXES = {"40", "41", "42", "45", "46", "47", "50", "51", "53"}
# Grobe PLZ-Präfix-Zuordnung zur nächstgelegenen der beiden Zielstädte,
# nur für die Richtwert-Auswahl beim Scoring relevant.
PREFIX_TO_CITY = {
    "40": "düsseldorf", "41": "düsseldorf", "42": "düsseldorf",
    "45": "düsseldorf", "46": "düsseldorf", "47": "düsseldorf",
    "50": "köln", "51": "köln", "53": "köln",
}
# Für Geschäfte/Ablöse: nur die Städte selbst, enger PLZ-Bereich.
STRICT_CITY_PLZ_RANGES = {
    "köln": (50667, 51149),
    "düsseldorf": (40200, 40629),
}
_PLZ_RE = re.compile(r"\b(\d{5})\b")

# Verneinte/positive Erwähnungen ("kein Makler", "provisionsfrei",
# "maklerfrei") sind gerade das Gegenteil eines gewerblichen Hinweises
# und dürfen den Treffer nicht ausschließen.
_NEGATED_COMMERCIAL_RE = re.compile(
    r"\b(?:provisionsfrei|maklerfrei)\w*"
    r"|\b(?:kein|keine|keiner|ohne)\w*(?:\s+\w+){0,2}\s+\b(?:makler|provision)\w*",
    re.IGNORECASE,
)

# Kleinanzeigen zeigt auf jeder Anzeigenseite (gesetzlich vorgeschrieben,
# Impressumspflicht) explizit "Privater Anbieter" oder "Gewerblicher
# Anbieter" im Profil-Kasten des Verkäufers. Das ist deutlich
# zuverlässiger als ein geratenes CSS-Badge auf der Trefferliste.
_COMMERCIAL_SELLER_RE = re.compile(r"gewerblich(?:e[rn]?)?\s+(?:anbieter|nutzer)", re.IGNORECASE)
_PRIVATE_SELLER_RE = re.compile(r"privat(?:e[rn]?)?\s+(?:anbieter|nutzer)", re.IGNORECASE)

_MONTHS_DE = {
    "jan": 1, "feb": 2, "mär": 3, "maer": 3, "apr": 4, "mai": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "okt": 10, "nov": 11, "dez": 12,
}


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
    listing_age_days: Optional[int] = None
    matched_city: Optional[str] = None


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


def _looks_foreign(text: str) -> bool:
    lowered = text.lower()
    return any(kw in lowered for kw in FOREIGN_LOCATION_KEYWORDS)


def _in_target_region(location: str) -> bool:
    match = _PLZ_RE.search(location or "")
    if not match:
        # Keine PLZ erkennbar - im Zweifel nicht ausschließen.
        return True
    return match.group(1)[:2] in REGION_PLZ_PREFIXES


def _matched_strict_city(location: str, cities: list[str]) -> Optional[str]:
    """Für Geschäfte/Ablöse: gibt die erste Stadt aus `cities` zurück, deren
    engem PLZ-Bereich der Treffer entspricht, sonst None (= verwerfen)."""
    match = _PLZ_RE.search(location or "")
    if not match:
        return None
    plz = int(match.group(1))
    for city in cities:
        plz_range = STRICT_CITY_PLZ_RANGES.get(city.lower())
        if plz_range and plz_range[0] <= plz <= plz_range[1]:
            return city
    return None


def _guess_nearby_city(location: str, cities: list[str]) -> str:
    """Für Wohnungen/Grundstücke: nur für die Richtwert-Auswahl beim Scoring
    relevant, nicht für die Region-Filterung selbst. Fällt auf die erste
    konfigurierte Stadt zurück, wenn nichts Genaueres erkennbar ist."""
    match = _PLZ_RE.search(location or "")
    if match:
        guessed = PREFIX_TO_CITY.get(match.group(1)[:2])
        if guessed:
            for city in cities:
                if city.lower() == guessed:
                    return city
    return cities[0] if cities else ""


# Platzhalter für das Ort-Segment der URL. Erwiesenermaßen ohne Effekt auf
# die Ergebnisse (Suchen mit "koeln" und "duesseldorf" liefern identische
# bundesweite Treffer) - wird trotzdem benötigt, weil dieses URL-Muster
# (<ort>/<suchbegriff>/k0) das einzige ist, das überhaupt Ergebniskarten
# liefert. Die eigentliche Regions-Filterung passiert clientseitig.
_PLACEHOLDER_LOCATION_SLUG = "koeln"


def _build_search_url(slug: str, property_type: str, max_price: int, min_price: int, radius_km: int) -> str:
    url = f"{BASE_URL}/s-{_PLACEHOLDER_LOCATION_SLUG}/{slug}/k0?maxPrice={max_price}&minPrice={min_price}"
    if property_type not in STRICT_CITY_ONLY_TYPES:
        url += f"&radius={radius_km}"
    return url


def _parse_listing_age_days(text: str, today: Optional[date] = None) -> Optional[int]:
    """Best-effort: leitet aus Kleinanzeigen-Datumsangaben ('Heute', 'Gestern',
    '17.05.2025', '17. Mai') das Alter der Anzeige in Tagen ab. Gibt None
    zurück, wenn kein Datum erkennbar ist (lieber nichts anzeigen als raten)."""
    if not text:
        return None
    today = today or date.today()
    lowered = text.lower()

    if "heute" in lowered:
        return 0
    if "gestern" in lowered:
        return 1

    match = re.search(r"\b(\d{1,2})\.(\d{1,2})\.(\d{4})\b", text)
    if match:
        day, month, year = (int(g) for g in match.groups())
        try:
            listed = date(year, month, day)
        except ValueError:
            return None
        return max((today - listed).days, 0)

    match = re.search(r"\b(\d{1,2})\.\s*(\w{3,4})\b", lowered)
    if match:
        day = int(match.group(1))
        month = _MONTHS_DE.get(match.group(2)[:3])
        if month:
            year = today.year
            try:
                listed = date(year, month, day)
            except ValueError:
                return None
            if listed > today:
                listed = date(year - 1, month, day)
            return max((today - listed).days, 0)

    return None


def _verify_private_seller(url: str, timeout: int = 20) -> Optional[bool]:
    """Ruft die Anzeigenseite ab und liest das gesetzlich vorgeschriebene
    Anbieter-Kennzeichen ('Privater Anbieter' / 'Gewerblicher Anbieter').
    Gibt True/False bei eindeutigem Befund zurück, sonst None."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
    except requests.RequestException as exc:
        logger.debug("Anzeigenseite nicht abrufbar (%s): %s", url, exc)
        return None

    if resp.status_code != 200:
        return None

    text = BeautifulSoup(resp.text, "lxml").get_text(" ", strip=True)
    if _COMMERCIAL_SELLER_RE.search(text):
        return False
    if _PRIVATE_SELLER_RE.search(text):
        return True
    return None


def fetch_listings(
    cities: list[str],
    property_type: str,
    max_price: int,
    min_price: int = 15000,
    radius_km: int = 30,
    max_pages: int = 2,
    request_delay_s: float = 2.0,
    verify_seller_type: bool = True,
    max_seller_checks: int = 120,
) -> list[Listing]:
    """Holt Angebote von Kleinanzeigen.de (über alle Suchbegriff-Varianten
    der Kategorie) und filtert Miete/Gewerbe/Ausland grob raus.

    Sucht pro Suchbegriff nur EINMAL (nicht mehr einmal je Stadt): Kleinanzeigen
    ignoriert den Ort in der Such-URL nachweislich, wiederholte Suchen pro
    Stadt lieferten byte-identische Ergebnisse. Jeder Treffer wird nach dem
    Abruf per PLZ einer der konfigurierten Städte zugeordnet (`matched_city`).
    """
    listings: list[Listing] = []
    seen_urls_in_search: set[str] = set()
    strict_city = property_type in STRICT_CITY_ONLY_TYPES
    seller_checks_done = 0

    for slug in QUERY_SLUGS[property_type]:
        seller_checks_done = _fetch_for_slug(
            slug=slug,
            cities=cities,
            property_type=property_type,
            max_price=max_price,
            min_price=min_price,
            radius_km=radius_km,
            max_pages=max_pages,
            request_delay_s=request_delay_s,
            verify_seller_type=verify_seller_type,
            max_seller_checks=max_seller_checks,
            seller_checks_done=seller_checks_done,
            strict_city=strict_city,
            seen_urls_in_search=seen_urls_in_search,
            listings=listings,
        )

    return listings


def _fetch_for_slug(
    slug: str,
    cities: list[str],
    property_type: str,
    max_price: int,
    min_price: int,
    radius_km: int,
    max_pages: int,
    request_delay_s: float,
    verify_seller_type: bool,
    max_seller_checks: int,
    seller_checks_done: int,
    strict_city: bool,
    seen_urls_in_search: set[str],
    listings: list[Listing],
) -> int:
    """Durchsucht eine einzelne Suchbegriff-Variante (bundesweit, da der
    Ort-Parameter ignoriert wird) und hängt Treffer an `listings` an. Gibt
    den aktualisierten seller_checks_done-Zähler zurück."""
    base_url = _build_search_url(slug, property_type, max_price, min_price, radius_km)

    for page in range(1, max_pages + 1):
        page_url = base_url if page == 1 else f"{base_url}&page={page}"
        try:
            resp = requests.get(page_url, headers=HEADERS, timeout=20)
        except requests.RequestException as exc:
            logger.warning("Kleinanzeigen-Anfrage fehlgeschlagen (%s): %s", property_type, exc)
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

        card_urls = []
        for c in cards:
            a = c.select_one("a.ellipsis") or c.find("a", href=True)
            href = a["href"] if a and a.get("href") else None
            if href:
                card_urls.append(href if href.startswith("http") else f"{BASE_URL}{href}")
        if page > 1 and card_urls and all(u in seen_urls_in_search for u in card_urls):
            logger.info("Seite %d liefert identische Treffer wie zuvor - Paginierung greift nicht, breche ab.", page)
            break

        sample_locations = [
            (c.select_one(".aditem-main--top--left").get_text(" ", strip=True) if c.select_one(".aditem-main--top--left") else "?")
            for c in cards[:5]
        ]
        logger.info("Rohe Orte (ungefiltert, erste 5 von %d): %s", len(cards), sample_locations)

        skipped_out_of_region = 0
        skipped_foreign = 0
        skipped_duplicate = 0
        skipped_commercial_confirmed = 0
        skipped_seller_unconfirmed = 0
        with_age = 0
        for card in cards:
            listing = _parse_card(card, property_type)
            if listing is None:
                continue
            if listing.url in seen_urls_in_search:
                skipped_duplicate += 1
                continue
            seen_urls_in_search.add(listing.url)

            haystack = f"{listing.title} {listing.description_snippet}"
            if _looks_like_rental(haystack):
                continue
            if _looks_commercial(haystack):
                continue
            if _looks_foreign(listing.title):
                skipped_foreign += 1
                continue

            if strict_city:
                matched = _matched_strict_city(listing.location, cities)
                if matched is None:
                    skipped_out_of_region += 1
                    continue
                listing.matched_city = matched
            else:
                if not _in_target_region(listing.location):
                    skipped_out_of_region += 1
                    continue
                listing.matched_city = _guess_nearby_city(listing.location, cities)

            if verify_seller_type and seller_checks_done < max_seller_checks:
                seller_checks_done += 1
                time.sleep(1.0)
                confirmed_private = _verify_private_seller(listing.url)
                if confirmed_private is False:
                    skipped_commercial_confirmed += 1
                    continue
                if confirmed_private is None:
                    # Kein eindeutiges Anbieter-Kennzeichen gefunden - im
                    # Zweifel ausschließen, statt versehentlich einen
                    # gewerblichen Anbieter/Konkurrenten durchzulassen.
                    skipped_seller_unconfirmed += 1
                    continue
                listing.is_private = True

            if listing.listing_age_days is not None:
                with_age += 1
            listings.append(listing)

        if skipped_out_of_region or skipped_foreign or skipped_duplicate or skipped_commercial_confirmed or skipped_seller_unconfirmed:
            logger.info(
                "Übersprungen: %d außerhalb Zielregion, %d Ausland, %d Duplikate, "
                "%d bestätigt gewerblich, %d Anbietertyp nicht eindeutig (Seite %d).",
                skipped_out_of_region, skipped_foreign, skipped_duplicate,
                skipped_commercial_confirmed, skipped_seller_unconfirmed, page,
            )
        logger.info("%d/%d Treffer mit erkennbarem Anzeigedatum.", with_age, len(cards))

        time.sleep(request_delay_s)

    return seller_checks_done


def _parse_card(card, property_type: str) -> Optional[Listing]:
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
        location = location_el.get_text(" ", strip=True) if location_el else ""

        # Beobachtetes Layout: das Anzeigedatum steht meist als eigenes
        # Element neben dem Preis oder unten im Karten-Footer. Da die
        # genaue Klasse unsicher ist, wird zusätzlich der komplette
        # Kartentext als Fallback nach einem Datumsmuster durchsucht.
        date_el = card.select_one(".aditem-main--top--right") or card.select_one(".aditem-main--bottom")
        date_text = date_el.get_text(" ", strip=True) if date_el else ""
        listing_age_days = _parse_listing_age_days(date_text)
        if listing_age_days is None:
            listing_age_days = _parse_listing_age_days(card.get_text(" ", strip=True))

        size = _extract_size_sqm(title) or _extract_size_sqm(description)

        return Listing(
            title=title,
            url=url,
            price_eur=price,
            location=location,
            size_sqm=size,
            property_type=property_type,
            # Nur ein vorläufiger Platzhalter - die verbindliche Prüfung
            # passiert in fetch_listings() anhand der Anzeigenseite selbst.
            is_private=False,
            description_snippet=description[:300],
            listing_age_days=listing_age_days,
        )
    except Exception as exc:  # defensiv: eine kaputte Karte darf den ganzen Lauf nicht stoppen
        logger.debug("Konnte Angebotskarte nicht parsen: %s", exc)
        return None
