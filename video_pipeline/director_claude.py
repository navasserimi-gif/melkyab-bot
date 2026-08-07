"""
Die "Schnitt-Regie": trifft alle kreativen Entscheidungen.

Warum Claude für diesen Schritt und nicht Gemini (das die Rohvideos ja
schon gesehen hat)? Ab hier ist die Aufgabe kein Video-Verständnis mehr,
sondern strukturiertes, mehrstufiges Reasoning über strukturierte Text-
/JSON-Daten (Szenenliste mit Scores) unter vielen gleichzeitigen Neben-
bedingungen (Zieldauer, Hook-Regel, Raumreihenfolge, keine Wiederholungen,
Plattform-Unterschiede) — genau Claudes Stärke. Die Trennung "Gemini sieht,
Claude entscheidet" hält beide Modelle jeweils in ihrer stärksten Disziplin
und macht die Entscheidung außerdem nachvollziehbar/debugbar (Klartext-
Begründung pro Szene im JSON-Output).

Claude bekommt NIE die Videodateien selbst — nur die von OpenCV/Gemini
erzeugten strukturierten Metadaten. Das ist exakt die Antwort auf die
Einschränkung "Claude Code kann Videodateien nicht direkt verarbeiten":
die Kreativentscheidung ist ein reines Text-Reasoning-Problem, sobald die
Videos einmal in strukturierte Beschreibungen übersetzt wurden.
"""
from __future__ import annotations

import json
import logging

import anthropic

from . import config
from .models import EDLClip, EDLProject, PLATFORM_SPECS, Platform, RoomLabel, Scene

logger = logging.getLogger(__name__)

# Bevorzugte Erzählreihenfolge eines Immobilien-Rundgangs. Der Director darf
# davon abweichen, wenn eine Szene als hook_candidate deutlich stärker ist,
# MUSS diese Abweichung im Ergebnis aber über order_index abbilden.
NARRATIVE_ORDER = [
    RoomLabel.EXTERIOR, RoomLabel.ARCHITECTURE, RoomLabel.ENTRANCE,
    RoomLabel.LIVING_ROOM, RoomLabel.KITCHEN, RoomLabel.DINING_ROOM,
    RoomLabel.DETAIL_LUXURY, RoomLabel.BEDROOM, RoomLabel.BATHROOM,
    RoomLabel.BALCONY, RoomLabel.TERRACE, RoomLabel.GARDEN,
    RoomLabel.GARAGE, RoomLabel.BASEMENT, RoomLabel.OTHER,
]

_SYSTEM_PROMPT = """\
Du bist ein preisgekrönter Video-Editor und Creative Director für
Luxus-Immobilienmarketing auf TikTok, Instagram Reels und YouTube Shorts.
Dir liegt eine Liste bewerteter Videoszenen eines Objekt-Rundgangs vor
(als JSON, inkl. technischer Qualität und semantischer Analyse). Du
triffst ALLE kreativen Entscheidungen selbst — der Nutzer wählt keine
Szenen aus.

Regeln:
- Die ersten 3 Sekunden MÜSSEN sofort Aufmerksamkeit erzeugen (nutze eine
  Szene mit hook_candidate=true oder sehr hohem social_media_potential).
- Style: Luxus, modern, elegant, dynamisch, professionell. Kein
  Standard-Template — jedes Video individuell aus dem tatsächlichen
  Material heraus gestalten.
- Ignoriere Szenen mit is_duplicate_of gesetzt sowie technisch
  unbrauchbare Szenen (werden dir nicht vorgelegt).
- Baue einen natürlichen Rundgang-Spannungsbogen (Außen -> Ankunft ->
  Haupträume -> Luxusdetails -> emotionaler Abschluss), darfst aber die
  stärkste Szene als Hook vorziehen.
- Halte dich an target_duration_seconds (+/- 15%) und niemals über
  max_duration_seconds.
- Vergib knappe, wirkungsvolle on_screen_text-Overlays (max. 5-7 Wörter,
  z. B. "180m² purer Luxus", "Dein neues Zuhause?") - nicht auf jeder Szene,
  sondern gezielt auf Schlüsselmomenten.
- hook_text: der Text/Sound-Hook für die ersten Sekunden (Textoverlay).
- cta_text: kurzer Call-to-Action für die letzte Szene.
- Wähle music_mood als kurzes Stimmungslabel (z. B. "luxurious_uplifting",
  "cinematic_calm", "energetic_modern") - passend zu Tempo und Bildsprache.
- Wähle color_grade_preset aus: "warm_luxury", "cool_modern",
  "bright_airy", "cinematic_contrast".
- transition_out pro Clip aus: "cut", "whip_pan", "crossfade", "match_cut".
  Nutze schnelle, dynamische Übergänge (whip_pan, match_cut) für Energie in
  den ersten Sekunden, ruhigere (crossfade) für emotionale Momente.

Antworte AUSSCHLIESSLICH mit validem JSON gemäß Schema, keine Erklärungen
außerhalb des JSON."""

_TOOL_SCHEMA = {
    "name": "submit_edit_decision_list",
    "description": "Reicht die finale Schnittentscheidung für eine Plattform-Variante ein.",
    "input_schema": {
        "type": "object",
        "properties": {
            "hook_text": {"type": "string"},
            "cta_text": {"type": "string"},
            "music_mood": {"type": "string"},
            "color_grade_preset": {"type": "string"},
            "clips": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "scene_id": {"type": "string"},
                        "in_seconds": {"type": "number"},
                        "out_seconds": {"type": "number"},
                        "transition_out": {"type": "string"},
                        "speed_ramp": {"type": "number"},
                        "on_screen_text": {"type": ["string", "null"]},
                    },
                    "required": ["scene_id", "in_seconds", "out_seconds", "transition_out"],
                },
            },
        },
        "required": ["hook_text", "cta_text", "music_mood", "color_grade_preset", "clips"],
    },
}


def _scenes_to_json(scenes: list[Scene]) -> list[dict]:
    usable = [s for s in scenes if s.technical and s.technical.is_usable and s.analysis and not s.analysis.is_duplicate_of]
    return [
        {
            "scene_id": s.scene_id,
            "duration": round(s.duration, 2),
            "room": s.analysis.room.value,
            "description": s.analysis.description,
            "has_luxury_detail": s.analysis.has_luxury_detail,
            "luxury_notes": s.analysis.luxury_notes,
            "lighting": s.analysis.lighting,
            "camera_movement": s.analysis.camera_movement,
            "emotional_impact": s.analysis.emotional_impact,
            "social_media_potential": s.analysis.social_media_potential,
            "hook_candidate": s.analysis.hook_candidate,
            "technical_overall": round(s.technical.overall, 2),
        }
        for s in usable
    ]


def build_edl(project_id: str, scenes: list[Scene], platform: Platform) -> EDLProject:
    spec = PLATFORM_SPECS[platform]
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

    scene_by_id = {s.scene_id: s for s in scenes}
    user_prompt = json.dumps(
        {
            "platform": platform.value,
            "target_duration_seconds": spec.target_duration_seconds,
            "max_duration_seconds": spec.max_duration_seconds,
            "scenes": _scenes_to_json(scenes),
        },
        ensure_ascii=False,
    )

    response = client.messages.create(
        model=config.CLAUDE_DIRECTOR_MODEL,
        max_tokens=4096,
        system=_SYSTEM_PROMPT,
        tools=[_TOOL_SCHEMA],
        tool_choice={"type": "tool", "name": "submit_edit_decision_list"},
        messages=[{"role": "user", "content": user_prompt}],
    )

    tool_use = next(b for b in response.content if b.type == "tool_use")
    decision = tool_use.input

    edl_clips: list[EDLClip] = []
    for idx, raw in enumerate(decision["clips"]):
        scene = scene_by_id.get(raw["scene_id"])
        if scene is None:
            logger.warning("Director referenzierte unbekannte scene_id %s", raw["scene_id"])
            continue
        edl_clips.append(
            EDLClip(
                scene_id=scene.scene_id,
                source_key=scene.source_key,
                in_seconds=scene.start_seconds + raw["in_seconds"],
                out_seconds=scene.start_seconds + raw["out_seconds"],
                order_index=idx,
                transition_out=raw.get("transition_out", "cut"),
                speed_ramp=float(raw.get("speed_ramp", 1.0)),
                on_screen_text=raw.get("on_screen_text"),
                room=scene.analysis.room if scene.analysis else RoomLabel.OTHER,
            )
        )

    return EDLProject(
        project_id=project_id,
        platform=platform,
        clips=edl_clips,
        hook_text=decision["hook_text"],
        cta_text=decision["cta_text"],
        music_mood=decision["music_mood"],
        music_track_key=None,
        color_grade_preset=decision["color_grade_preset"],
    )


def build_all_platform_edls(project_id: str, scenes: list[Scene]) -> dict[Platform, EDLProject]:
    return {platform: build_edl(project_id, scenes, platform) for platform in Platform}
