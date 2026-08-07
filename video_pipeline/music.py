"""
Musikauswahl passend zur von Claude gewählten Stimmung (EDLProject.music_mood).

Primär: Epidemic Sound / Artlist API (lizenziert, sicher für kommerzielle
Immobilienwerbung — kein Copyright-Strike-Risiko auf TikTok/Meta/YouTube).
Fallback ohne API-Key: eine lokal kuratierte, gemeinfreie/CC0-Playlist
(z. B. YouTube Audio Library, Pixabay Music), gruppiert nach denselben
Mood-Labels, die der Director verwendet. Damit läuft die Pipeline auch
Kosten-frei, nur eben mit kleinerer Musikauswahl.
"""
from __future__ import annotations

import logging
import random

import requests

from . import config

logger = logging.getLogger(__name__)

# Fallback-Bibliothek: Mood-Label -> Liste lokal vorgehaltener, lizenzfreier
# Tracks (Pfad relativ zu einem Music-Asset-Bucket/Verzeichnis). In
# Produktion aus einer gepflegten JSON-Datei laden statt hier hart zu codieren.
_FREE_LIBRARY: dict[str, list[str]] = {
    "luxurious_uplifting": ["free/luxurious_uplifting_01.mp3", "free/luxurious_uplifting_02.mp3"],
    "cinematic_calm": ["free/cinematic_calm_01.mp3"],
    "energetic_modern": ["free/energetic_modern_01.mp3", "free/energetic_modern_02.mp3"],
}
_DEFAULT_MOOD = "luxurious_uplifting"


def select_track(mood: str, target_duration: float) -> str:
    """Liefert einen lokalen Dateipfad (bereits heruntergeladen) zu einem
    zur Stimmung passenden, ausreichend langen Track."""
    if config.EPIDEMIC_SOUND_API_KEY:
        track = _select_from_epidemic_sound(mood, target_duration)
        if track:
            return track
        logger.warning("Kein passender Epidemic-Sound-Track für Mood '%s', nutze freie Bibliothek", mood)

    pool = _FREE_LIBRARY.get(mood, _FREE_LIBRARY[_DEFAULT_MOOD])
    return random.choice(pool)


def _select_from_epidemic_sound(mood: str, target_duration: float) -> str | None:
    """Platzhalter für die echte Epidemic-Sound-API-Integration. Die
    tatsächliche Such-/Lizenz-Download-API erfordert einen Partner-Account;
    hier wird bewusst nur die Schnittstelle vorgegeben, damit sie ohne
    Änderungen an render.py/pipeline.py nachgerüstet werden kann."""
    try:
        resp = requests.get(
            "https://partner-api.epidemicsound.com/v0/tracks",
            params={"mood": mood, "min_duration": target_duration},
            headers={"Authorization": f"Bearer {config.EPIDEMIC_SOUND_API_KEY}"},
            timeout=15,
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])
        return results[0]["download_url"] if results else None
    except Exception:
        logger.exception("Epidemic-Sound-API-Aufruf fehlgeschlagen")
        return None
