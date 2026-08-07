"""
Zerlegt lange Rohclips in einzelne Einstellungen (Shots) und erkennt
Beinahe-Duplikate (z. B. drei fast identische Schwenks durchs Wohnzimmer).

Schnitterkennung: PySceneDetect (Content-Detector, HSV-Differenz zwischen
Frames). Immobilien-Rohmaterial ist meist EIN durchgehender Take pro Raum
(Gimbal-Walk) statt vieler harter Schnitte — deshalb wird zusätzlich ein
festes Zeitfenster (siehe config.MIN_SCENE_DURATION_SECONDS) erzwungen,
damit auch aus einem 3-Minuten-Rundgang mehrere bewertbare Kandidaten
entstehen, statt einer einzigen 3-Minuten-"Szene".

Duplikat-Erkennung: Perceptual Hashing (pHash) der Mittelframes. Deutlich
günstiger als jede Szene doppelt durch die Vision-API zu schicken.
"""
from __future__ import annotations

import logging
import uuid

import cv2
import imagehash
from PIL import Image
from scenedetect import ContentDetector, SceneManager, open_video

from . import config
from .models import Scene

logger = logging.getLogger(__name__)


def detect_scenes(video_path: str, source_key: str) -> list[Scene]:
    video = open_video(video_path)
    scene_manager = SceneManager()
    scene_manager.add_detector(ContentDetector(threshold=config.SCENE_DETECT_THRESHOLD))
    scene_manager.detect_scenes(video)
    raw_scenes = scene_manager.get_scene_list()

    scenes: list[Scene] = []
    if not raw_scenes:
        # Kein harter Schnitt gefunden -> gesamten Clip als eine Szene behandeln,
        # ggf. später per fixem Fenster (chunk_long_takes) weiter unterteilen.
        duration = video.duration.get_seconds()
        raw_scenes = [(video.base_timecode, video.base_timecode + video.duration)]

    for start_tc, end_tc in raw_scenes:
        start_s, end_s = start_tc.get_seconds(), end_tc.get_seconds()
        if end_s - start_s < config.MIN_SCENE_DURATION_SECONDS:
            continue
        scenes.append(Scene(scene_id=str(uuid.uuid4())[:8], source_key=source_key, start_seconds=start_s, end_seconds=end_s))

    scenes = _chunk_long_takes(scenes)
    logger.info("%s: %d Rohszenen erkannt", source_key, len(scenes))
    return scenes


def _chunk_long_takes(scenes: list[Scene], max_len: float = 8.0) -> list[Scene]:
    """Teilt sehr lange, ungeschnittene Gimbal-Walks in ~max_len-Sekunden-
    Häppchen, damit die Regie (director_claude.py) einzelne Momente daraus
    wählen kann, statt den gesamten Rundgang übernehmen zu müssen."""
    chunked: list[Scene] = []
    for scene in scenes:
        if scene.duration <= max_len:
            chunked.append(scene)
            continue
        t = scene.start_seconds
        while t < scene.end_seconds:
            end = min(t + max_len, scene.end_seconds)
            chunked.append(Scene(scene_id=str(uuid.uuid4())[:8], source_key=scene.source_key, start_seconds=t, end_seconds=end))
            t = end
    return chunked


def frame_hash(video_path: str, mid_seconds: float) -> imagehash.ImageHash | None:
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(mid_seconds * fps))
    ok, frame = cap.read()
    cap.release()
    if not ok:
        return None
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    return imagehash.phash(Image.fromarray(rgb))


def mark_duplicates(scenes: list[Scene], video_paths: dict[str, str]) -> None:
    """Setzt `analysis.is_duplicate_of` für Szenen, deren Mittelframe einem
    bereits gesehenen, sehr ähnlichen Frame entspricht. Erwartet, dass jede
    Szene bereits eine (leere) SceneAnalysis hat oder toleriert deren Fehlen."""
    seen: list[tuple[str, imagehash.ImageHash]] = []
    for scene in scenes:
        path = video_paths.get(scene.source_key)
        if not path:
            continue
        h = frame_hash(path, (scene.start_seconds + scene.end_seconds) / 2)
        if h is None:
            continue
        for other_id, other_hash in seen:
            if h - other_hash <= config.DUPLICATE_PHASH_DISTANCE:
                if scene.analysis is not None:
                    scene.analysis.is_duplicate_of = other_id
                break
        else:
            seen.append((scene.scene_id, h))
