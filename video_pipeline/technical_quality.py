"""
Günstige, lokale Vorfilterung der Bildqualität (OpenCV, kein KI-API-Call).

Zweck: Von 20-100 Rohclips sind erfahrungsgemäß 30-50% technisch unbrauchbar
(verwackelt, unscharf, falsch belichtet). Diese Stufe sortiert sie VOR den
teuren Gemini/Claude-Aufrufen aus — das senkt die API-Kosten pro Projekt
erheblich und ist einer der wichtigsten Hebel für "beste Qualität bei
vertretbaren Kosten" (siehe ARCHITEKTUR.md, Abschnitt Kosten).
"""
from __future__ import annotations

import logging

import cv2
import numpy as np

from . import config
from .models import TechnicalScore

logger = logging.getLogger(__name__)

_SAMPLE_FRAMES = 12  # gleichmäßig über die Szene verteilte Stichprobe


def _sharpness(gray: np.ndarray) -> float:
    """Laplacian-Varianz — Standardmaß für Bildschärfe."""
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def _exposure(gray: np.ndarray) -> float:
    """Anteil der Pixel im nutzbaren Mittelband des Histogramms (nicht
    ausgefressen/nicht abgesoffen)."""
    hist = cv2.calcHist([gray], [0], None, [256], [0, 256]).flatten()
    hist /= hist.sum() + 1e-9
    clipped = hist[:8].sum() + hist[-8:].sum()
    return float(max(0.0, 1.0 - clipped * 4))


def _colorfulness(frame_bgr: np.ndarray) -> float:
    """Hasler-Süsstrunk-Colorfulness-Metrik, normalisiert auf 0-1."""
    b, g, r = cv2.split(frame_bgr.astype("float"))
    rg = np.absolute(r - g)
    yb = np.absolute(0.5 * (r + g) - b)
    std_root = np.sqrt(rg.std() ** 2 + yb.std() ** 2)
    mean_root = np.sqrt(rg.mean() ** 2 + yb.mean() ** 2)
    raw = std_root + 0.3 * mean_root
    return float(min(1.0, raw / 100.0))


def analyze_scene(video_path: str, start_seconds: float, end_seconds: float) -> TechnicalScore:
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    start_frame = int(start_seconds * fps)
    end_frame = int(end_seconds * fps)
    step = max(1, (end_frame - start_frame) // _SAMPLE_FRAMES)

    sharpness_vals, exposure_vals, color_vals = [], [], []
    prev_gray = None
    motion_deltas = []

    frame_idx = start_frame
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
    while frame_idx < end_frame:
        ok, frame = cap.read()
        if not ok:
            break
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        sharpness_vals.append(_sharpness(gray))
        exposure_vals.append(_exposure(gray))
        color_vals.append(_colorfulness(frame))

        if prev_gray is not None:
            flow = cv2.calcOpticalFlowFarneback(prev_gray, gray, None, 0.5, 2, 15, 3, 5, 1.2, 0)
            magnitude = np.sqrt(flow[..., 0] ** 2 + flow[..., 1] ** 2)
            motion_deltas.append(float(magnitude.mean()))
        prev_gray = gray

        frame_idx += step
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
    cap.release()

    if not sharpness_vals:
        return TechnicalScore(0, 0, 0, 0, 0, is_usable=False, reject_reason="Keine Frames lesbar")

    # Normalisierung: Laplacian-Varianz >800 gilt bei 4K als sehr scharf.
    sharpness = min(1.0, float(np.mean(sharpness_vals)) / 800.0)
    exposure = float(np.mean(exposure_vals))
    colorfulness = float(np.mean(color_vals))

    # Stabilität: hohe optische-Fluss-Varianz = Wackeln. Bewusste, langsame
    # Kameraschwenks (gleichmäßige, aber niedrige Bewegung) werden NICHT
    # bestraft — nur die Unruhe (Varianz) zählt, nicht die Bewegung selbst.
    if motion_deltas:
        jitter = float(np.std(motion_deltas))
        stability = max(0.0, 1.0 - jitter / 3.0)
    else:
        stability = 1.0

    overall = 0.35 * sharpness + 0.3 * stability + 0.2 * exposure + 0.15 * colorfulness

    reject_reason = None
    if sharpness < config.MIN_SHARPNESS_SCORE:
        reject_reason = "unscharf"
    elif stability < (1 - config.MAX_SHAKE_SCORE):
        reject_reason = "verwackelt"
    elif exposure < config.MIN_EXPOSURE_SCORE:
        reject_reason = "Belichtungsfehler"

    return TechnicalScore(
        sharpness=sharpness,
        stability=stability,
        exposure=exposure,
        colorfulness=colorfulness,
        overall=overall,
        is_usable=reject_reason is None,
        reject_reason=reject_reason,
    )
