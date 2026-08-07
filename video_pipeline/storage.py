"""
Zugriff auf den externen Objekt-Speicher (Cloudflare R2, S3-kompatibel).

Warum R2 und nicht direkt Google Drive fürs Processing? R2 hat keine
Egress-Kosten — der Worker liest jedes Rohvideo mehrfach (Szenenerkennung,
Technik-Analyse, Vision-API-Sampling, finales Rendering) und schreibt drei
Output-Varianten pro Projekt zurück. Bei Drive/S3 würde das schnell teuer.
Der Google-Drive-"Posteingang" (siehe n8n-Workflow) ist nur die
Upload-Komfortfunktion für den Nutzer; n8n synct neue Ordner von dort
automatisch nach R2, bevor dieser Worker überhaupt startet.
"""
from __future__ import annotations

import logging
from pathlib import Path

import boto3
from botocore.client import Config as BotoConfig

from . import config

logger = logging.getLogger(__name__)

_client = None


def _r2_client():
    global _client
    if _client is None:
        _client = boto3.client(
            "s3",
            endpoint_url=config.R2_ENDPOINT_URL,
            aws_access_key_id=config.R2_ACCESS_KEY_ID,
            aws_secret_access_key=config.R2_SECRET_ACCESS_KEY,
            config=BotoConfig(signature_version="s3v4", retries={"max_attempts": 5, "mode": "adaptive"}),
            region_name="auto",
        )
    return _client


def list_raw_clips(project_id: str) -> list[str]:
    """Listet alle Rohvideo-Objekt-Keys unter raw/{project_id}/ ."""
    prefix = f"raw/{project_id}/"
    client = _r2_client()
    keys: list[str] = []
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=config.R2_BUCKET_RAW, Prefix=prefix):
        for obj in page.get("Contents", []):
            if obj["Key"].lower().endswith((".mp4", ".mov", ".mxf", ".avi")):
                keys.append(obj["Key"])
    logger.info("Projekt %s: %d Rohvideos gefunden", project_id, len(keys))
    return keys


def download(key: str, dest_dir: str, bucket: str | None = None) -> Path:
    dest = Path(dest_dir) / Path(key).name
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        _r2_client().download_file(bucket or config.R2_BUCKET_RAW, key, str(dest))
    return dest


def upload_output(local_path: str, project_id: str, filename: str) -> str:
    key = f"outputs/{project_id}/{filename}"
    _r2_client().upload_file(local_path, config.R2_BUCKET_OUTPUT, key)
    return key


def presigned_url(key: str, bucket: str | None = None) -> str:
    return _r2_client().generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket or config.R2_BUCKET_OUTPUT, "Key": key},
        ExpiresIn=config.PRESIGNED_URL_TTL_SECONDS,
    )
