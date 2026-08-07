"""
Semantische Videoanalyse mit Google Gemini.

Warum Gemini und nicht GPT-4V/Claude Vision für diesen Schritt? Gemini
nimmt Video nativ als Input (nicht nur Einzelbilder) und "versteht" damit
Kameraführung, Schwenk-Geschwindigkeit und Bewegungsfluss — genau die
Kriterien, die der Auftrag explizit fordert (Kameraführung, Dynamik,
Stabilität als *Inhalt*, nicht nur als Pixelmetrik). Zusätzlich ist der
Kontext/Preis für Bulk-Videoanalyse aktuell der beste am Markt.

Zwei-Stufen-Strategie (Kostenoptimierung):
  1. gemini-2.5-flash klassifiziert JEDE überlebende Szene (Raumtyp,
     Kurzbeschreibung, grobe Scores) — günstig, hohe Parallelität.
  2. gemini-2.5-pro bewertet nur die Top-Kandidaten pro Raum-Kategorie
     noch einmal genau (feinere emotionale/Social-Media-Scores), bevor
     Claude daraus die finale Regie-Entscheidung trifft.
"""
from __future__ import annotations

import json
import logging

from google import genai
from google.genai import types

from . import config
from .models import RoomLabel, Scene, SceneAnalysis

logger = logging.getLogger(__name__)

_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "room": {"type": "string", "enum": [r.value for r in RoomLabel]},
        "description": {"type": "string"},
        "has_luxury_detail": {"type": "boolean"},
        "luxury_notes": {"type": "array", "items": {"type": "string"}},
        "lighting": {"type": "string"},
        "architecture_notes": {"type": "string"},
        "camera_movement": {"type": "string"},
        "emotional_impact": {"type": "number"},
        "social_media_potential": {"type": "number"},
        "hook_candidate": {"type": "boolean"},
    },
    "required": ["room", "description", "has_luxury_detail", "emotional_impact", "social_media_potential"],
}

_SYSTEM_PROMPT = """\
Du bist ein preisgekrönter Immobilien-Videograf und Social-Media-Stratege.
Analysiere den gegebenen Videoausschnitt eines Immobilien-Rundgangs.
Erkenne den Raumtyp, bewerte hochwertige/luxuriöse Ausstattungsdetails,
Lichtstimmung, Architektur und Kameraführung. Bewerte emotional_impact und
social_media_potential jeweils auf einer Skala 0-10, aus Sicht eines
Scrollenden auf TikTok/Instagram Reels — nicht aus Sicht eines Maklers.
hook_candidate=true nur, wenn diese Einstellung in den ersten 3 Sekunden
eines Reels sofortige Aufmerksamkeit erzeugen würde (starker visueller
Auftakt: spektakuläre Außenansicht, Wow-Moment, ungewöhnlicher Blickwinkel).
Antworte AUSSCHLIESSLICH als JSON gemäß Schema."""


def _client() -> genai.Client:
    return genai.Client(api_key=config.GEMINI_API_KEY)


def _extract_clip(video_path: str, start: float, end: float) -> bytes:
    """Schneidet den Szenen-Ausschnitt für den Upload an Gemini aus (per
    ffmpeg, verlustfrei/stream-copy wo möglich) und liefert die Rohbytes."""
    import subprocess
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".mp4") as tmp:
        subprocess.run(
            [
                config.FFMPEG_BINARY, "-y", "-ss", str(start), "-to", str(end),
                "-i", video_path, "-c:v", "libx264", "-preset", "veryfast",
                "-vf", "scale=-2:480", "-an", tmp.name,
            ],
            check=True, capture_output=True,
        )
        return tmp.read()


def analyze_scene(scene: Scene, video_path: str, model: str | None = None) -> SceneAnalysis:
    clip_bytes = _extract_clip(video_path, scene.start_seconds, scene.end_seconds)
    client = _client()
    response = client.models.generate_content(
        model=model or config.GEMINI_MODEL_BULK,
        contents=[
            types.Part.from_bytes(data=clip_bytes, mime_type="video/mp4"),
            "Analysiere diese Einstellung.",
        ],
        config=types.GenerateContentConfig(
            system_instruction=_SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=_RESPONSE_SCHEMA,
            temperature=0.2,
        ),
    )
    data = json.loads(response.text)
    return SceneAnalysis(
        room=RoomLabel(data["room"]),
        description=data.get("description", ""),
        has_luxury_detail=data.get("has_luxury_detail", False),
        luxury_notes=data.get("luxury_notes", []),
        lighting=data.get("lighting", ""),
        architecture_notes=data.get("architecture_notes", ""),
        camera_movement=data.get("camera_movement", ""),
        emotional_impact=float(data.get("emotional_impact", 0)),
        social_media_potential=float(data.get("social_media_potential", 0)),
        hook_candidate=data.get("hook_candidate", False),
    )


def analyze_all(scenes: list[Scene], video_paths: dict[str, str]) -> None:
    """Stufe 1 (Bulk) für alle Szenen, gefolgt von Stufe 2 (Deep) für die
    Top-3 Kandidaten je Raumtyp. Schreibt das Ergebnis direkt in scene.analysis."""
    for scene in scenes:
        path = video_paths[scene.source_key]
        try:
            scene.analysis = analyze_scene(scene, path, model=config.GEMINI_MODEL_BULK)
        except Exception:
            logger.exception("Gemini-Analyse fehlgeschlagen für Szene %s", scene.scene_id)

    by_room: dict[RoomLabel, list[Scene]] = {}
    for scene in scenes:
        if scene.analysis:
            by_room.setdefault(scene.analysis.room, []).append(scene)

    for room, room_scenes in by_room.items():
        top = sorted(room_scenes, key=lambda s: s.analysis.social_media_potential, reverse=True)[:3]
        for scene in top:
            path = video_paths[scene.source_key]
            try:
                scene.analysis = analyze_scene(scene, path, model=config.GEMINI_MODEL_DEEP)
            except Exception:
                logger.exception("Gemini-Deep-Analyse fehlgeschlagen für Szene %s", scene.scene_id)
