"""Schickt die Analyse-Ergebnisse optional an das Web-App-Backend (Railway)."""
import logging
from datetime import datetime, timezone

import requests

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
    }


def push_to_webapp(url: str, token: str, scored_listings: list[ScoredListing]) -> bool:
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "listings": [scored_listing_to_dict(s) for s in scored_listings],
    }
    try:
        resp = requests.post(
            url,
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        resp.raise_for_status()
        return True
    except requests.RequestException as exc:
        logger.error("Konnte Ergebnisse nicht an Web-App senden (%s): %s", url, exc)
        return False
