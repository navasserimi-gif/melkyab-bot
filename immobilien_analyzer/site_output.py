"""Schreibt die Analyse-Ergebnisse als JSON für die statische PWA (docs/data.json)."""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from .scoring import ScoredListing

logger = logging.getLogger(__name__)


def scored_listing_to_dict(scored: ScoredListing) -> dict:
    listing = scored.listing
    return {
        "title": listing.title,
        "url": listing.url,
        "price_eur": listing.price_eur,
        "location": listing.location,
        "size_sqm": listing.size_sqm,
        "property_type": listing.property_type,
        "source": listing.source,
        "is_private": listing.is_private,
        "price_per_sqm": scored.price_per_sqm,
        "score": scored.score,
        "reasons": scored.reasons,
        "listing_age_days": listing.listing_age_days,
        "is_stale_opportunity": scored.is_stale_opportunity,
    }


def write_site_data(output_path: Path, scored_listings: list[ScoredListing]) -> None:
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "listings": [scored_listing_to_dict(s) for s in scored_listings],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Web-App-Daten geschrieben: %s (%d Treffer).", output_path, len(scored_listings))
