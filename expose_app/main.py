"""
MaYa Investment — Exposé Generator
Nimmt ein externes Immobilien-Exposé (PDF) entgegen und erstellt daraus
ein gebrandetes Katalog-Exposé im Design von MaYa Investment GmbH.
"""

from __future__ import annotations

import io
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from extraction import extract_expose
from pdf_render import render_expose_pdf

BASE_DIR = Path(__file__).resolve().parent
MAX_UPLOAD_BYTES = 25 * 1024 * 1024

app = FastAPI(title="MaYa Investment Exposé Generator")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    html = (BASE_DIR / "templates" / "index.html").read_text(encoding="utf-8")
    return HTMLResponse(html)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/generate")
async def generate(file: UploadFile = File(...)) -> StreamingResponse:
    if file.content_type not in ("application/pdf", "application/octet-stream") and not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Bitte eine PDF-Datei hochladen.")

    pdf_bytes = await file.read()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Die Datei ist leer.")
    if len(pdf_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="Die Datei ist zu groß (max. 25 MB).")

    try:
        expose_data = extract_expose(pdf_bytes)
    except Exception:
        raise HTTPException(status_code=422, detail="Die PDF-Datei konnte nicht gelesen werden.")

    try:
        output_pdf = render_expose_pdf(expose_data)
    except Exception:
        raise HTTPException(status_code=500, detail="Beim Erstellen des Exposés ist ein Fehler aufgetreten.")

    filename = "MaYa-Investment-Expose.pdf"
    return StreamingResponse(
        io.BytesIO(output_pdf),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
