"""
Bewertet gefundene Angebote nach "Attraktivität" für Investment- bzw.
Kontakt-Zwecke.

Die Richtwerte (€/m²) sind grobe Schätzungen für 2026 und keine
Marktgarantie — insbesondere bei Grundstücken schwankt der Preis pro
Quadratmeter je nach Mikrolage extrem. Bei Bedarf hier anpassen.

Für "geschaeft" (Laden-/Gastro-Übernahme mit Ablöse) gibt es keinen
sinnvollen €/m²-Vergleich, daher entfällt dort die Richtwert-Bewertung.
"""
import re
from dataclasses import dataclass, field

from .kleinanzeigen import Listing

_PROVISION_FREE_RE = re.compile(r"\b(provisionsfrei|maklerfrei|keine\w*\s+provision|ohne\s+provision)\b", re.IGNORECASE)

BENCHMARK_PRICE_PER_SQM = {
    ("köln", "wohnung"): 4800,
    ("köln", "grundstueck"): 900,
    ("düsseldorf", "wohnung"): 5200,
    ("düsseldorf", "grundstueck"): 950,
}
DEFAULT_BENCHMARK = {"wohnung": 4500, "grundstueck": 800}
SQM_BENCHMARK_TYPES = {"wohnung", "grundstueck"}

PRIVATE_SELLER_BONUS = 1.15  # keine Käuferprovision zu erwarten
STALE_LISTING_BONUS = 1.3  # lange inseriert = gute Kontakt-Chance
DEFAULT_STALE_DAYS_THRESHOLD = 21


@dataclass
class ScoredListing:
    listing: Listing
    price_per_sqm: float | None
    benchmark_price_per_sqm: float | None
    score: float
    reasons: list[str] = field(default_factory=list)
    is_stale_opportunity: bool = False


def _benchmark_for(city: str, property_type: str) -> float:
    return BENCHMARK_PRICE_PER_SQM.get((city.lower(), property_type), DEFAULT_BENCHMARK[property_type])


def score_listing(
    listing: Listing,
    city: str,
    stale_days_threshold: int = DEFAULT_STALE_DAYS_THRESHOLD,
) -> ScoredListing:
    reasons: list[str] = []
    score = 1.0
    price_per_sqm = None
    benchmark = None

    if listing.property_type in SQM_BENCHMARK_TYPES:
        benchmark = _benchmark_for(city, listing.property_type)
        if listing.price_eur and listing.size_sqm and listing.size_sqm > 0:
            price_per_sqm = listing.price_eur / listing.size_sqm
            score = benchmark / price_per_sqm
            if score > 1:
                reasons.append(f"≈{round((score - 1) * 100)}% unter Richtwert ({int(benchmark)} €/m² in {city})")
            else:
                reasons.append(f"≈{round((1 - score) * 100)}% über Richtwert ({int(benchmark)} €/m² in {city})")
        else:
            reasons.append("Preis pro m² nicht ermittelbar – bitte manuell prüfen")

    if listing.is_private:
        score *= PRIVATE_SELLER_BONUS
        reasons.append("Privater Anbieter – vermutlich keine Käuferprovision")

    if _PROVISION_FREE_RE.search(f"{listing.title} {listing.description_snippet}"):
        score *= 1.1
        reasons.append("Ausdrücklich provisionsfrei beworben")

    is_stale = listing.listing_age_days is not None and listing.listing_age_days >= stale_days_threshold
    if is_stale:
        score *= STALE_LISTING_BONUS
        reasons.append(
            f"🎯 Seit {listing.listing_age_days} Tagen inseriert – vermutlich noch offen, gute Kontakt-Chance"
        )

    return ScoredListing(
        listing=listing,
        price_per_sqm=price_per_sqm,
        benchmark_price_per_sqm=benchmark,
        score=score,
        reasons=reasons,
        is_stale_opportunity=is_stale,
    )


def rank_listings(scored: list[ScoredListing], top_n: int) -> list[ScoredListing]:
    return sorted(scored, key=lambda s: s.score, reverse=True)[:top_n]
