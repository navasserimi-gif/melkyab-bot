"""
MelkYab — Geschäftsmodell-Umfrage-Bot / ربات نظرسنجی ایده‌های کسب‌وکار
Zweisprachig: Deutsch & Persisch / دو زبانه: آلمانی و فارسی

Ablauf:
  1. Der Admin postet mit /umfrage eine Ankündigung in der Telegram-Gruppe.
  2. Interessenten klicken auf den Button und landen im privaten Chat mit dem Bot.
  3. Der Bot fragt Sprache + 7 Fragen ab (Geschäftsmodell, Kapital, Stadt,
     Telefon, Name, E-Mail, Startzeitpunkt).
  4. Jede fertige Antwort wird in einer CSV-Datei gespeichert, optional in
     Google Sheets angehängt, und der Admin bekommt sofort eine
     Telegram-Nachricht (+ optional E-Mail) mit den neuen Daten.
  5. /liste (nur Admin) zeigt eine Zusammenfassung + schickt die CSV-Datei.
"""

import csv
import json
import logging
import os
import re
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("melkyab_business_survey_bot")

# ══════════════════════════════════════════════════════════
BOT_TOKEN = os.environ.get("BUSINESS_BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
CSV_DATEI = "business_leads.csv"

# Optional: Google Sheets (siehe docs/BUSINESS_SURVEY_BOT.md)
GOOGLE_SHEETS_CREDENTIALS_JSON = os.environ.get("GOOGLE_SHEETS_CREDENTIALS_JSON")
GOOGLE_SHEET_ID = os.environ.get("GOOGLE_SHEET_ID")
GOOGLE_SHEET_WORKSHEET = os.environ.get("GOOGLE_SHEET_WORKSHEET", "Leads")

# Optional: E-Mail-Benachrichtigung (gleiche Variablen wie immobilien_analyzer)
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "465"))
SMTP_USER = os.environ.get("SMTP_USER")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")
RECIPIENT_EMAIL = os.environ.get("RECIPIENT_EMAIL") or SMTP_USER
# ══════════════════════════════════════════════════════════

# Konversations-Status
(LANG, GESCHAEFT, GESCHAEFT_FREI, KAPITAL, STADT, TELEFON,
 NAME, EMAIL, STARTZEIT, STARTZEIT_FREI) = range(10)

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

CSV_HEADER = [
    "Datum / تاریخ",
    "Sprache / زبان",
    "Geschäftsmodell / مدل کسب‌وکار",
    "Kapital (€) / سرمایه (یورو)",
    "Stadt / شهر",
    "Telefonnummer / شماره تلفن",
    "Name / نام",
    "E-Mail / ایمیل",
    "Startzeitpunkt / زمان شروع",
    "Telegram User ID",
    "Telegram Username",
]

# ── Texte (DE + FA) ──────────────────────────────────────
TXT = {
    "de": {
        "geschaeft_frage": "1️⃣ *Welches Geschäftsmodell suchen Sie?*\n\n(z. B. Kiosk, Gastronomie, Industriebetrieb …)\nWählen Sie eine Option oder tippen Sie selbst etwas ein:",
        "geschaeft_frei": "✏️ Bitte schreiben Sie, welches Geschäftsmodell Sie suchen:",
        "kapital_frage": "2️⃣ *Wie viel Eigenkapital / Budget steht Ihnen zur Verfügung?*\n\nBitte als Zahl in Euro eingeben (z. B. 20000).",
        "kapital_error": "⚠️ Bitte geben Sie eine gültige Zahl ein. Beispiel: 20000",
        "stadt_frage": "3️⃣ *In welcher Stadt suchen Sie ein Business?*",
        "telefon_frage": "4️⃣ *Bitte hinterlassen Sie Ihre Telefonnummer.*\n\nSie können unten auf den Button tippen oder die Nummer selbst eingeben.",
        "telefon_button": "📱 Nummer teilen",
        "name_frage": "5️⃣ *Bitte schreiben Sie Ihren Vor- und Nachnamen.*",
        "email_frage": "6️⃣ *Bitte geben Sie Ihre E-Mail-Adresse ein.*",
        "email_error": "⚠️ Das sieht nicht nach einer gültigen E-Mail-Adresse aus. Bitte erneut versuchen.",
        "start_frage": "7️⃣ *Ab wann möchten Sie mit dem Business starten?*",
        "start_frei": "✏️ Bitte schreiben Sie den gewünschten Zeitpunkt:",
        "fertig": (
            "✅ *Vielen Dank!*\n\n"
            "Ihre Angaben wurden erfolgreich übermittelt. "
            "Wir melden uns bei Ihnen, sobald ein passendes Angebot verfügbar ist."
        ),
        "abgebrochen": "❌ Umfrage abgebrochen. Mit /start können Sie jederzeit neu beginnen.",
        "opts_geschaeft": [
            ("Kiosk", "kiosk"), ("Gastronomie", "gastro"),
            ("Industriebetrieb", "industrie"), ("Handel / Einzelhandel", "handel"),
            ("✏️ Andere (selbst eingeben)", "other"),
        ],
        "opts_start": [
            ("Sofort", "sofort"), ("1–3 Monate", "1_3"),
            ("3–6 Monate", "3_6"), ("6–12 Monate", "6_12"),
            ("✏️ Anderer Zeitpunkt", "other"),
        ],
    },
    "fa": {
        "geschaeft_frage": "1️⃣ *به دنبال چه مدل کسب‌وکاری هستید؟*\n\n(مثلاً کیوسک، رستوران/گاستروفروشی، کارخانه صنعتی …)\nیک گزینه را انتخاب کنید یا خودتان بنویسید:",
        "geschaeft_frei": "✏️ لطفاً بنویسید به دنبال چه مدل کسب‌وکاری هستید:",
        "kapital_frage": "2️⃣ *چقدر سرمایه شخصی / بودجه در اختیار دارید؟*\n\nلطفاً به‌صورت عدد و به یورو وارد کنید (مثلاً 20000).",
        "kapital_error": "⚠️ لطفاً یک عدد معتبر وارد کنید. مثال: 20000",
        "stadt_frage": "3️⃣ *در کدام شهر به دنبال کسب‌وکار هستید؟*",
        "telefon_frage": "4️⃣ *لطفاً شماره تلفن خود را وارد کنید.*\n\nمی‌توانید از دکمه پایین استفاده کنید یا شماره را خودتان تایپ کنید.",
        "telefon_button": "📱 اشتراک‌گذاری شماره",
        "name_frage": "5️⃣ *لطفاً نام و نام خانوادگی خود را بنویسید.*",
        "email_frage": "6️⃣ *لطفاً آدرس ایمیل خود را وارد کنید.*",
        "email_error": "⚠️ این یک آدرس ایمیل معتبر به نظر نمی‌رسد. لطفاً دوباره امتحان کنید.",
        "start_frage": "7️⃣ *از چه زمانی می‌خواهید کسب‌وکار را شروع کنید؟*",
        "start_frei": "✏️ لطفاً زمان مورد نظر خود را بنویسید:",
        "fertig": (
            "✅ *متشکریم!*\n\n"
            "اطلاعات شما با موفقیت ثبت شد. "
            "به محض وجود پیشنهاد مناسب، با شما تماس خواهیم گرفت."
        ),
        "abgebrochen": "❌ نظرسنجی لغو شد. برای شروع دوباره /start را بزنید.",
        "opts_geschaeft": [
            ("کیوسک", "kiosk"), ("رستوران / گاستروفروشی", "gastro"),
            ("کارخانه صنعتی", "industrie"), ("تجارت / خرده‌فروشی", "handel"),
            ("✏️ سایر (نوشتن دستی)", "other"),
        ],
        "opts_start": [
            ("بلافاصله", "sofort"), ("۱ تا ۳ ماه دیگر", "1_3"),
            ("۳ تا ۶ ماه دیگر", "3_6"), ("۶ تا ۱۲ ماه دیگر", "6_12"),
            ("✏️ زمان دیگر", "other"),
        ],
    },
}

GESCHAEFT_LABELS = {
    "kiosk": "Kiosk", "gastro": "Gastronomie", "industrie": "Industriebetrieb",
    "handel": "Handel / Einzelhandel",
}
START_LABELS = {
    "sofort": "Sofort", "1_3": "1–3 Monate", "3_6": "3–6 Monate", "6_12": "6–12 Monate",
}

GROUP_ANNOUNCEMENT = (
    "📢 *Geschäftsmodell gesucht? / به دنبال یک ایده کسب‌وکار هستید؟*\n\n"
    "Wenn Sie auf der Suche nach einer Geschäftsmodell-Idee sind (Kiosk, Gastronomie, "
    "Industriebetrieb u.v.m.), beantworten Sie gerne ein paar kurze Fragen — dauert nur 2 Minuten.\n\n"
    "اگر به دنبال یک ایده کسب‌وکار هستید (کیوسک، رستوران، کارخانه صنعتی و غیره)، "
    "لطفاً چند سؤال کوتاه را پاسخ دهید — فقط ۲ دقیقه زمان می‌برد.\n\n"
    "👇 Klicken Sie unten / روی دکمه زیر کلیک کنید"
)


def _kb(options, prefix):
    return InlineKeyboardMarkup([[InlineKeyboardButton(label, callback_data=f"{prefix}_{code}")] for label, code in options])


# ── CSV ──────────────────────────────────────────────────
def speichern(user, d):
    neu = not os.path.exists(CSV_DATEI)
    with open(CSV_DATEI, "a", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        if neu:
            w.writerow(CSV_HEADER)
        w.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            d.get("lang", "—"),
            d.get("geschaeft", "—"),
            d.get("kapital", "—"),
            d.get("stadt", "—"),
            d.get("telefon", "—"),
            d.get("name", "—"),
            d.get("email", "—"),
            d.get("startzeit", "—"),
            user.id,
            f"@{user.username}" if user.username else "—",
        ])


# ── Google Sheets (optional) ─────────────────────────────
_sheets_client = None
_sheets_ready = bool(GOOGLE_SHEETS_CREDENTIALS_JSON and GOOGLE_SHEET_ID)


def _get_worksheet():
    global _sheets_client
    if not _sheets_ready:
        return None
    try:
        import gspread

        if _sheets_client is None:
            creds = json.loads(GOOGLE_SHEETS_CREDENTIALS_JSON)
            _sheets_client = gspread.service_account_from_dict(creds)
        sheet = _sheets_client.open_by_key(GOOGLE_SHEET_ID)
        try:
            ws = sheet.worksheet(GOOGLE_SHEET_WORKSHEET)
        except gspread.WorksheetNotFound:
            ws = sheet.add_worksheet(title=GOOGLE_SHEET_WORKSHEET, rows=1000, cols=len(CSV_HEADER))
            ws.append_row(CSV_HEADER)
        return ws
    except Exception:
        log.exception("Google Sheets nicht erreichbar — Eintrag wurde trotzdem in CSV gespeichert.")
        return None


def sheets_append(user, d):
    ws = _get_worksheet()
    if ws is None:
        return
    try:
        ws.append_row([
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            d.get("lang", "—"),
            d.get("geschaeft", "—"),
            d.get("kapital", "—"),
            d.get("stadt", "—"),
            d.get("telefon", "—"),
            d.get("name", "—"),
            d.get("email", "—"),
            d.get("startzeit", "—"),
            str(user.id),
            f"@{user.username}" if user.username else "—",
        ])
    except Exception:
        log.exception("Google Sheets append_row fehlgeschlagen.")


# ── E-Mail (optional) ────────────────────────────────────
def email_notify(user, d):
    if not (SMTP_USER and SMTP_PASSWORD and RECIPIENT_EMAIL):
        return
    try:
        body = (
            f"<h3>📋 Neue Geschäftsmodell-Anfrage</h3>"
            f"<p><b>Geschäftsmodell:</b> {d.get('geschaeft','—')}<br>"
            f"<b>Kapital:</b> {d.get('kapital','—')} €<br>"
            f"<b>Stadt:</b> {d.get('stadt','—')}<br>"
            f"<b>Telefon:</b> {d.get('telefon','—')}<br>"
            f"<b>Name:</b> {d.get('name','—')}<br>"
            f"<b>E-Mail:</b> {d.get('email','—')}<br>"
            f"<b>Startzeitpunkt:</b> {d.get('startzeit','—')}<br>"
            f"<b>Telegram:</b> @{user.username or '—'} (ID {user.id})</p>"
        )
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "📋 Neue Geschäftsmodell-Anfrage — MelkYab"
        msg["From"] = SMTP_USER
        msg["To"] = RECIPIENT_EMAIL
        msg.attach(MIMEText(body, "html", "utf-8"))
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=30) as server:
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, [RECIPIENT_EMAIL], msg.as_string())
    except Exception:
        log.exception("E-Mail-Benachrichtigung fehlgeschlagen.")


# ── Admin-Benachrichtigung (Telegram) ────────────────────
async def admin_notify(context, user, d):
    tg_link = f"tg://user?id={user.id}"
    msg = (
        f"📋 *درخواست جدید — ایده کسب‌وکار*\n\n"
        f"👤 [{user.first_name or '—'}]({tg_link}) | @{user.username or '—'}\n"
        f"🆔 `{user.id}`\n\n"
        f"🏪 مدل کسب‌وکار: `{d.get('geschaeft','—')}`\n"
        f"💰 سرمایه: `{d.get('kapital','—')} €`\n"
        f"🏙️ شهر: `{d.get('stadt','—')}`\n"
        f"📞 تلفن: `{d.get('telefon','—')}`\n"
        f"🙍 نام: `{d.get('name','—')}`\n"
        f"📧 ایمیل: `{d.get('email','—')}`\n"
        f"📅 زمان شروع: `{d.get('startzeit','—')}`"
    )
    if ADMIN_ID:
        await context.bot.send_message(ADMIN_ID, msg, parse_mode="Markdown", disable_web_page_preview=True)


# ── /umfrage — Ankündigung posten (nur Admin) ────────────
async def cmd_umfrage(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    me = await ctx.bot.get_me()
    url = f"https://t.me/{me.username}?start=umfrage"
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("▶️ Umfrage starten / شروع پرسشنامه", url=url)]])
    await update.message.reply_text(GROUP_ANNOUNCEMENT, parse_mode="Markdown", reply_markup=kb)


# ── /start ────────────────────────────────────────────────
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        me = await ctx.bot.get_me()
        url = f"https://t.me/{me.username}?start=umfrage"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("▶️ Privater Chat / چت خصوصی", url=url)]])
        await update.message.reply_text(
            "Bitte antworten Sie im privaten Chat mit dem Bot. / لطفاً در چت خصوصی با ربات پاسخ دهید.",
            reply_markup=kb,
        )
        return ConversationHandler.END

    ctx.user_data.clear()
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🇩🇪 Deutsch", callback_data="lang_de")],
        [InlineKeyboardButton("🇮🇷 فارسی", callback_data="lang_fa")],
    ])
    await update.message.reply_text(
        "🌍 Bitte wählen Sie Ihre Sprache / لطفاً زبان خود را انتخاب کنید",
        reply_markup=kb,
    )
    return LANG


async def cb_lang(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    lang = q.data.split("_")[1]
    ctx.user_data["lang"] = lang
    t = TXT[lang]
    await q.edit_message_text(t["geschaeft_frage"], parse_mode="Markdown", reply_markup=_kb(t["opts_geschaeft"], "geschaeft"))
    return GESCHAEFT


async def cb_geschaeft(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    lang = ctx.user_data["lang"]
    t = TXT[lang]
    code = q.data.split("_", 1)[1]
    if code == "other":
        await q.edit_message_text(t["geschaeft_frei"])
        return GESCHAEFT_FREI
    ctx.user_data["geschaeft"] = GESCHAEFT_LABELS.get(code, code)
    await q.edit_message_text(t["kapital_frage"], parse_mode="Markdown")
    return KAPITAL


async def msg_geschaeft_frei(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    lang = ctx.user_data["lang"]
    t = TXT[lang]
    ctx.user_data["geschaeft"] = update.message.text.strip()
    await update.message.reply_text(t["kapital_frage"], parse_mode="Markdown")
    return KAPITAL


async def msg_kapital(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    lang = ctx.user_data["lang"]
    t = TXT[lang]
    try:
        wert = float(update.message.text.replace(",", ".").replace("€", "").strip())
        ctx.user_data["kapital"] = int(wert)
    except ValueError:
        await update.message.reply_text(t["kapital_error"])
        return KAPITAL
    await update.message.reply_text(t["stadt_frage"], parse_mode="Markdown")
    return STADT


async def msg_stadt(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    lang = ctx.user_data["lang"]
    t = TXT[lang]
    ctx.user_data["stadt"] = update.message.text.strip()
    kb = ReplyKeyboardMarkup(
        [[KeyboardButton(t["telefon_button"], request_contact=True)]],
        resize_keyboard=True, one_time_keyboard=True,
    )
    await update.message.reply_text(t["telefon_frage"], parse_mode="Markdown", reply_markup=kb)
    return TELEFON


async def msg_telefon(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    lang = ctx.user_data["lang"]
    t = TXT[lang]
    if update.message.contact:
        ctx.user_data["telefon"] = update.message.contact.phone_number
    else:
        ctx.user_data["telefon"] = update.message.text.strip()
    await update.message.reply_text(t["name_frage"], parse_mode="Markdown", reply_markup=ReplyKeyboardRemove())
    return NAME


async def msg_name(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    lang = ctx.user_data["lang"]
    t = TXT[lang]
    ctx.user_data["name"] = update.message.text.strip()
    await update.message.reply_text(t["email_frage"], parse_mode="Markdown")
    return EMAIL


async def msg_email(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    lang = ctx.user_data["lang"]
    t = TXT[lang]
    email = update.message.text.strip()
    if not EMAIL_REGEX.match(email):
        await update.message.reply_text(t["email_error"])
        return EMAIL
    ctx.user_data["email"] = email
    await update.message.reply_text(t["start_frage"], parse_mode="Markdown", reply_markup=_kb(t["opts_start"], "startzeit"))
    return STARTZEIT


async def _abschliessen(update_message, ctx, user):
    lang = ctx.user_data["lang"]
    t = TXT[lang]
    speichern(user, ctx.user_data)
    sheets_append(user, ctx.user_data)
    await admin_notify(ctx, user, ctx.user_data)
    email_notify(user, ctx.user_data)
    await update_message.reply_text(t["fertig"], parse_mode="Markdown")


async def cb_startzeit(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    lang = ctx.user_data["lang"]
    t = TXT[lang]
    code = q.data.split("_", 1)[1]
    if code == "other":
        await q.edit_message_text(t["start_frei"])
        return STARTZEIT_FREI
    ctx.user_data["startzeit"] = START_LABELS.get(code, code)
    await q.edit_message_text("⏳ …")
    await _abschliessen(q.message, ctx, q.from_user)
    return ConversationHandler.END


async def msg_startzeit_frei(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["startzeit"] = update.message.text.strip()
    await _abschliessen(update.message, ctx, update.effective_user)
    return ConversationHandler.END


async def cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    lang = ctx.user_data.get("lang", "de")
    await update.message.reply_text(TXT[lang]["abgebrochen"], reply_markup=ReplyKeyboardRemove())
    ctx.user_data.clear()
    return ConversationHandler.END


# ── /liste — nur Admin ───────────────────────────────────
async def cmd_liste(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not os.path.exists(CSV_DATEI):
        await update.message.reply_text("هنوز هیچ درخواستی ثبت نشده. / Noch keine Anfragen vorhanden.")
        return

    with open(CSV_DATEI, "r", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))
    data_rows = rows[1:]
    if not data_rows:
        await update.message.reply_text("هنوز هیچ درخواستی ثبت نشده. / Noch keine Anfragen vorhanden.")
        return

    lines = []
    for i, r in enumerate(data_rows, 1):
        tg_link = f"tg://user?id={r[9]}" if len(r) > 9 and r[9] else None
        name = r[6] if len(r) > 6 else "—"
        label = f"[{name}]({tg_link})" if tg_link else name
        lines.append(
            f"*{i}.* {label}\n"
            f"   🏪 {r[2] if len(r)>2 else '—'} | 💰 {r[3] if len(r)>3 else '—'} € | 🏙️ {r[4] if len(r)>4 else '—'}\n"
            f"   📞 {r[5] if len(r)>5 else '—'} | 📧 {r[7] if len(r)>7 else '—'} | 📅 {r[8] if len(r)>8 else '—'}\n"
        )

    summary = f"📊 *لیست درخواست‌ها — {len(data_rows)} مورد*\n━━━━━━━━━━━━━━━━━━\n\n"
    full_msg = summary + "\n".join(lines)
    if len(full_msg) <= 4000:
        await update.message.reply_text(full_msg, parse_mode="Markdown", disable_web_page_preview=True)
    else:
        await update.message.reply_text(summary, parse_mode="Markdown")
        for i in range(0, len(lines), 10):
            await update.message.reply_text("\n".join(lines[i:i + 10]), parse_mode="Markdown", disable_web_page_preview=True)

    await update.message.reply_document(
        document=open(CSV_DATEI, "rb"),
        filename=f"business_leads_{datetime.now().strftime('%Y%m%d')}.csv",
        caption="📎 CSV-Datei aller Anfragen / فایل کامل همه درخواست‌ها",
    )


# ── Main ─────────────────────────────────────────────────
def main():
    if not BOT_TOKEN:
        raise SystemExit("BUSINESS_BOT_TOKEN ist nicht gesetzt.")

    app = Application.builder().token(BOT_TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            LANG: [CallbackQueryHandler(cb_lang, pattern="^lang_")],
            GESCHAEFT: [CallbackQueryHandler(cb_geschaeft, pattern="^geschaeft_")],
            GESCHAEFT_FREI: [MessageHandler(filters.TEXT & ~filters.COMMAND, msg_geschaeft_frei)],
            KAPITAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, msg_kapital)],
            STADT: [MessageHandler(filters.TEXT & ~filters.COMMAND, msg_stadt)],
            TELEFON: [MessageHandler((filters.TEXT | filters.CONTACT) & ~filters.COMMAND, msg_telefon)],
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, msg_name)],
            EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, msg_email)],
            STARTZEIT: [CallbackQueryHandler(cb_startzeit, pattern="^startzeit_")],
            STARTZEIT_FREI: [MessageHandler(filters.TEXT & ~filters.COMMAND, msg_startzeit_frei)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(conv)
    app.add_handler(CommandHandler("umfrage", cmd_umfrage))
    app.add_handler(CommandHandler("liste", cmd_liste))
    print("✅ MelkYab Business-Survey-Bot läuft — ربات نظرسنجی کسب‌وکار فعال است")
    app.run_polling()


if __name__ == "__main__":
    main()
