"""
Backend für die Real-Estate-Analyzer-PWA.

Liefert die statische Web-App aus und stellt zwei API-Endpunkte bereit:
  - GET  /api/listings  -> aktuelle (zuletzt empfangene) Analyse-Ergebnisse
  - POST /api/ingest     -> nimmt die tägliche Analyse (aus GitHub Actions)
                            entgegen und speichert sie

/api/ingest ist per Bearer-Token (INGEST_TOKEN) geschützt.
"""
import json
import os
from pathlib import Path

from flask import Flask, abort, jsonify, request, send_from_directory

STATIC_DIR = Path(__file__).parent / "static"
DATA_FILE = Path(__file__).parent / "data" / "latest.json"
INGEST_TOKEN = os.environ.get("INGEST_TOKEN")

app = Flask(__name__, static_folder=str(STATIC_DIR), static_url_path="")


@app.get("/")
def index():
    return send_from_directory(STATIC_DIR, "index.html")


@app.get("/api/listings")
def get_listings():
    if not DATA_FILE.exists():
        return jsonify({"generated_at": None, "listings": []})
    return jsonify(json.loads(DATA_FILE.read_text(encoding="utf-8")))


@app.post("/api/ingest")
def ingest():
    if not INGEST_TOKEN:
        abort(503, "INGEST_TOKEN ist auf dem Server nicht konfiguriert.")

    auth_header = request.headers.get("Authorization", "")
    token = auth_header.removeprefix("Bearer ").strip()
    if token != INGEST_TOKEN:
        abort(401)

    payload = request.get_json(force=True, silent=True)
    if not isinstance(payload, dict) or "listings" not in payload:
        abort(400, "Erwarte JSON mit Feld 'listings'.")

    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return jsonify({"status": "ok", "count": len(payload.get("listings", []))})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    app.run(host="0.0.0.0", port=port)
