"""
Orchestriert den kompletten Ablauf für EIN Objekt/Projekt von "Rohvideos
liegen in R2" bis "drei fertige 9:16-Videos liegen im Output-Bucket".

Wird von webhook_server.py (n8n-Trigger) oder direkt per CLI aufgerufen:
    python -m video_pipeline.pipeline <project_id>

Bewusst als Klartext-Sequenz statt als verteilte Task-Queue gehalten, damit
der Ablauf für die erste Version leicht nachvollziehbar und debugbar
bleibt. Für höheren Durchsatz (mehrere Objekte parallel) siehe
ARCHITEKTUR.md, Abschnitt "Erweiterbarkeit" (Celery/RQ-Queue vor diesem
Modul).
"""
from __future__ import annotations

import asyncio
import logging
import shutil
from pathlib import Path

from . import config, director_claude, music, notify, render, scene_detect, storage, technical_quality, vision_gemini
from .models import Platform, Scene

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def _project_workdir(project_id: str) -> Path:
    d = Path(config.WORKDIR) / project_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def run_project(project_id: str) -> dict[str, str]:
    workdir = _project_workdir(project_id)
    raw_dir = workdir / "raw"

    # 1. Rohvideos laden
    keys = storage.list_raw_clips(project_id)
    if not keys:
        raise RuntimeError(f"Keine Rohvideos für Projekt {project_id} in R2 gefunden")
    video_paths: dict[str, str] = {key: str(storage.download(key, str(raw_dir))) for key in keys}
    logger.info("%d Rohvideos heruntergeladen", len(video_paths))

    # 2. Schnitterkennung: jede Rohdatei in bewertbare Einzelszenen zerlegen
    all_scenes: list[Scene] = []
    for key, path in video_paths.items():
        all_scenes.extend(scene_detect.detect_scenes(path, key))
    logger.info("%d Rohszenen insgesamt", len(all_scenes))

    # 3. Günstige technische Vorfilterung (OpenCV, kein API-Call)
    for scene in all_scenes:
        scene.technical = technical_quality.analyze_scene(
            video_paths[scene.source_key], scene.start_seconds, scene.end_seconds
        )
    usable_scenes = [s for s in all_scenes if s.technical and s.technical.is_usable]
    logger.info(
        "%d/%d Szenen bestehen die technische Vorfilterung (Rest: verwackelt/unscharf/Belichtung)",
        len(usable_scenes), len(all_scenes),
    )

    # 4. Semantische Analyse (Gemini) nur auf den technisch brauchbaren Szenen
    vision_gemini.analyze_all(usable_scenes, video_paths)

    # 5. Duplikate erkennen (pHash) und aus dem Kandidatenpool ausschließen
    scene_detect.mark_duplicates(usable_scenes, video_paths)
    final_pool = [s for s in usable_scenes if s.analysis and not s.analysis.is_duplicate_of]
    logger.info("%d einzigartige, nutzbare Szenen für die Regie verfügbar", len(final_pool))

    # 6. Kreative Entscheidung je Plattform (Claude)
    edl_by_platform = director_claude.build_all_platform_edls(project_id, final_pool)

    # 7. Musik auswählen + rendern je Plattform
    output_keys: dict[str, str] = {}
    for platform, edl_project in edl_by_platform.items():
        track_key = music.select_track(edl_project.music_mood, edl_project.total_duration)
        music_path = storage.download(track_key, str(workdir / "music"))
        output_path = render.render_platform_variant(edl_project, video_paths, str(music_path), str(workdir))
        r2_key = storage.upload_output(output_path, project_id, Path(output_path).name)
        output_keys[platform.value] = r2_key

    links = {platform: storage.presigned_url(key) for platform, key in output_keys.items()}

    shutil.rmtree(workdir, ignore_errors=True)
    return links


def main(project_id: str) -> None:
    try:
        links = run_project(project_id)
        asyncio.run(notify.notify_project_done(project_id, links))
        logger.info("Projekt %s abgeschlossen: %s", project_id, links)
    except Exception as exc:
        logger.exception("Projekt %s fehlgeschlagen", project_id)
        asyncio.run(notify.notify_project_failed(project_id, str(exc)))
        raise


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Verwendung: python -m video_pipeline.pipeline <project_id>")
        raise SystemExit(1)
    main(sys.argv[1])
