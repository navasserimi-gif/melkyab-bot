"""
Extraktion der Kerndaten (Titel, Preis, Fläche, Zimmer, Adresse, Beschreibung,
Bilder) aus einem beliebigen externen Immobilien-Exposé (PDF).
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass, field

import fitz  # PyMuPDF
from PIL import Image

MIN_IMAGE_SIDE = 180          # Bilder kleiner als das gelten als Icon/Logo und werden ignoriert
MAX_GALLERY_IMAGES = 8


@dataclass
class ExposeData:
    title: str = "Exklusives Immobilienangebot"
    price: str = ""
    area: str = ""
    plot_area: str = ""
    rooms: str = ""
    year_built: str = ""
    address: str = ""
    description: str = ""
    features: list[str] = field(default_factory=list)
    hero_image: bytes | None = None
    gallery_images: list[bytes] = field(default_factory=list)


_LABEL_PATTERNS = {
    "price": re.compile(
        r"(?:kaufpreis|preis|angebotspreis)\s*[:\-]?\s*([\d.,]+\s?(?:€|eur))",
        re.IGNORECASE,
    ),
    "price_bare": re.compile(r"([\d]{1,3}(?:[.\s]\d{3})+(?:,\d+)?)\s?€"),
    "area": re.compile(
        r"(?:wohnfl(?:ä|ae)che|wohnfl\.)\s*[:\-]?\s*([\d.,]+)\s?(?:m²|m2|qm)",
        re.IGNORECASE,
    ),
    "area_bare": re.compile(r"([\d]+(?:,\d+)?)\s?(?:m²|m2|qm)\s*wohnfl", re.IGNORECASE),
    "plot_area": re.compile(
        r"(?:grundst(?:ü|ue)cksfl(?:ä|ae)che|grundst(?:ü|ue)ck)\s*[:\-]?\s*([\d.,]+)\s?(?:m²|m2|qm)",
        re.IGNORECASE,
    ),
    "rooms": re.compile(r"([\d]+(?:,\d+)?)\s?(?:zimmer|zi\.)", re.IGNORECASE),
    "year_built": re.compile(r"baujahr\s*[:\-]?\s*(\d{4})", re.IGNORECASE),
    "address": re.compile(r"(\d{5})\s+([A-ZÄÖÜ][a-zäöüß\-]+(?:\s[A-ZÄÖÜ][a-zäöüß\-]+)*)"),
}

_FEATURE_KEYWORDS = [
    "balkon", "terrasse", "garten", "einbauküche", "keller", "garage",
    "stellplatz", "fußbodenheizung", "aufzug", "kamin", "sauna",
    "denkmalschutz", "altbau", "neubau", "barrierefrei", "energieeffizienz",
]

_STOPWORDS_FOR_TITLE = ("exposé", "expose", "immobilienangebot", "seite")


def _clean_text(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _extract_title(doc: fitz.Document) -> str | None:
    """Nimmt die Textzeile mit der größten Schriftgröße auf den ersten beiden Seiten."""
    best_text, best_size = None, 0.0
    for page in doc[:2]:
        info = page.get_text("dict")
        for block in info.get("blocks", []):
            for line in block.get("lines", []):
                line_text = "".join(span["text"] for span in line["spans"]).strip()
                if not line_text or len(line_text) < 4:
                    continue
                if line_text.lower() in _STOPWORDS_FOR_TITLE:
                    continue
                max_size = max((span["size"] for span in line["spans"]), default=0)
                if max_size > best_size and len(line_text) < 120:
                    best_size, best_text = max_size, line_text
    return best_text


def _extract_fields(full_text: str) -> dict:
    fields = {}
    for key in ("price", "area", "plot_area", "rooms", "year_built"):
        m = _LABEL_PATTERNS[key].search(full_text)
        if not m and key + "_bare" in _LABEL_PATTERNS:
            m = _LABEL_PATTERNS[key + "_bare"].search(full_text)
        if m:
            fields[key] = m.group(1).strip()
    addr_m = _LABEL_PATTERNS["address"].search(full_text)
    if addr_m:
        fields["address"] = f"{addr_m.group(1)} {addr_m.group(2)}"
    return fields


_NEGATION_WORDS = ("nicht", "kein", "keine", "keinen", "ohne")


def _extract_features(full_text: str) -> list[str]:
    lower = full_text.lower()
    found = []
    for kw in _FEATURE_KEYWORDS:
        for m in re.finditer(re.escape(kw), lower):
            sentence_start = max(lower.rfind(".", 0, m.start()), lower.rfind("\n\n", 0, m.start()))
            sentence_end_rel = lower[m.end():m.end() + 60].find(".")
            sentence_end = m.end() + sentence_end_rel if sentence_end_rel != -1 else m.end() + 60
            sentence = lower[max(0, sentence_start):sentence_end]
            if any(neg in sentence for neg in _NEGATION_WORDS):
                continue
            found.append(kw.capitalize())
            break
    return found


_HEADING_PREFIXES = ("objektbeschreibung", "beschreibung", "lagebeschreibung", "ausstattung")


def _extract_description(full_text: str) -> str:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", full_text) if len(p.strip()) > 80]
    if not paragraphs:
        lines = [l.strip() for l in full_text.splitlines() if len(l.strip()) > 40]
        text = " ".join(lines[:6])[:1200]
    else:
        paragraphs.sort(key=len, reverse=True)
        text = _clean_text(paragraphs[0])[:1500]

    first_line, _, rest = text.partition("\n")
    if first_line.strip().lower() in _HEADING_PREFIXES and rest:
        text = rest.strip()
    return text


def _extract_images(doc: fitz.Document) -> list[bytes]:
    seen_xrefs = set()
    candidates = []
    for page in doc:
        for img in page.get_images(full=True):
            xref = img[0]
            if xref in seen_xrefs:
                continue
            seen_xrefs.add(xref)
            try:
                base = doc.extract_image(xref)
                data = base["image"]
                with Image.open(io.BytesIO(data)) as im:
                    w, h = im.size
                    if w < MIN_IMAGE_SIDE or h < MIN_IMAGE_SIDE:
                        continue
                    if im.mode not in ("RGB", "RGBA"):
                        im = im.convert("RGB")
                    buf = io.BytesIO()
                    im.save(buf, format="JPEG", quality=88)
                    candidates.append((w * h, buf.getvalue()))
            except Exception:
                continue
    candidates.sort(key=lambda c: c[0], reverse=True)
    return [c[1] for c in candidates[:MAX_GALLERY_IMAGES]]


def extract_expose(pdf_bytes: bytes) -> ExposeData:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    full_text = "\n".join(page.get_text() for page in doc)
    full_text = _clean_text(full_text)

    data = ExposeData()

    title = _extract_title(doc)
    if title:
        data.title = title

    fields = _extract_fields(full_text)
    data.price = fields.get("price", "")
    data.area = fields.get("area", "")
    data.plot_area = fields.get("plot_area", "")
    data.rooms = fields.get("rooms", "")
    data.year_built = fields.get("year_built", "")
    data.address = fields.get("address", "")

    data.features = _extract_features(full_text)
    data.description = _extract_description(full_text)

    images = _extract_images(doc)
    if images:
        data.hero_image = images[0]
        data.gallery_images = images[1:]

    doc.close()
    return data
