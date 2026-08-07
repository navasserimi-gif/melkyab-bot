"""
Konfiguration für den Video-Automatisierungs-Worker.

Alle Werte kommen aus Umgebungsvariablen, damit der Worker unabhängig
davon konfiguriert werden kann, wo er läuft (VPS, Modal, RunPod, ...).
Nichts davon wird von der Railway-Deployment des Telegram-Bots
(nixpacks.toml / Procfile) berührt — der Video-Worker ist ein eigener
Deploy, siehe docs/video-automation/README.md.
"""
import os

# --- Objekt-Speicher (Cloudflare R2, S3-kompatibel) -------------------
R2_ACCOUNT_ID = os.environ.get("R2_ACCOUNT_ID")
R2_ACCESS_KEY_ID = os.environ.get("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = os.environ.get("R2_SECRET_ACCESS_KEY")
R2_BUCKET_RAW = os.environ.get("R2_BUCKET_RAW", "immo-reels-raw")
R2_BUCKET_OUTPUT = os.environ.get("R2_BUCKET_OUTPUT", "immo-reels-output")
R2_ENDPOINT_URL = (
    os.environ.get("R2_ENDPOINT_URL")
    or (f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com" if R2_ACCOUNT_ID else None)
)
# Presigned URLs für Rohvideos/Outputs sind standardmäßig 7 Tage gültig.
PRESIGNED_URL_TTL_SECONDS = int(os.environ.get("PRESIGNED_URL_TTL_SECONDS", str(7 * 24 * 3600)))

# --- KI-Modelle ---------------------------------------------------------
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
# Flash für die günstige Massenanalyse aller Clips, Pro für die
# Feinbewertung der Top-Kandidaten (siehe vision_gemini.py).
GEMINI_MODEL_BULK = os.environ.get("GEMINI_MODEL_BULK", "gemini-2.5-flash")
GEMINI_MODEL_DEEP = os.environ.get("GEMINI_MODEL_DEEP", "gemini-2.5-pro")

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
CLAUDE_DIRECTOR_MODEL = os.environ.get("CLAUDE_DIRECTOR_MODEL", "claude-opus-4-6")

WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "large-v3")

# Lizenzierte Musikbibliothek (optional). Ohne Key fällt music.py auf die
# freie, lokal kuratierte Playlist zurück (siehe music.py).
EPIDEMIC_SOUND_API_KEY = os.environ.get("EPIDEMIC_SOUND_API_KEY")

# --- Technische Vorfilterung (scene_detect.py / technical_quality.py) --
MIN_SHARPNESS_SCORE = float(os.environ.get("MIN_SHARPNESS_SCORE", "0.35"))
MAX_SHAKE_SCORE = float(os.environ.get("MAX_SHAKE_SCORE", "0.55"))
MIN_EXPOSURE_SCORE = float(os.environ.get("MIN_EXPOSURE_SCORE", "0.3"))
SCENE_DETECT_THRESHOLD = float(os.environ.get("SCENE_DETECT_THRESHOLD", "27.0"))
MIN_SCENE_DURATION_SECONDS = float(os.environ.get("MIN_SCENE_DURATION_SECONDS", "1.2"))
# Ähnlichkeits-Schwelle (Perceptual Hash) ab der zwei Szenen als Duplikat gelten.
DUPLICATE_PHASH_DISTANCE = int(os.environ.get("DUPLICATE_PHASH_DISTANCE", "6"))

# --- Rendering -----------------------------------------------------------
FFMPEG_BINARY = os.environ.get("FFMPEG_BINARY", "ffmpeg")
# NVENC nutzen, falls der Worker eine NVIDIA-GPU hat (deutlich schneller bei 4K).
USE_NVENC = os.environ.get("USE_NVENC", "false").lower() == "true"
WORKDIR = os.environ.get("VIDEO_WORKDIR", "/tmp/immo-reels")

# --- Benachrichtigung (nutzt den bestehenden Telegram-Bot dieses Repos) --
BOT_TOKEN = os.environ.get("BOT_TOKEN")
NOTIFY_CHAT_ID = os.environ.get("VIDEO_NOTIFY_CHAT_ID") or os.environ.get("ADMIN_ID")

# --- Webhook-Server (wird von n8n angesprochen) --------------------------
WEBHOOK_HOST = os.environ.get("VIDEO_WEBHOOK_HOST", "0.0.0.0")
WEBHOOK_PORT = int(os.environ.get("VIDEO_WEBHOOK_PORT", "8080"))
WEBHOOK_SHARED_SECRET = os.environ.get("VIDEO_WEBHOOK_SHARED_SECRET")
