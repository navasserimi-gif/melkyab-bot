"""Rendert die extrahierten Objektdaten als gebrandetes MaYa-Investment-PDF."""

from __future__ import annotations

import base64
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

from company import COMPANY
from extraction import ExposeData

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
LOGO_PATH = BASE_DIR / "static" / "logo_cropped.jpg"

_env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))


def _to_data_uri(data: bytes, mime: str = "image/jpeg") -> str:
    return f"data:{mime};base64," + base64.b64encode(data).decode("ascii")


def render_expose_pdf(data: ExposeData) -> bytes:
    template = _env.get_template("expose.html")

    logo_uri = _to_data_uri(LOGO_PATH.read_bytes(), "image/jpeg")
    hero_uri = _to_data_uri(data.hero_image) if data.hero_image else None
    gallery_uris = [_to_data_uri(img) for img in data.gallery_images]

    html_str = template.render(
        data={
            "title": data.title,
            "price": data.price,
            "area": data.area,
            "plot_area": data.plot_area,
            "rooms": data.rooms,
            "year_built": data.year_built,
            "address": data.address,
            "description": data.description,
            "features": data.features,
            "hero_image_uri": hero_uri,
            "gallery_uris": gallery_uris,
        },
        logo_uri=logo_uri,
        company=COMPANY,
    )

    pdf_bytes = HTML(string=html_str, base_url=str(TEMPLATES_DIR)).write_pdf()
    return pdf_bytes
