"""
Zentrale Datenstrukturen des Pipelines.

Die wichtigste davon ist die "Edit Decision List" (EDLProject): Sie ist
die Schnittstelle zwischen der kreativen Entscheidung (director_claude.py)
und dem eigentlichen Rendering (render.py). Jede Stufe der Pipeline liest
und schreibt ausschließlich diese typisierten Objekte (als JSON serialisierbar,
z. B. für Debugging, ein künftiges Override-UI oder Wiederholungen einzelner
Stufen ohne den ganzen Job neu zu starten).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum


class RoomLabel(str, Enum):
    EXTERIOR = "exterior"
    ENTRANCE = "entrance"
    LIVING_ROOM = "living_room"
    KITCHEN = "kitchen"
    DINING_ROOM = "dining_room"
    BEDROOM = "bedroom"
    BATHROOM = "bathroom"
    BALCONY = "balcony"
    TERRACE = "terrace"
    GARDEN = "garden"
    GARAGE = "garage"
    BASEMENT = "basement"
    DETAIL_LUXURY = "detail_luxury"  # Nahaufnahme hochwertiger Ausstattung
    ARCHITECTURE = "architecture"    # Treppenhaus, Deckenhöhe, Fassade, etc.
    OTHER = "other"


class Platform(str, Enum):
    TIKTOK = "tiktok"
    INSTAGRAM_REEL = "instagram_reel"
    YOUTUBE_SHORT = "youtube_short"


@dataclass
class PlatformSpec:
    platform: Platform
    target_duration_seconds: float
    max_duration_seconds: float
    width: int = 1080
    height: int = 1920
    fps: int = 30
    loudness_target_lufs: float = -14.0
    # Sicherheitsabstand für Textoverlays (UI-Elemente der Plattform: Captions,
    # Like/Share-Leiste, Profilbild-Kreis etc. dürfen nicht verdeckt werden).
    safe_zone_top_px: int = 220
    safe_zone_bottom_px: int = 320


PLATFORM_SPECS: dict[Platform, PlatformSpec] = {
    Platform.TIKTOK: PlatformSpec(Platform.TIKTOK, target_duration_seconds=21, max_duration_seconds=34),
    Platform.INSTAGRAM_REEL: PlatformSpec(Platform.INSTAGRAM_REEL, target_duration_seconds=28, max_duration_seconds=45),
    Platform.YOUTUBE_SHORT: PlatformSpec(Platform.YOUTUBE_SHORT, target_duration_seconds=35, max_duration_seconds=59),
}


@dataclass
class TechnicalScore:
    """Objektive, günstig berechenbare Bildqualitäts-Metriken (OpenCV)."""

    sharpness: float          # 0-1, Laplacian-Varianz normalisiert
    stability: float          # 0-1, 1 = kein Wackeln (aus optischem Fluss)
    exposure: float           # 0-1, 1 = gut belichtet (Histogramm-Analyse)
    colorfulness: float       # 0-1, Hasler-Süsstrunk-Colorfulness-Metrik
    overall: float            # gewichteter Gesamtwert 0-1
    is_usable: bool
    reject_reason: str | None = None


@dataclass
class SceneAnalysis:
    """Semantische Bewertung einer Szene durch das Vision-Modell (Gemini)."""

    room: RoomLabel
    description: str
    has_luxury_detail: bool
    luxury_notes: list[str] = field(default_factory=list)
    lighting: str = ""
    architecture_notes: str = ""
    camera_movement: str = ""          # z.B. "langsamer Schwenk", "Gimbal-Walk", "statisch"
    emotional_impact: float = 0.0      # 0-10
    social_media_potential: float = 0.0  # 0-10
    hook_candidate: bool = False       # geeignet für die ersten 3 Sekunden?
    is_duplicate_of: str | None = None  # scene_id einer bereits gesehenen, sehr ähnlichen Szene


@dataclass
class Scene:
    """Eine einzelne Einstellung (Shot) nach dem Schnitterkennungs-Schritt."""

    scene_id: str
    source_key: str            # Pfad/Objekt-Key des Rohvideos im R2-Bucket
    start_seconds: float
    end_seconds: float
    thumbnail_path: str | None = None
    technical: TechnicalScore | None = None
    analysis: SceneAnalysis | None = None

    @property
    def duration(self) -> float:
        return self.end_seconds - self.start_seconds


@dataclass
class EDLClip:
    """Ein für den finalen Schnitt ausgewählter Ausschnitt einer Szene."""

    scene_id: str
    source_key: str
    in_seconds: float
    out_seconds: float
    order_index: int
    transition_out: str = "cut"        # "cut" | "whip_pan" | "crossfade" | "match_cut"
    transition_duration: float = 0.25
    speed_ramp: float = 1.0            # 1.0 = normal, >1 = Zeitraffer für Dynamik
    on_screen_text: str | None = None
    room: RoomLabel = RoomLabel.OTHER


@dataclass
class EDLProject:
    """Die vollständige Schnittentscheidung für EINE Plattform-Variante."""

    project_id: str
    platform: Platform
    clips: list[EDLClip]
    hook_text: str
    cta_text: str
    music_mood: str
    music_track_key: str | None
    color_grade_preset: str            # siehe render.py: COLOR_GRADE_PRESETS
    subtitle_style: str = "kinetic_bold"
    voiceover_key: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def total_duration(self) -> float:
        return sum(c.out_seconds - c.in_seconds for c in self.clips)
