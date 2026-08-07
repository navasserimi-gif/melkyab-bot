"""
Fertig-Meldung per Telegram — nutzt bewusst den bereits vorhandenen Bot
dieses Repos (BOT_TOKEN/ADMIN_ID, siehe melkyab_kredit_bot.py) statt einen
neuen Kanal aufzubauen. Der Nutzer bekommt dieselbe Alltags-Oberfläche
(Telegram), die er für den Immobilien-Analyzer bereits nutzt.
"""
from __future__ import annotations

import logging

from telegram import Bot
from telegram.constants import ParseMode

from . import config

logger = logging.getLogger(__name__)


async def notify_project_done(project_id: str, links: dict[str, str]) -> None:
    if not config.BOT_TOKEN or not config.NOTIFY_CHAT_ID:
        logger.warning("BOT_TOKEN/VIDEO_NOTIFY_CHAT_ID nicht gesetzt — Benachrichtigung übersprungen.")
        return
    bot = Bot(token=config.BOT_TOKEN)
    lines = [f"🎬 *Video-Projekt {project_id} fertig!*", ""]
    for platform, url in links.items():
        lines.append(f"• [{platform}]({url})")
    await bot.send_message(
        chat_id=config.NOTIFY_CHAT_ID,
        text="\n".join(lines),
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True,
    )


async def notify_project_failed(project_id: str, error: str) -> None:
    if not config.BOT_TOKEN or not config.NOTIFY_CHAT_ID:
        return
    bot = Bot(token=config.BOT_TOKEN)
    await bot.send_message(
        chat_id=config.NOTIFY_CHAT_ID,
        text=f"⚠️ Video-Projekt {project_id} fehlgeschlagen:\n{error}",
    )
