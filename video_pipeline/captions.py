"""
Untertitel/Text-Overlays.

Zwei Quellen von Text im fertigen Video:
1. Kinetische on_screen_text-Overlays, die Claude pro Clip vergeben hat
   (director_claude.py) — kurze Schlüsselwörter, kein Transkript nötig.
2. Falls eine Tonspur mit Sprache existiert (Voiceover/O-Ton des Maklers),
   wird sie per Whisper transkribiert und als eingebrannte Untertitel-Spur
   (ASS) hinzugefügt. Immobilien-Rohmaterial ist meist stumm (nur Ambient/
   Musik), daher ist dieser Pfad optional und wird übersprungen, wenn keine
   Sprache erkannt wird.
"""
from __future__ import annotations

import logging

from faster_whisper import WhisperModel

from . import config
from .models import EDLClip

logger = logging.getLogger(__name__)

_model: WhisperModel | None = None


def _get_model() -> WhisperModel:
    global _model
    if _model is None:
        _model = WhisperModel(config.WHISPER_MODEL, device="auto", compute_type="auto")
    return _model


def transcribe(audio_path: str) -> list[dict]:
    """Liefert eine Liste von {start, end, text}-Segmenten, leer wenn keine
    verständliche Sprache erkannt wurde (reines Ambient/Musik)."""
    segments, info = _get_model().transcribe(audio_path, vad_filter=True)
    if info.language_probability < 0.5:
        return []
    return [{"start": s.start, "end": s.end, "text": s.text.strip()} for s in segments]


def build_ass_subtitles(segments: list[dict], style: str, width: int, height: int) -> str:
    """Baut eine .ass-Untertiteldatei im gewählten Stil (kinetic_bold =
    große, zentrierte, fett hervorgehobene Wörter im Social-Media-Look)."""
    font_size = int(height * 0.045)
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, Bold, BorderStyle, Outline, Shadow, Alignment, MarginV
Style: Default,Montserrat ExtraBold,{font_size},&H00FFFFFF,&H00000000,1,1,4,0,2,{int(height * 0.22)}

[Events]
Format: Layer, Start, End, Style, Text
"""
    lines = []
    for seg in segments:
        start = _fmt_ts(seg["start"])
        end = _fmt_ts(seg["end"])
        lines.append(f"Dialogue: 0,{start},{end},Default,{seg['text']}")
    return header + "\n".join(lines)


def build_kinetic_overlay_ass(clips: list[EDLClip], clip_offsets: list[float], width: int, height: int) -> str:
    """Baut die on_screen_text-Overlays der Regie-Entscheidung als eigene
    ASS-Spur, zeitlich an die finale Timeline (nach dem Schnitt) angepasst."""
    font_size = int(height * 0.06)
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, Bold, BorderStyle, Outline, Shadow, Alignment, MarginV
Style: Overlay,Montserrat ExtraBold,{font_size},&H00FFFFFF,&H00000000,1,1,5,0,8,{int(height * 0.14)}

[Events]
Format: Layer, Start, End, Style, Text
"""
    lines = []
    for clip, offset in zip(clips, clip_offsets):
        if not clip.on_screen_text:
            continue
        dur = clip.out_seconds - clip.in_seconds
        start = _fmt_ts(offset)
        end = _fmt_ts(offset + min(dur, 2.5))
        lines.append(f"Dialogue: 1,{start},{end},Overlay,{{\\fad(200,200)}}{clip.on_screen_text}")
    return header + "\n".join(lines)


def _fmt_ts(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:d}:{m:02d}:{s:05.2f}"
