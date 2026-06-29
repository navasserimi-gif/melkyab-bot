"""
MelkYab — Mieter-Anfrage-Bot / ربات ثبت درخواست مستأجر
Strukturierte Erfassung von Wohnungssuchenden (Deutsch / Farsi)
Vollständige Speicherung der Daten + Sofort-Report für den Admin
"""

import logging, csv, os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ConversationHandler, ContextTypes, filters
)

logging.basicConfig(level=logging.INFO)

# ══════════════════════════════════════════════════════════
BOT_TOKEN  = os.environ.get("BOT_TOKEN")        # von @BotFather
ADMIN_ID   = int(os.environ.get("ADMIN_ID"))    # numerische Telegram-ID — via @userinfobot
CSV_DATEI  = "melkyab_mietanfragen.csv"
# ══════════════════════════════════════════════════════════

# Gesprächsphasen (in vorgegebener Reihenfolge)
(SPRACHE, BESCHAEFTIGUNG, NETTOEINKOMMEN, SCHUFA,
 PERSONEN, AUFENTHALTSTITEL, SUCHORT, EINWILLIGUNG) = range(8)

# Aufenthaltstitel-Labels (Index = A/B/C)
TITEL_LABELS = {
    "de": [
        "A — Aufenthaltstitel (3 Jahre)",
        "B — Niederlassungserlaubnis",
        "C — Deutscher Pass",
    ],
    "fa": [
        "A — اجازه اقامت (۳ ساله)",
        "B — اجازه اقامت دائم (Niederlassungserlaubnis)",
        "C — پاسپورت آلمانی",
    ],
}

# ── Zweisprachige Texte ───────────────────────────────────
TXT = {
    "de": {
        "ask_beschaeftigung": (
            "💼 *Frage 1 von 7 — Beschäftigung*\n\n"
            "Sind Sie in einem Arbeitsverhältnis oder sind Sie berufstätig?\n"
            "_(z. B. Angestellt, Selbstständig, Beamter, Rentner, arbeitssuchend …)_"
        ),
        "ask_netto": (
            "💰 *Frage 2 von 7 — Nettoeinkommen*\n\n"
            "Wie hoch ist Ihr monatliches Nettoeinkommen? (in €)"
        ),
        "ask_schufa": (
            "📄 *Frage 3 von 7 — SCHUFA*\n\n"
            "Verfügen Sie über ein SCHUFA-Zertifikat?"
        ),
        "ask_personen": (
            "👥 *Frage 4 von 7 — Personenanzahl*\n\n"
            "Wie viele Personen werden in die Wohnung einziehen?"
        ),
        "ask_titel": (
            "🛂 *Frage 5 von 7 — Aufenthaltstitel*\n\n"
            "Welcher Aufenthaltstitel liegt vor?"
        ),
        "ask_ort": (
            "🏙️ *Frage 6 von 7 — Suchort*\n\n"
            "In welcher Stadt suchen Sie eine Wohnung?"
        ),
        "ask_einwilligung": (
            "🙏 *Vielen Dank für die Informationen, die Sie uns mitgeteilt haben. "
            "Wir schätzen Ihr Vertrauen.*\n\n"
            "ℹ️ *Hinweis zur Provision:*\n"
            "Für die Wohnungsvermittlung berechnen wir eine Provision von "
            "*2–3 Monatsmieten (Warmmiete)*, abhängig von der Wohnungsgröße und der Stadt.\n\n"
            "🔒 *Frage 7 von 7 — Datenschutz (DSGVO):*\n"
            "Gemäß DSGVO benötigen wir eine Widerrufserklärung. "
            "Stimmen Sie der Speicherung und Verarbeitung Ihrer Daten bei uns zu?"
        ),
        "btn_ja": "✅ Ja",
        "btn_nein": "❌ Nein",
        "err_zahl": "⚠️ Bitte geben Sie eine gültige Zahl ein. Beispiel: {bsp}",
        "err_text": "⚠️ Bitte geben Sie eine gültige Antwort ein.",
        "abgelehnt": (
            "Verstanden. Ohne Ihre Einwilligung dürfen wir Ihre Daten nicht speichern.\n"
            "Ihre Angaben wurden *nicht* gespeichert. Für einen Neustart: /start"
        ),
        "summary_head": "✅ *Zusammenfassung Ihrer Anfrage*",
        "lbl_sprache": "Sprache",
        "lbl_beschaeftigung": "Beschäftigungsstatus",
        "lbl_netto": "Nettoeinkommen",
        "lbl_schufa": "SCHUFA-Zertifikat",
        "lbl_personen": "Personenanzahl",
        "lbl_titel": "Aufenthaltstitel",
        "lbl_ort": "Suchstadt",
        "lbl_consent": "Datenverarbeitung akzeptiert",
        "ja": "Ja",
        "nein": "Nein",
        "outro": (
            "\nVielen Dank! Wir melden uns bei passenden Wohnungen.\n"
            "Für eine neue Anfrage: /start"
        ),
        "cancel": "❌ Abgebrochen. Für einen Neustart: /start",
        "offtopic": (
            "Ich bin ausschließlich für die Erfassung Ihrer Wohnungsanfrage zuständig. "
            "Bitte beantworten Sie die gestellte Frage."
        ),
    },
    "fa": {
        "ask_beschaeftigung": (
            "💼 *سؤال ۱ از ۷ — وضعیت شغلی*\n\n"
            "آیا شاغل هستید یا در یک رابطه کاری قرار دارید؟\n"
            "_(مثلاً: کارمند، خوداشتغال، کارمند دولت، بازنشسته، جویای کار …)_"
        ),
        "ask_netto": (
            "💰 *سؤال ۲ از ۷ — درآمد خالص*\n\n"
            "درآمد خالص ماهانه شما چقدر است؟ (به یورو)"
        ),
        "ask_schufa": (
            "📄 *سؤال ۳ از ۷ — شوفا (SCHUFA)*\n\n"
            "آیا گواهی شوفا (SCHUFA) دارید؟"
        ),
        "ask_personen": (
            "👥 *سؤال ۴ از ۷ — تعداد نفرات*\n\n"
            "چند نفر در این خانه ساکن خواهند شد؟"
        ),
        "ask_titel": (
            "🛂 *سؤال ۵ از ۷ — نوع اقامت*\n\n"
            "چه نوع اجازه اقامتی دارید؟"
        ),
        "ask_ort": (
            "🏙️ *سؤال ۶ از ۷ — شهر مورد نظر*\n\n"
            "در کدام شهر به دنبال خانه هستید؟"
        ),
        "ask_einwilligung": (
            "🙏 *از اطلاعاتی که در اختیار ما گذاشتید سپاسگزاریم. "
            "ما برای اعتماد شما ارزش قائلیم.*\n\n"
            "ℹ️ *توضیح درباره کمیسیون:*\n"
            "برای واسطه‌گری اجاره خانه، کمیسیونی معادل "
            "*۲ تا ۳ ماه اجاره (اجاره کامل / Warmmiete)* دریافت می‌کنیم؛ "
            "بسته به متراژ خانه و شهر.\n\n"
            "🔒 *سؤال ۷ از ۷ — حفاظت از داده‌ها (DSGVO):*\n"
            "طبق قانون DSGVO به اعلام رضایت شما نیاز داریم. "
            "آیا با ذخیره و پردازش اطلاعات خود نزد ما موافق هستید؟"
        ),
        "btn_ja": "✅ بله",
        "btn_nein": "❌ خیر",
        "err_zahl": "⚠️ لطفاً یک عدد معتبر وارد کنید. مثال: {bsp}",
        "err_text": "⚠️ لطفاً یک پاسخ معتبر وارد کنید.",
        "abgelehnt": (
            "متوجه شدم. بدون رضایت شما اجازه ذخیره اطلاعات را نداریم.\n"
            "اطلاعات شما ذخیره *نشد*. برای شروع مجدد: /start"
        ),
        "summary_head": "✅ *خلاصه درخواست شما*",
        "lbl_sprache": "زبان",
        "lbl_beschaeftigung": "وضعیت شغلی",
        "lbl_netto": "درآمد خالص",
        "lbl_schufa": "گواهی شوفا",
        "lbl_personen": "تعداد نفرات",
        "lbl_titel": "نوع اقامت",
        "lbl_ort": "شهر مورد نظر",
        "lbl_consent": "موافقت با پردازش داده‌ها",
        "ja": "بله",
        "nein": "خیر",
        "outro": (
            "\nسپاسگزاریم! در صورت یافتن خانه مناسب با شما تماس می‌گیریم.\n"
            "برای درخواست جدید: /start"
        ),
        "cancel": "❌ لغو شد. برای شروع مجدد: /start",
        "offtopic": (
            "من فقط مسئول ثبت درخواست خانه شما هستم. "
            "لطفاً به سؤال مطرح‌شده پاسخ دهید."
        ),
    },
}

START_MSG = (
    "🏠 *Willkommen / خوش آمدید*\n\n"
    "Bitte wählen Sie Ihre Sprache.\n"
    "لطفاً زبان خود را انتخاب کنید.\n\n"
    "Welche Sprache bevorzugen Sie? / کدام زبان را ترجیح می‌دهید؟"
)

# ── Helfer ────────────────────────────────────────────────
def lang(ctx):
    return ctx.user_data.get("sprache_code", "de")

def parse_zahl(text):
    return float(text.replace(",", ".").replace("€", "").strip())

# ── Speichern in CSV ──────────────────────────────────────
def speichern(user, d):
    neu = not os.path.exists(CSV_DATEI)
    with open(CSV_DATEI, "a", newline="", encoding="utf-8-sig") as csvf:
        w = csv.writer(csvf)
        if neu:
            w.writerow([
                "Datum", "User ID", "Username", "Name",
                "Sprache", "Beschäftigung", "Nettoeinkommen (€)",
                "SCHUFA", "Personen", "Aufenthaltstitel", "Suchstadt",
                "DSGVO akzeptiert",
            ])
        w.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            user.id,
            f"@{user.username}" if user.username else "—",
            user.first_name or "—",
            d.get("sprache", "—"),
            d.get("beschaeftigung", "—"),
            d.get("netto", "—"),
            "Ja" if d.get("schufa") else "Nein",
            d.get("personen", "—"),
            d.get("titel_code", "—"),
            d.get("ort", "—"),
            "Ja" if d.get("consent") else "Nein",
        ])

# ── Sofort-Benachrichtigung an Admin ──────────────────────
async def admin_notify(context, user, d):
    tg_link = f"tg://user?id={user.id}"
    msg = (
        f"📋 *Neue Mieter-Anfrage*\n\n"
        f"👤 Name: [{user.first_name or '—'}]({tg_link})\n"
        f"🔗 Username: @{user.username or '—'}\n"
        f"🆔 ID: `{user.id}`\n\n"
        f"🗣️ Sprache: {d.get('sprache', '—')}\n"
        f"💼 Beschäftigung: {d.get('beschaeftigung', '—')}\n"
        f"💰 Nettoeinkommen: `{d.get('netto', '—')} €`\n"
        f"📄 SCHUFA: {'Ja' if d.get('schufa') else 'Nein'}\n"
        f"👥 Personen: {d.get('personen', '—')}\n"
        f"🛂 Aufenthaltstitel: {d.get('titel_code', '—')}\n"
        f"🏙️ Suchstadt: {d.get('ort', '—')}\n"
        f"🔒 DSGVO: {'Ja' if d.get('consent') else 'Nein'}"
    )
    await context.bot.send_message(ADMIN_ID, msg,
                                   parse_mode="Markdown",
                                   disable_web_page_preview=True)

# ── Vollständiger Report für Admin (/liste) ───────────────
async def cmd_liste(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not os.path.exists(CSV_DATEI):
        await update.message.reply_text("Noch keine Anfragen vorhanden.")
        return

    with open(CSV_DATEI, "r", encoding="utf-8-sig") as csvf:
        rows = list(csv.reader(csvf))

    if len(rows) <= 1:
        await update.message.reply_text("Noch keine Anfragen vorhanden.")
        return

    data_rows = rows[1:]
    total = len(data_rows)
    summary = (
        f"📊 *MelkYab — Mieter-Anfragen*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📅 Report: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        f"👥 Gesamtanzahl Anfragen: *{total}*\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"*Liste:*\n\n"
    )

    lines = []
    for i, r in enumerate(data_rows, 1):
        # r: Datum, ID, Username, Name, Sprache, Beschäftigung, Netto,
        #    SCHUFA, Personen, Titel, Stadt, DSGVO
        tg_link = f"tg://user?id={r[1]}"
        lines.append(
            f"*{i}.* [{r[3]}]({tg_link}) | {r[2]}\n"
            f"   🆔 `{r[1]}` | 📅 {r[0]}\n"
            f"   💼 {r[5]} | 💰 `{r[6]} €` | 📄 SCHUFA: {r[7]}\n"
            f"   👥 {r[8]} | 🛂 {r[9]} | 🏙️ {r[10]} | 🔒 {r[11]}\n"
        )

    full_msg = summary + "\n".join(lines)
    if len(full_msg) <= 4000:
        await update.message.reply_text(full_msg, parse_mode="Markdown",
                                        disable_web_page_preview=True)
    else:
        await update.message.reply_text(summary, parse_mode="Markdown")
        for i in range(0, len(lines), 10):
            chunk = "\n".join(lines[i:i+10])
            await update.message.reply_text(chunk, parse_mode="Markdown",
                                            disable_web_page_preview=True)

    await update.message.reply_document(
        document=open(CSV_DATEI, "rb"),
        filename=f"melkyab_miet_{datetime.now().strftime('%Y%m%d')}.csv",
        caption="📎 Vollständige CSV aller Anfragen"
    )

# ── Handlers (Gesprächsablauf in vorgegebener Reihenfolge) ─
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data.clear()
    kb = [[
        InlineKeyboardButton("🇩🇪 Deutsch", callback_data="lang_de"),
        InlineKeyboardButton("🇮🇷 فارسی",   callback_data="lang_fa"),
    ]]
    await update.message.reply_text(START_MSG, parse_mode="Markdown",
                                    reply_markup=InlineKeyboardMarkup(kb))
    return SPRACHE

async def cb_sprache(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    code = q.data.split("_")[1]            # de | fa
    ctx.user_data["sprache_code"] = code
    ctx.user_data["sprache"] = "Deutsch" if code == "de" else "فارسی"
    t = TXT[code]
    await q.edit_message_text(t["ask_beschaeftigung"], parse_mode="Markdown")
    return BESCHAEFTIGUNG

async def msg_beschaeftigung(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    t = TXT[lang(ctx)]
    antwort = update.message.text.strip()
    if not antwort:
        await update.message.reply_text(t["err_text"])
        return BESCHAEFTIGUNG
    ctx.user_data["beschaeftigung"] = antwort
    await update.message.reply_text(t["ask_netto"], parse_mode="Markdown")
    return NETTOEINKOMMEN

async def msg_netto(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    t = TXT[lang(ctx)]
    try:
        ctx.user_data["netto"] = int(round(parse_zahl(update.message.text)))
    except Exception:
        await update.message.reply_text(t["err_zahl"].format(bsp="2500"))
        return NETTOEINKOMMEN
    kb = [[
        InlineKeyboardButton(t["btn_ja"],   callback_data="schufa_1"),
        InlineKeyboardButton(t["btn_nein"], callback_data="schufa_0"),
    ]]
    await update.message.reply_text(t["ask_schufa"], parse_mode="Markdown",
                                    reply_markup=InlineKeyboardMarkup(kb))
    return SCHUFA

async def cb_schufa(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    t = TXT[lang(ctx)]
    ctx.user_data["schufa"] = (q.data.split("_")[1] == "1")
    await q.edit_message_text(t["ask_personen"], parse_mode="Markdown")
    return PERSONEN

async def msg_personen(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    t = TXT[lang(ctx)]
    try:
        n = int(round(parse_zahl(update.message.text)))
        if n < 1:
            raise ValueError
        ctx.user_data["personen"] = n
    except Exception:
        await update.message.reply_text(t["err_zahl"].format(bsp="3"))
        return PERSONEN
    labels = TITEL_LABELS[lang(ctx)]
    kb = [
        [InlineKeyboardButton(labels[0], callback_data="titel_A")],
        [InlineKeyboardButton(labels[1], callback_data="titel_B")],
        [InlineKeyboardButton(labels[2], callback_data="titel_C")],
    ]
    await update.message.reply_text(t["ask_titel"], parse_mode="Markdown",
                                    reply_markup=InlineKeyboardMarkup(kb))
    return AUFENTHALTSTITEL

async def cb_titel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    t = TXT[lang(ctx)]
    ctx.user_data["titel_code"] = q.data.split("_")[1]   # A | B | C
    await q.edit_message_text(t["ask_ort"], parse_mode="Markdown")
    return SUCHORT

async def msg_ort(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    t = TXT[lang(ctx)]
    ort = update.message.text.strip()
    if not ort:
        await update.message.reply_text(t["err_text"])
        return SUCHORT
    ctx.user_data["ort"] = ort
    kb = [[
        InlineKeyboardButton(t["btn_ja"],   callback_data="consent_1"),
        InlineKeyboardButton(t["btn_nein"], callback_data="consent_0"),
    ]]
    await update.message.reply_text(t["ask_einwilligung"], parse_mode="Markdown",
                                    reply_markup=InlineKeyboardMarkup(kb))
    return EINWILLIGUNG

async def cb_einwilligung(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    t = TXT[lang(ctx)]
    consent = (q.data.split("_")[1] == "1")
    ctx.user_data["consent"] = consent

    if not consent:
        # Ohne Einwilligung: keine Speicherung (DSGVO)
        await q.edit_message_text(t["abgelehnt"], parse_mode="Markdown")
        return ConversationHandler.END

    d = ctx.user_data
    speichern(q.from_user, d)
    await admin_notify(ctx, q.from_user, d)

    await q.edit_message_text(zusammenfassung(t, d), parse_mode="Markdown")
    return ConversationHandler.END

# ── Zusammenfassung im vorgegebenen Format ────────────────
def zusammenfassung(t, d):
    code = d.get("sprache_code", "de")
    titel_idx = {"A": 0, "B": 1, "C": 2}.get(d.get("titel_code", ""), 0)
    titel_label = TITEL_LABELS[code][titel_idx]
    return (
        f"{t['summary_head']}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🗣️ {t['lbl_sprache']}: {d.get('sprache', '—')}\n"
        f"💼 {t['lbl_beschaeftigung']}: {d.get('beschaeftigung', '—')}\n"
        f"💰 {t['lbl_netto']}: {d.get('netto', '—')} €\n"
        f"📄 {t['lbl_schufa']}: {t['ja'] if d.get('schufa') else t['nein']}\n"
        f"👥 {t['lbl_personen']}: {d.get('personen', '—')}\n"
        f"🛂 {t['lbl_titel']}: {d.get('titel_code', '—')} ({titel_label})\n"
        f"🏙️ {t['lbl_ort']}: {d.get('ort', '—')}\n"
        f"🔒 {t['lbl_consent']}: {t['ja'] if d.get('consent') else t['nein']}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{t['outro']}"
    )

# ── Off-Topic / Fallbacks ─────────────────────────────────
async def offtopic(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    # Leitet bei themenfremden Nachrichten höflich zurück
    t = TXT[lang(ctx)]
    await update.message.reply_text(t["offtopic"])

async def cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    t = TXT[lang(ctx)]
    await update.message.reply_text(t["cancel"])
    return ConversationHandler.END

# ── Main ──────────────────────────────────────────────────
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SPRACHE:          [CallbackQueryHandler(cb_sprache, pattern="^lang_(de|fa)$")],
            BESCHAEFTIGUNG:   [MessageHandler(filters.TEXT & ~filters.COMMAND, msg_beschaeftigung)],
            NETTOEINKOMMEN:   [MessageHandler(filters.TEXT & ~filters.COMMAND, msg_netto)],
            SCHUFA:           [CallbackQueryHandler(cb_schufa, pattern="^schufa_[01]$")],
            PERSONEN:         [MessageHandler(filters.TEXT & ~filters.COMMAND, msg_personen)],
            AUFENTHALTSTITEL: [CallbackQueryHandler(cb_titel, pattern="^titel_[ABC]$")],
            SUCHORT:          [MessageHandler(filters.TEXT & ~filters.COMMAND, msg_ort)],
            EINWILLIGUNG:     [CallbackQueryHandler(cb_einwilligung, pattern="^consent_[01]$")],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CommandHandler("start", start),
            MessageHandler(filters.TEXT & ~filters.COMMAND, offtopic),
        ],
    )
    app.add_handler(conv)
    app.add_handler(CommandHandler("liste", cmd_liste))
    print("✅ MelkYab Mieter-Bot läuft — ربات ثبت درخواست مستأجر فعال است")
    app.run_polling()

if __name__ == "__main__":
    main()
