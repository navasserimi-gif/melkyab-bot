"""
Rendert eine EDLProject-Entscheidung zu einer fertigen MP4-Datei.

FFmpeg ist hier bewusst die Render-Engine (nicht ein weiterer Cloud-API-
Aufruf): der Schnitt steht durch director_claude.py bereits fest, es geht
nur noch um deterministisches, schnelles, GPU-beschleunigbares Encoding.
Ein API-Dienst wäre hier teurer und langsamer, ohne einen Qualitätsvorteil
zu bringen, da die kreative Arbeit schon erledigt ist.

Pipeline pro Plattform-Variante:
  1. Pro Clip: trim, speed-ramp, Farbkorrektur/-look, Skalierung + Crop auf
     9:16 (Center-Crop mit optionalem Fokus-Offset für zukünftige
     Saliency-basierte Reframe-Logik, siehe TODO unten).
  2. Aneinanderreihen mit den von der Regie gewählten Übergängen (xfade).
  3. On-Screen-Text- und Untertitel-Overlay (ASS, via captions.py).
  4. Audio: Musikbett (geloopt/getrimmt auf Zieldauer, loudnorm) plus
     optionales Voiceover mit Sidechain-Ducking der Musik darunter.
"""
from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from . import captions, config
from .models import EDLProject, PLATFORM_SPECS

logger = logging.getLogger(__name__)

COLOR_GRADE_PRESETS: dict[str, str] = {
    # ffmpeg eq/curves-Filterketten je "Look". In Produktion durch echte
    # .cube-LUTs ersetzbar (lut3d-Filter) für konsistentere, hochwertigere Farben.
    "warm_luxury": "eq=contrast=1.08:saturation=1.15:brightness=0.02,colorbalance=rm=0.05:ym=0.02",
    "cool_modern": "eq=contrast=1.1:saturation=0.95,colorbalance=bm=0.06",
    "bright_airy": "eq=contrast=1.02:saturation=1.05:brightness=0.06,curves=all='0/0 0.5/0.58 1/1'",
    "cinematic_contrast": "eq=contrast=1.18:saturation=1.05:brightness=-0.01,curves=all='0/0 0.25/0.18 0.75/0.82 1/1'",
}

_TRANSITIONS = {"crossfade": "fade", "whip_pan": "wipeleft", "match_cut": "fade", "cut": None}


def _clip_filter(idx: int, input_idx: int, in_s: float, out_s: float, speed: float, color_preset: str, width: int, height: int) -> str:
    setpts = f"setpts={1/speed:.4f}*(PTS-STARTPTS)" if speed != 1.0 else "setpts=PTS-STARTPTS"
    color = COLOR_GRADE_PRESETS.get(color_preset, COLOR_GRADE_PRESETS["warm_luxury"])
    # Skaliert so, dass die kürzere Seite den Zielrahmen füllt, croppt dann
    # zentriert auf 9:16. TODO(Erweiterung): Crop-Offset aus einer künftigen
    # Saliency-/Objekterkennung beziehen statt hartem Center-Crop.
    scale_crop = f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}"
    return f"[{input_idx}:v]trim=start={in_s}:end={out_s},{setpts},{scale_crop},{color},format=yuv420p[v{idx}]"


def build_filter_complex(project: EDLProject, input_index_by_key: dict[str, int], width: int, height: int, fps: int) -> tuple[str, str]:
    """Baut die filter_complex-Kette. `input_index_by_key` ordnet jedem
    Quell-Key (Rohvideo, aus dem eine oder mehrere Szenen stammen) den
    ffmpeg -i-Input-Index zu, da ein Projekt i. d. R. aus VIELEN
    unterschiedlichen Rohdateien besteht (nicht aus einer einzigen).
    Rückgabe: (filter_complex_string, output_label)."""
    parts = []
    labels = []
    for idx, clip in enumerate(project.clips):
        parts.append(
            _clip_filter(
                idx, input_index_by_key[clip.source_key], clip.in_seconds, clip.out_seconds,
                clip.speed_ramp, project.color_grade_preset, width, height,
            )
        )
        labels.append(f"[v{idx}]")

    if len(labels) == 1:
        concat = f"{labels[0]}fps={fps}[vout]"
    else:
        # xfade verkettet paarweise; harte "cut"-Übergänge nutzen offset=0/
        # duration=0 äquivalent -> hier vereinfachend concat für "cut" und
        # xfade für alle benannten Übergänge dazwischen.
        chain = labels[0]
        running_offset = project.clips[0].out_seconds - project.clips[0].in_seconds
        for i in range(1, len(project.clips)):
            clip = project.clips[i - 1]
            transition = _TRANSITIONS.get(clip.transition_out)
            out_label = f"[x{i}]" if i < len(project.clips) - 1 else "[vpre]"
            if transition:
                d = clip.transition_duration
                offset = max(0.0, running_offset - d)
                parts.append(f"{chain}{labels[i]}xfade=transition={transition}:duration={d}:offset={offset}{out_label}")
                running_offset = offset + d + (project.clips[i].out_seconds - project.clips[i].in_seconds)
            else:
                parts.append(f"{chain}{labels[i]}concat=n=2:v=1:a=0{out_label}")
                running_offset += project.clips[i].out_seconds - project.clips[i].in_seconds
            chain = out_label
        concat = f"[vpre]fps={fps}[vout]"

    parts.append(concat)
    return ";".join(parts), "[vout]"


def render_platform_variant(project: EDLProject, source_path_by_key: dict[str, str], music_path: str, workdir: str) -> str:
    spec = PLATFORM_SPECS[project.platform]
    out_dir = Path(workdir) / project.project_id
    out_dir.mkdir(parents=True, exist_ok=True)
    output_path = out_dir / f"{project.platform.value}.mp4"

    # Jede in der EDL referenzierte Rohdatei wird als eigener ffmpeg-Input
    # eingebunden (ein Projekt besteht i. d. R. aus 20-100 unterschiedlichen
    # Quelldateien, nicht aus einer einzigen).
    used_keys = list(dict.fromkeys(clip.source_key for clip in project.clips))
    input_index_by_key = {key: i for i, key in enumerate(used_keys)}
    source_inputs = [source_path_by_key[key] for key in used_keys]
    music_input_idx = len(source_inputs)

    filter_complex, vout = build_filter_complex(project, input_index_by_key, spec.width, spec.height, spec.fps)

    clip_offsets = []
    running = 0.0
    for clip in project.clips:
        clip_offsets.append(running)
        running += (clip.out_seconds - clip.in_seconds) / max(clip.speed_ramp, 0.01)

    ass_path = out_dir / f"{project.platform.value}_overlay.ass"
    ass_content = captions.build_kinetic_overlay_ass(project.clips, clip_offsets, spec.width, spec.height)
    ass_path.write_text(ass_content, encoding="utf-8")

    video_codec = ["-c:v", "h264_nvenc", "-preset", "p5"] if config.USE_NVENC else ["-c:v", "libx264", "-preset", "medium", "-crf", "19"]

    input_args = []
    for src in source_inputs:
        input_args += ["-i", src]
    input_args += ["-stream_loop", "-1", "-i", music_path]  # Musik auf Zieldauer loopen, dann atrim

    cmd = [
        config.FFMPEG_BINARY, "-y",
        *input_args,
        "-filter_complex",
        f"{filter_complex};{vout}ass={ass_path}[vsub];"
        f"[{music_input_idx}:a]atrim=0:{running},asetpts=PTS-STARTPTS,volume=0.8,loudnorm=I={spec.loudness_target_lufs}[aout]",
        "-map", "[vsub]", "-map", "[aout]",
        *video_codec,
        "-r", str(spec.fps),
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        str(output_path),
    ]

    logger.info("Rendere %s (%s) ...", project.project_id, project.platform.value)
    subprocess.run(cmd, check=True, capture_output=True)
    return str(output_path)
