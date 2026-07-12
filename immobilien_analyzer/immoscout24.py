"""
Platzhalter-Adapter für die offizielle ImmoScout24-API.

Wird automatisch aktiv, sobald IS24_CLIENT_ID und IS24_CLIENT_SECRET als
Umgebungsvariablen/GitHub Secrets gesetzt sind. Ohne Zugangsdaten liefert
search() einfach eine leere Liste, der Rest der Analyse läuft unverändert
mit den Kleinanzeigen-Treffern weiter.

ImmoScout24 nutzt für seine Partner-API historisch OAuth 1.0a (nicht
OAuth2) und erfordert vor dem ersten automatisierten Zugriff eine
einmalige, interaktive Autorisierung (Access Token + Access Token Secret).
Das lässt sich nicht headless in einer Cron-Job vorwegnehmen.

TODO, sobald ein IS24-Partner-Zugang vorliegt:
  1. Einmalig die OAuth1-Autorisierung durchführen und Access Token +
     Access Token Secret erzeugen.
  2. Diese als IS24_ACCESS_TOKEN / IS24_ACCESS_TOKEN_SECRET hinterlegen.
  3. search() unten mit dem echten Aufruf der IS24 Real Estate API füllen
     und die Ergebnisse als kleinanzeigen.Listing-Objekte zurückgeben,
     damit scoring.py sie identisch weiterverarbeiten kann.
"""
import logging

logger = logging.getLogger(__name__)


class ImmoScout24Client:
    def __init__(self, client_id: str | None, client_secret: str | None):
        self.client_id = client_id
        self.client_secret = client_secret
        self.enabled = bool(client_id and client_secret)

    def search(self, city: str, property_type: str, max_price: int, radius_km: int = 30):
        if not self.enabled:
            logger.info(
                "ImmoScout24-Adapter übersprungen: IS24_CLIENT_ID/IS24_CLIENT_SECRET nicht gesetzt."
            )
            return []
        logger.warning(
            "ImmoScout24-Zugangsdaten gefunden, aber die API-Anbindung ist noch nicht "
            "implementiert (siehe TODO in immobilien_analyzer/immoscout24.py)."
        )
        return []
