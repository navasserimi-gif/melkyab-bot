"""
======================================================================
 VIRALER VIDEO-GENERATOR
 Erstellt aus einer Reihe von Bildern automatisch ein fertiges,
 hochkant ausgerichtetes Video (9:16) fuer TikTok, Instagram Reels
 und YouTube Shorts.
======================================================================

INSTALLATION (einmalig im Terminal ausfuehren):

    pip install moviepy==1.0.3 librosa pillow numpy imageio-ffmpeg

Hinweis: moviepy benoetigt ffmpeg. Ueber "imageio-ffmpeg" wird ein
passendes ffmpeg-Binary automatisch mitinstalliert, du musst also
nichts weiter tun. Falls du lieber dein System-ffmpeg nutzen willst,
kannst du es zusaetzlich per "sudo apt install ffmpeg" (Linux) bzw.
"brew install ffmpeg" (Mac) installieren.

SO BENUTZT DU DAS SKRIPT:
 1. Trage unten bei "BILDER" die Pfade zu deinen Fotos ein.
 2. Lege optional deinen Trending-Sound unter dem Pfad in "MUSIK_PFAD"
    ab (z. B. als MP3, aus TikTok/CapCut exportiert). Ist keine Datei
    vorhanden, wird das Video trotzdem erstellt -- nur ohne Ton und
    mit einem festen Ersatz-Rhythmus fuer die Schnitte.
 3. Optional: MIT_TEXT_OVERLAYS = True setzen und HOOK_TEXT / TEXT_OVERLAYS
    anpassen, falls Text im Video erscheinen soll (Standard: aus).
 4. Optional: SCHNITT_TEMPO anpassen, um den Schnittrhythmus langsamer
    (Wert erhoehen) oder schneller (Wert senken) zu machen.
 5. Skript ausfuehren:  python erstelle_viral_video.py
======================================================================
"""

import os
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageOps

from moviepy.editor import (
    VideoClip, CompositeVideoClip, ColorClip,
    AudioFileClip, CompositeAudioClip,
)
from moviepy.audio.fx.all import audio_loop

try:
    import librosa
except ImportError:
    librosa = None


# ======================================================================
# 1) KONFIGURATION -- HIER DEINE EIGENEN PFADE UND TEXTE EINTRAGEN
# ======================================================================

# Pfade zu deinen Bildern, in der Reihenfolge, in der sie erscheinen sollen.
BILDER = [
    "bilder/bild1.jpg",
    "bilder/bild2.jpg",
    "bilder/bild3.jpg",
    "bilder/bild4.jpg",
    "bilder/bild5.jpg",
]

# Platzhalter fuer deinen Trending-Track (MP3/WAV). Sobald hier eine
# echte Datei liegt, erkennt das Skript automatisch den Beat und
# synchronisiert die Schnitte darauf.
MUSIK_PFAD = "musik/trending_track.mp3"

# Optionale Sound-Effekte fuer Uebergaenge. Wenn die Dateien nicht
# existieren, werden sie einfach uebersprungen (kein Fehler).
SFX_WHOOSH = "sfx/whoosh.mp3"   # wird bei "Glitch"-Uebergaengen abgespielt
SFX_IMPACT = "sfx/impact.mp3"   # wird beim Flash-Cut abgespielt

# Text im Video an/aus. Auf False = komplett textfreies Video (nur Bilder,
# Effekte und Musik). Auf True, um Hook- und Zusatztexte einzublenden.
MIT_TEXT_OVERLAYS = False

# Hook: erscheint gross und farbig in den ersten 1-3 Sekunden (nur falls
# MIT_TEXT_OVERLAYS = True).
HOOK_TEXT = "WARTE BIS ZUM ENDE 👀"

# Weitere Text-Overlays, die im Laufe des Videos nacheinander eingeblendet
# werden (leere Liste = keine Zusatztexte; nur falls MIT_TEXT_OVERLAYS = True).
TEXT_OVERLAYS = [
    "Das glaubst du nicht...",
    "Schau genau hin 🔍",
    "Und dann DAS 😱",
]

# Optional: Pfad zu einer eigenen fetten .ttf-Schriftart fuer die Texte.
# None = Skript sucht automatisch nach einer passenden System-Schrift.
FONT_PFAD = None

AUSGABE_PFAD = "output/viral_video.mp4"

# ---- Format & technische Einstellungen -------------------------------
BREITE, HOEHE = 1080, 1920     # 9:16 Hochkantformat fuer TikTok/Reels/Shorts
FPS = 30
ZOOM_MAX = 1.22                # maximale Ken-Burns-Zoomstufe pro Bild

# Tempo-Regler fuer den Schnittrhythmus: >1.0 = ruhigere/langsamere Schnitte,
# 1.0 = unveraendert (roher Beat-Takt), <1.0 = noch schnellere Schnitte.
# Die zu schnellen Cuts im ersten Test kamen vom rohen Beat-Takt -- hierueber
# laesst sich das Tempo bequem drosseln, ohne die Beat-Erkennung anzufassen.
SCHNITT_TEMPO = 1.8
MINDEST_SEGMENT_DAUER = 0.55   # kein Bild wird kuerzer als das angezeigt (Sek.)

HOOK_MIN_DAUER, HOOK_MAX_DAUER = 1.0, 2.6   # Laenge des Hook-Segments (Sek.)
FLASH_DAUER = 0.07             # Laenge des weissen Flash-Cuts (Sek.)
UEBERGANG_OVERLAP = 0.28       # Ueberlappung bei weichen Crossfades (Sek.)
TEXT_ALLE_N_SEGMENTE = 3       # nach wie vielen Segmenten der naechste Text kommt
MUSIK_LAUTSTAERKE = 0.9
SFX_LAUTSTAERKE = 0.8


# ======================================================================
# 2) BILD-VERARBEITUNG: Cover-Zuschnitt, Farbkorrektur, Ken-Burns-Effekt
# ======================================================================

def bild_cover_laden(pfad, ziel_breite, ziel_hoehe):
    """Laedt ein Bild und schneidet/skaliert es formatfuellend (wie
    "object-fit: cover" im Web) auf die gewuenschte Groesse zu."""
    img = Image.open(pfad).convert("RGB")
    img = ImageOps.exif_transpose(img)  # korrekte Ausrichtung bei Handyfotos

    quell_verhaeltnis = img.width / img.height
    ziel_verhaeltnis = ziel_breite / ziel_hoehe

    if quell_verhaeltnis > ziel_verhaeltnis:
        neue_hoehe = ziel_hoehe
        neue_breite = round(neue_hoehe * quell_verhaeltnis)
    else:
        neue_breite = ziel_breite
        neue_hoehe = round(neue_breite / quell_verhaeltnis)

    img = img.resize((neue_breite, neue_hoehe), Image.LANCZOS)
    left = (neue_breite - ziel_breite) // 2
    top = (neue_hoehe - ziel_hoehe) // 2
    return img.crop((left, top, left + ziel_breite, top + ziel_hoehe))


def farbkorrektur_bild(img):
    """Sorgt fuer einen konsistenten, kraeftigen 'Social-Media-Look':
    mehr Saettigung/Kontrast, ein Hauch Waerme und eine leichte Vignette,
    die den Blick zur Bildmitte lenkt."""
    img = ImageEnhance.Color(img).enhance(1.18)
    img = ImageEnhance.Contrast(img).enhance(1.12)
    img = ImageEnhance.Brightness(img).enhance(1.03)

    arr = np.array(img).astype(np.float32)
    arr[:, :, 0] = np.clip(arr[:, :, 0] * 1.03, 0, 255)   # etwas mehr Rot
    arr[:, :, 2] = np.clip(arr[:, :, 2] * 0.97, 0, 255)   # etwas weniger Blau

    h, w = arr.shape[:2]
    y, x = np.ogrid[:h, :w]
    dist = np.sqrt(((x - w / 2) / w) ** 2 + ((y - h / 2) / h) ** 2)
    vignette = 1 - np.clip(dist * 0.6, 0, 0.35)
    arr *= vignette[..., None]

    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def ken_burns_clip(bild_pfad, dauer, breite, hoehe, zoom_max, richtung=None):
    """Erstellt einen Video-Clip aus einem Standbild mit Ken-Burns-Effekt
    (langsamer Zoom + leichtes Schwenken), was Bewegung ins Bild bringt
    und dadurch die Watch-Time gegenueber statischen Fotos erhoeht."""
    richtung = richtung or random.choice(["rein", "raus"])

    work = bild_cover_laden(bild_pfad, round(breite * zoom_max), round(hoehe * zoom_max))
    work = farbkorrektur_bild(work)
    work_w, work_h = work.size

    pan_x = random.uniform(-0.6, 0.6)
    pan_y = random.uniform(-0.6, 0.6)

    def make_frame(t):
        p = min(max(t / dauer, 0.0), 1.0) if dauer > 0 else 0.0
        p = p * p * (3 - 2 * p)  # ease-in-out fuer eine organischere Bewegung
        zf = p if richtung == "rein" else 1 - p

        crop_w = work_w + (breite - work_w) * zf
        crop_h = work_h + (hoehe - work_h) * zf
        slack_w = work_w - crop_w
        slack_h = work_h - crop_h

        cx = work_w / 2 + pan_x * slack_w / 2
        cy = work_h / 2 + pan_y * slack_h / 2
        left = min(max(cx - crop_w / 2, 0), work_w - crop_w)
        top = min(max(cy - crop_h / 2, 0), work_h - crop_h)

        frame = work.resize((breite, hoehe), Image.LANCZOS,
                             box=(left, top, left + crop_w, top + crop_h))
        return np.array(frame)

    return VideoClip(make_frame, duration=dauer)


def glitch_frame(frame, t, dauer):
    """Verschiebt kurz die Farbkanaele und einzelne Bildzeilen -- ein
    schneller 'Glitch'-Effekt, der als aufmerksamkeitsstarker
    Uebergang zwischen zwei Clips dient."""
    intensitaet = max(0.0, 1 - t / dauer)
    verschiebung = int(16 * intensitaet)
    if verschiebung == 0:
        return frame

    out = frame.copy()
    out[:, :, 0] = np.roll(frame[:, :, 0], verschiebung, axis=1)
    out[:, :, 2] = np.roll(frame[:, :, 2], -verschiebung, axis=1)

    if random.random() < 0.5:
        zeile = random.randint(0, out.shape[0] - 1)
        band = slice(max(0, zeile - 4), min(out.shape[0], zeile + 4))
        out[band] = np.roll(out[band], verschiebung * 2, axis=1)

    return out


def flash_clip(dauer, breite, hoehe):
    """Kurzer weisser Vollbild-'Blitz' fuer knallige Flash-Cut-Uebergaenge."""
    return ColorClip(size=(breite, hoehe), color=(255, 255, 255), duration=dauer)


# ======================================================================
# 3) TEXT-OVERLAYS: grosse, kontrastreiche, animiert eingeblendete Schrift
# ======================================================================

def schriftart_laden(schriftgroesse):
    kandidaten = [
        FONT_PFAD,
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "C:\\Windows\\Fonts\\arialbd.ttf",
    ]
    for pfad in kandidaten:
        if pfad and os.path.exists(pfad):
            try:
                return ImageFont.truetype(pfad, schriftgroesse)
            except OSError:
                continue
    print("Hinweis: Keine fette System-Schriftart gefunden -- benutze die "
          "PIL-Standardschrift. Fuer einen schoeneren Look FONT_PFAD setzen.")
    return ImageFont.load_default()


def text_bild_rendern(text, breite, schriftgroesse, textfarbe, konturbreite=8):
    """Rendert Text mit Kontur (fuer Lesbarkeit auf jedem Hintergrund)
    als transparentes RGBA-Bild, inkl. einfachem Zeilenumbruch."""
    font = schriftart_laden(schriftgroesse)
    dummy = Image.new("RGBA", (10, 10))
    draw = ImageDraw.Draw(dummy)

    max_textbreite = int(breite * 0.85)
    zeilen, aktuelle_zeile = [], ""
    for wort in text.split():
        test = (aktuelle_zeile + " " + wort).strip()
        bbox = draw.textbbox((0, 0), test, font=font, stroke_width=konturbreite)
        if bbox[2] - bbox[0] <= max_textbreite or not aktuelle_zeile:
            aktuelle_zeile = test
        else:
            zeilen.append(aktuelle_zeile)
            aktuelle_zeile = wort
    if aktuelle_zeile:
        zeilen.append(aktuelle_zeile)

    zeilenabstand = int(schriftgroesse * 1.25)
    img = Image.new("RGBA", (breite, zeilenabstand * len(zeilen) + konturbreite * 2), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    for i, zeile in enumerate(zeilen):
        bbox = draw.textbbox((0, 0), zeile, font=font, stroke_width=konturbreite)
        x = (breite - (bbox[2] - bbox[0])) / 2
        y = i * zeilenabstand
        draw.text((x, y), zeile, font=font, fill=textfarbe,
                   stroke_width=konturbreite, stroke_fill=(0, 0, 0, 255))
    return img


def text_overlay_clip(text, dauer, breite, hoehe, y_position, schriftgroesse,
                       betont=False, verzoegerung=0.0):
    """Baut einen animierten Text-Layer: sanftes Einploppen (Skalierung +
    Fade), kurzes Halten, sanftes Ausblenden. Wird spaeter ueber den
    Hintergrund-Clip gelegt."""
    textfarbe = (255, 224, 0, 255) if betont else (255, 255, 255, 255)
    text_bild = text_bild_rendern(text, breite, schriftgroesse, textfarbe)
    tw, th = text_bild.size
    ziel_y = int(hoehe * y_position - th / 2)
    fade_dauer = 0.3

    def easing(x):
        x = min(max(x, 0.0), 1.0)
        return x * x * (3 - 2 * x)

    def zustand(t):
        t_lokal = t - verzoegerung
        if t_lokal < 0 or t_lokal > dauer - verzoegerung:
            return None
        alpha_ein = easing(t_lokal / fade_dauer)
        rest = (dauer - verzoegerung) - t_lokal
        alpha_aus = easing(rest / fade_dauer) if rest < fade_dauer else 1.0
        alpha = alpha_ein * alpha_aus
        skala = 0.75 + 0.25 * alpha_ein
        return alpha, skala

    def frame_und_maske(t):
        z = zustand(t)
        if z is None:
            return np.zeros((hoehe, breite, 3), dtype=np.uint8), np.zeros((hoehe, breite))
        alpha, skala = z
        skaliert = text_bild.resize((max(1, round(tw * skala)), max(1, round(th * skala))), Image.LANCZOS)
        canvas = Image.new("RGBA", (breite, hoehe), (0, 0, 0, 0))
        sx = round((breite - skaliert.width) / 2)
        sy = round(ziel_y + (th - skaliert.height) / 2)
        canvas.alpha_composite(skaliert, (sx, sy))
        arr = np.array(canvas)
        return arr[:, :, :3], (arr[:, :, 3] / 255.0) * alpha

    clip = VideoClip(lambda t: frame_und_maske(t)[0], duration=dauer)
    maske = VideoClip(lambda t: frame_und_maske(t)[1], duration=dauer, ismask=True)
    return clip.set_mask(maske)


# ======================================================================
# 4) BEAT-DETECTION: Schnitt-Rhythmus aus der Musik ableiten
# ======================================================================

def erkenne_schnitt_segmente(musik_pfad):
    """Analysiert den Trending-Track und liefert eine Liste von
    (Dauer, ist_energetisch)-Segmenten: bei energiereichen Passagen wird
    auf jeden Beat geschnitten (schnell), bei ruhigeren Passagen werden
    mehrere Beats zu einem laengeren, emotionaleren Hold zusammengefasst.
    Ist keine Musikdatei vorhanden, wird ein fester Ersatz-Rhythmus
    verwendet, damit das Skript trotzdem laeuft."""
    if librosa is not None and os.path.exists(musik_pfad):
        y, sr = librosa.load(musik_pfad, sr=None, mono=True)
        tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
        beat_times = librosa.frames_to_time(beat_frames, sr=sr)

        if len(beat_times) < 4:
            print("Hinweis: Zu wenige Beats erkannt, nutze Ersatz-Rhythmus.")
            return _ersatz_segmente()

        rms = librosa.feature.rms(y=y)[0]
        rms_zeiten = librosa.frames_to_time(np.arange(len(rms)), sr=sr)
        energie_werte = [rms[min(np.searchsorted(rms_zeiten, bt), len(rms) - 1)] for bt in beat_times]
        schwelle = float(np.median(energie_werte))

        segmente = []
        i = 0
        while i < len(beat_times) - 1:
            energetisch = energie_werte[i] >= schwelle
            beats_zusammen = 1 if energetisch else random.choice([2, 3])
            ende = min(i + beats_zusammen, len(beat_times) - 1)
            dauer = max(beat_times[ende] - beat_times[i], 0.18)
            segmente.append((dauer, energetisch))
            i = ende

        return segmente, sum(d for d, _ in segmente), beat_times, float(tempo)

    if not os.path.exists(musik_pfad):
        print(f"Hinweis: Keine Musikdatei unter '{musik_pfad}' gefunden -- "
              f"Video wird ohne Ton und mit festem Ersatz-Rhythmus erstellt.")
    elif librosa is None:
        print("Hinweis: librosa ist nicht installiert -- Ersatz-Rhythmus wird verwendet.")
    return _ersatz_segmente()


def _ersatz_segmente(bpm=100, anzahl=16):
    beat_dauer = 60 / bpm
    segmente = []
    for j in range(anzahl):
        energetisch = (j % 3 != 0)
        beats = 1 if energetisch else 2
        segmente.append((beat_dauer * beats, energetisch))
    return segmente, sum(d for d, _ in segmente), None, bpm


# ======================================================================
# 5) HAUPTFUNKTION: alles zu einem fertigen Video zusammensetzen
# ======================================================================

def erstelle_viral_video():
    os.makedirs(os.path.dirname(AUSGABE_PFAD) or ".", exist_ok=True)

    vorhandene_bilder = [b for b in BILDER if os.path.exists(b)]
    if not vorhandene_bilder:
        raise SystemExit(
            "Keine Bilder gefunden! Bitte in der Variable BILDER oben "
            "gueltige Pfade zu deinen Fotos eintragen."
        )
    fehlende = set(BILDER) - set(vorhandene_bilder)
    if fehlende:
        print(f"Warnung: folgende Bilder fehlen und werden uebersprungen: {sorted(fehlende)}")

    segmente, _, beat_times, tempo = erkenne_schnitt_segmente(MUSIK_PFAD)
    segmente = [(max(d * SCHNITT_TEMPO, MINDEST_SEGMENT_DAUER), e) for d, e in segmente]
    segmente[0] = (min(max(segmente[0][0], HOOK_MIN_DAUER), HOOK_MAX_DAUER), True)
    info = f"{len(segmente)} Schnitt-Segmente"
    info += f" bei ca. {tempo:.0f} BPM" if beat_times is not None else " (Ersatz-Rhythmus)"
    print(info)

    ebenen = []
    audio_events = []
    zeit_cursor = 0.0
    text_index = 0

    for i, (dauer, energetisch) in enumerate(segmente):
        bild_pfad = vorhandene_bilder[i % len(vorhandene_bilder)]
        richtung = "rein" if i % 2 == 0 else "raus"
        hg_clip = ken_burns_clip(bild_pfad, dauer, BREITE, HOEHE, ZOOM_MAX, richtung)

        if i == 0:
            uebergang = "start"
        elif energetisch:
            uebergang = random.choice(["hart", "flash", "glitch"])
        else:
            uebergang = "crossfade"

        overlap = UEBERGANG_OVERLAP if uebergang == "crossfade" else 0.0
        start_i = max(0.0, zeit_cursor - overlap)

        if uebergang == "crossfade":
            hg_clip = hg_clip.crossfadein(overlap)
        elif uebergang == "glitch":
            glitch_dauer = min(0.15, dauer * 0.4)
            hg_clip = hg_clip.fl(
                lambda gf, t, gd=glitch_dauer: glitch_frame(gf(t), t, gd) if t < gd else gf(t)
            )

        hg_clip = hg_clip.set_start(start_i)
        ebenen.append(hg_clip)

        if uebergang == "flash" and start_i > 0:
            ebenen.append(flash_clip(FLASH_DAUER, BREITE, HOEHE).set_start(max(0, start_i - FLASH_DAUER / 2)))
            audio_events.append((start_i, SFX_IMPACT))
        elif uebergang == "glitch":
            audio_events.append((start_i, SFX_WHOOSH))

        if MIT_TEXT_OVERLAYS and i == 0 and HOOK_TEXT:
            hook = text_overlay_clip(HOOK_TEXT, dauer + 0.4, BREITE, HOEHE,
                                      y_position=0.42, schriftgroesse=110,
                                      betont=True, verzoegerung=0.12)
            ebenen.append(hook.set_start(start_i))
        elif MIT_TEXT_OVERLAYS and TEXT_OVERLAYS and i > 0 and i % TEXT_ALLE_N_SEGMENTE == 0:
            text = TEXT_OVERLAYS[text_index % len(TEXT_OVERLAYS)]
            text_index += 1
            overlay = text_overlay_clip(text, min(dauer + 0.2, 2.2), BREITE, HOEHE,
                                         y_position=0.82, schriftgroesse=72,
                                         betont=False, verzoegerung=0.08)
            ebenen.append(overlay.set_start(start_i))

        zeit_cursor = start_i + dauer

    gesamtdauer = zeit_cursor
    video = CompositeVideoClip(ebenen, size=(BREITE, HOEHE)).set_duration(gesamtdauer).set_fps(FPS)

    audio_spuren = []
    if os.path.exists(MUSIK_PFAD):
        musik = AudioFileClip(MUSIK_PFAD)
        musik = (audio_loop(musik, duration=gesamtdauer) if musik.duration < gesamtdauer
                 else musik.subclip(0, gesamtdauer))
        audio_spuren.append(musik.volumex(MUSIK_LAUTSTAERKE))

    for zeitpunkt, sfx_pfad in audio_events:
        if sfx_pfad and os.path.exists(sfx_pfad):
            audio_spuren.append(AudioFileClip(sfx_pfad).volumex(SFX_LAUTSTAERKE).set_start(max(0, zeitpunkt - 0.03)))

    if audio_spuren:
        video = video.set_audio(CompositeAudioClip(audio_spuren).set_duration(gesamtdauer))

    print(f"Rendere Video ({gesamtdauer:.1f}s) nach: {AUSGABE_PFAD}")
    video.write_videofile(
        AUSGABE_PFAD,
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        preset="medium",
        threads=4,
        bitrate="8000k",
    )
    print("Fertig! Video ist bereit zum Hochladen.")


if __name__ == "__main__":
    erstelle_viral_video()
