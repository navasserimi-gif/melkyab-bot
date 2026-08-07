"""
Kleiner HTTP-Server, den n8n anspricht, um einen Video-Job zu starten und
seinen Status abzufragen.

FastAPI statt eines schwergewichtigen Task-Queue-Systems, weil pro
Objekt nur 1 Job entsteht und Nebenläufigkeit hier kein Kernproblem ist
(siehe pipeline.py-Docstring zur Erweiterung auf eine echte Queue).

Endpunkte:
  POST /projects/{project_id}/run   -> startet die Pipeline im Hintergrund
  GET  /projects/{project_id}/status -> {"status": "running|done|failed", ...}
"""
from __future__ import annotations

import logging
import threading
import time

from fastapi import FastAPI, Header, HTTPException

from . import config, pipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="Immo-Reels Video Worker")

_jobs: dict[str, dict] = {}
_lock = threading.Lock()


def _check_secret(x_webhook_secret: str | None) -> None:
    if config.WEBHOOK_SHARED_SECRET and x_webhook_secret != config.WEBHOOK_SHARED_SECRET:
        raise HTTPException(status_code=401, detail="Ungültiges Shared Secret")


def _run_in_background(project_id: str) -> None:
    with _lock:
        _jobs[project_id] = {"status": "running", "started_at": time.time()}
    try:
        links = pipeline.run_project(project_id)
        with _lock:
            _jobs[project_id] = {"status": "done", "links": links, "finished_at": time.time()}
    except Exception as exc:
        logger.exception("Job %s fehlgeschlagen", project_id)
        with _lock:
            _jobs[project_id] = {"status": "failed", "error": str(exc), "finished_at": time.time()}


@app.post("/projects/{project_id}/run")
def run(project_id: str, x_webhook_secret: str | None = Header(default=None)):
    _check_secret(x_webhook_secret)
    with _lock:
        if _jobs.get(project_id, {}).get("status") == "running":
            raise HTTPException(status_code=409, detail="Job läuft bereits")
    thread = threading.Thread(target=_run_in_background, args=(project_id,), daemon=True)
    thread.start()
    return {"project_id": project_id, "status": "started"}


@app.get("/projects/{project_id}/status")
def status(project_id: str, x_webhook_secret: str | None = Header(default=None)):
    _check_secret(x_webhook_secret)
    job = _jobs.get(project_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Unbekanntes Projekt (noch nicht gestartet)")
    return {"project_id": project_id, **job}


@app.get("/health")
def health():
    return {"ok": True}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=config.WEBHOOK_HOST, port=config.WEBHOOK_PORT)
