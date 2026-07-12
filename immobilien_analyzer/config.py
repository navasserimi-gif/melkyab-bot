"""
Konfiguration für den täglichen Immobilien-Analysator.

Alle Werte können per Umgebungsvariable (bzw. GitHub Actions Secret)
überschrieben werden, ohne den Code anzufassen.
"""
import os

MAX_PRICE = int(os.environ.get("MAX_PRICE", "350000"))
MIN_PRICE = int(os.environ.get("MIN_PRICE", "15000"))  # filtert versehentliche Mietangebote raus
CITIES = [c.strip() for c in os.environ.get("CITIES", "Köln,Düsseldorf").split(",") if c.strip()]
# Umkreis für Wohnungen/Grundstücke. "geschaeft" (Ablöse-Übernahmen)
# ignoriert das und bleibt strikt auf Köln/Düsseldorf selbst beschränkt.
RADIUS_KM = int(os.environ.get("RADIUS_KM", "50"))
PROPERTY_TYPES = ["wohnung", "grundstueck", "geschaeft"]
TOP_N = int(os.environ.get("TOP_N", "12"))
MAX_PAGES_PER_SEARCH = int(os.environ.get("MAX_PAGES_PER_SEARCH", "2"))
# Ab diesem Anzeigenalter (Tage) gilt ein Angebot als "lange inseriert" -
# ein Hinweis darauf, dass der Verkäufer evtl. noch keinen Käufer/
# Nachmieter gefunden hat und offen für Unterstützung sein könnte.
STALE_DAYS_THRESHOLD = int(os.environ.get("STALE_DAYS_THRESHOLD", "21"))

SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "465"))
SMTP_USER = os.environ.get("SMTP_USER")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")
RECIPIENT_EMAIL = os.environ.get("RECIPIENT_EMAIL") or SMTP_USER or "navasserimi@gmail.com"

IS24_CLIENT_ID = os.environ.get("IS24_CLIENT_ID")
IS24_CLIENT_SECRET = os.environ.get("IS24_CLIENT_SECRET")

# JSON-Datei, die die statische PWA unter docs/ ausliest (GitHub Pages).
SITE_DATA_PATH = os.environ.get("SITE_DATA_PATH", "docs/data.json")
