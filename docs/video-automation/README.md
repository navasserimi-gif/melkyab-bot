# Video-Automatisierung — Setup & Quickstart

Siehe [ARCHITEKTUR.md](./ARCHITEKTUR.md) für die vollständige Begründung
der Architektur. Diese Datei ist die praktische Inbetriebnahme-Anleitung.

## Überblick

Dieses Feature besteht aus drei getrennten Deploy-Einheiten:

1. **`video_pipeline/`** — der eigentliche Worker (Analyse + Rendering).
   Läuft NICHT auf Railway zusammen mit dem Telegram-Bot, sondern als
   eigener Container/Prozess mit FFmpeg und ausreichend Rechenleistung.
2. **n8n** (`n8n/real-estate-video-workflow.json`) — Orchestrierung/Trigger.
3. **Cloudflare R2** — Speicher für Roh- und Output-Videos.

## 1. Cloudflare R2 einrichten

1. R2-Bucket `immo-reels-raw` und `immo-reels-output` anlegen (Namen sind
   über `R2_BUCKET_RAW`/`R2_BUCKET_OUTPUT` konfigurierbar).
2. API-Token mit R2-Schreibrechten erstellen → `R2_ACCESS_KEY_ID`,
   `R2_SECRET_ACCESS_KEY`, `R2_ACCOUNT_ID`.
3. Rohvideos eines Objekts nach `raw/{project_id}/` hochladen (z. B. per
   `rclone` oder dem Cloudflare-Dashboard). `project_id` frei wählbar,
   z. B. `koeln-musterstrasse-12`.

## 2. Worker deployen

```bash
docker build -f Dockerfile.video-worker -t immo-reels-worker .
docker run -p 8080:8080 \
  -e R2_ACCOUNT_ID=... -e R2_ACCESS_KEY_ID=... -e R2_SECRET_ACCESS_KEY=... \
  -e GEMINI_API_KEY=... -e ANTHROPIC_API_KEY=... \
  -e BOT_TOKEN=... -e VIDEO_NOTIFY_CHAT_ID=... \
  -e VIDEO_WEBHOOK_SHARED_SECRET=... \
  --gpus all \
  immo-reels-worker
```

`--gpus all` ist optional, aktiviert aber NVENC (`USE_NVENC=true`) für
deutlich schnelleres Rendering von 4K/60fps-Ausgangsmaterial. Ohne GPU
läuft alles über `libx264`, nur langsamer.

Empfohlene Hosts: eine GPU-VM (Hetzner/Lambda/RunPod) oder ein Serverless-
GPU-Anbieter wie Modal — je nach erwartetem Volumen an Objekten/Monat.

Alle Umgebungsvariablen: siehe `video_pipeline/config.py`.

## 3. n8n einrichten

1. `n8n/real-estate-video-workflow.json` importieren.
2. Umgebungsvariablen in n8n setzen: `VIDEO_WORKER_URL` (z. B.
   `https://worker.example.com`), `VIDEO_WEBHOOK_SHARED_SECRET`
   (identisch zum Worker), `ADMIN_ID`.
3. Telegram-Credential `melkyab-bot-telegram` mit dem bestehenden
   `BOT_TOKEN` dieses Repos anlegen (Bot wird für Fehleralarme wiederverwendet).
4. Den n8n-Webhook (`.../webhook/start-video-project`) aufrufen, sobald ein
   Projektordner vollständig in R2 liegt:
   ```bash
   curl -X POST https://<n8n-host>/webhook/start-video-project \
     -H "Content-Type: application/json" \
     -d '{"project_id": "koeln-musterstrasse-12"}'
   ```

## 4. Manueller Testlauf (ohne n8n)

```bash
pip install -r requirements-video.txt
python -m video_pipeline.pipeline koeln-musterstrasse-12
```

Gibt beim Erfolg die presigned R2-Links der drei Plattform-Varianten aus
und schickt zusätzlich die Telegram-Fertig-Meldung.

## 5. Google-Drive-Inbox (optional)

Wer keinen R2-Client nutzen möchte, kann stattdessen einen Drive-Ordner als
Posteingang verwenden. Dafür wird ein zusätzlicher, kleiner Sync-Schritt
benötigt (z. B. ein n8n-Google-Drive-Trigger-Node + Datei-Download +
Re-Upload nach R2, oder ein `rclone sync gdrive:Uploads r2:immo-reels-raw`
Cronjob) — bewusst nicht Teil von `video_pipeline/`, da Drive für
GB-große 4K-Dateien deutlich langsamer/quota-limitierter ist als ein
direkter R2-Upload und dieser Schritt unabhängig von der eigentlichen
KI-Pipeline austauschbar bleiben soll.
