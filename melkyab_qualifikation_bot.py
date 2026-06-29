"""
MelkYab — ربات کوالیفیکیشن + محاسبه وام مسکن
Immobilien-Kundenqualifizierung + Kreditrechner — Telegram-Bot
فقط به زبان فارسی با مشتری صحبت می‌کند

جریان کار:
  ۱) ۵ سؤال استاندارد کوالیفیکیشن → تولید «KUNDENPROFIL» برای مشاور
  ۲) سپس ادامه به محاسبه وام مسکن (مقادیر درآمد و سرمایه دوباره پرسیده نمی‌شوند)
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
BOT_TOKEN  = os.environ.get("BOT_TOKEN")          # از @BotFather بگیرید
ADMIN_ID   = int(os.environ.get("ADMIN_ID"))      # آیدی عددی تلگرام شما — از @userinfobot
CSV_PROFIL = "melkyab_kundenprofile.csv"          # داده‌های کوالیفیکیشن
CSV_KREDIT = "melkyab_anfragen.csv"               # نتایج محاسبه وام
# ══════════════════════════════════════════════════════════

# مراحل مکالمه
# بخش کوالیفیکیشن:
(EIGENKAPITAL, NETTOEINKOMMEN, SCHUFA, REGION, HAUSHALT,
# پل بین دو بخش:
 PROFIL_FERTIG,
# بخش محاسبه وام:
 PERSONEN, BESCHAEFTIGUNG, SCHULDEN, SCHULDEN_BETRAG, LAUFZEIT) = range(11)

# پارامترهای محاسبه وام
JOB_FAKTOR = [1.0, 0.85, 0.75, 1.05]
LZ_JAHRE   = [10, 15, 20, 25, 30]
ZINS       = 0.04
JOB_LABELS = ["کارمند (دائمی)", "کارمند (موقت)", "خوداشتغال", "کارمند دولت"]

# ── متن‌های ثابت ─────────────────────────────────────────
OFFTOPIC_FA = (
    "ببخشید، در حال حاضر تمرکز من روی ثبت اطلاعات شماست. "
    "بیایید سؤال‌ها را ادامه دهیم. 🙏"
)

START_MSG = (
    "🏠 *به دستیار دفتر املاک خوش آمدید!*\n\n"
    "من دستیار دیجیتال دفتر مشاور املاک شما هستم. "
    "برای اینکه مشاور بتواند بهترین آپارتمان را برای شما پیدا کند، "
    "چند سؤال کوتاه درباره وضعیت مالی و نیاز سکونتی شما می‌پرسم.\n\n"
    "همه چیز محرمانه و فقط برای پیدا کردن خانه مناسب شماست. "
    "برای شروع دکمه زیر را بزنید 👇"
)


# ── کمک‌تابع: تبدیل عدد ──────────────────────────────────
def parse_zahl(text):
    """رشته ورودی را به عدد تبدیل می‌کند؛ در صورت نامعتبر None برمی‌گرداند."""
    bereinigt = (
        text.replace("€", "")
            .replace("یورو", "")
            .replace("تومان", "")
            .replace(" ", "")
            .replace(".", "")   # جداکننده هزارگان آلمانی
            .replace(",", ".")  # جداکننده اعشاری
            .strip()
    )
    try:
        wert = float(bereinigt)
        if wert < 0:
            return None
        return wert
    except ValueError:
        return None


def f(n):
    return f"{int(n):,}".replace(",", ".")


# ── تولید KUNDENPROFIL ───────────────────────────────────
def kundenprofil_text(d):
    schufa = "JA" if d["schufa"] else "NEIN"
    return (
        "```\n"
        "=== KUNDENPROFIL ===\n"
        f"Eigenkapital: {f(d['eigenkapital'])} €\n"
        f"Nettoeinkommen/Monat: {f(d['netto'])} €\n"
        f"SCHUFA vorhanden: {schufa}\n"
        f"Suchregion: {d['region']}\n"
        f"Haushaltsgröße: {d['haushalt']} Personen\n"
        f"Erfassungsdatum: {datetime.now().strftime('%Y-%m-%d')}\n"
        "===\n"
        "```"
    )


# ── محاسبه وام ───────────────────────────────────────────
def berechne(netto, job, schulden, ek, lz_idx, personen):
    jahre  = LZ_JAHRE[lz_idx]
    monate = jahre * 12
    mzins  = ZINS / 12
    faktor = JOB_FAKTOR[job]

    brutto_rate = netto * 0.35 * faktor
    netto_rate  = max(0, brutto_rate - schulden)
    kredit = netto_rate * ((1 - (1 + mzins) ** -monate) / mzins)
    kredit = round(kredit / 1000) * 1000

    kaufpreis     = round((kredit + ek) / 1000) * 1000
    ek_pct        = round(ek / kaufpreis * 100, 1) if kaufpreis > 0 else 0
    empfehlung_ek = round(kaufpreis * 0.20 / 1000) * 1000
    ek_diff       = max(0, empfehlung_ek - ek)

    return dict(
        kredit=kredit, kaufpreis=kaufpreis,
        monatsrate=round(netto_rate),
        ek_pct=ek_pct, empfehlung_ek=empfehlung_ek,
        ek_diff=ek_diff, jahre=jahre,
        schulden_abzug=round(schulden),
        personen=personen,
    )


def ergebnis_fa(r, d):
    schulden_zeile = (
        f"💳 کسر اقساط بدهی موجود: `{f(r['schulden_abzug'])} €` در ماه\n"
        if r['schulden_abzug'] > 0 else ""
    )
    warn = (
        f"⚠️ توصیه می‌شود حداقل *{f(r['empfehlung_ek'])} €* سرمایه اولیه داشته باشید\n"
        f"   (هنوز `{f(r['ek_diff'])} €` تا رسیدن به این هدف)\n\n"
        if r['ek_diff'] > 0 else "✅ سرمایه اولیه شما کافی است!\n\n"
    )
    return (
        f"✅ *نتیجه محاسبه وام شما*\n\n"
        f"👥 تعداد وام‌گیرندگان: `{r['personen']} نفر`\n"
        f"💰 درآمد خالص: `{f(d['netto'])} €` در ماه\n"
        f"{schulden_zeile}"
        f"🏦 سرمایه اولیه: `{f(d['eigenkapital'])} €`\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🏦 *حداکثر وام: {f(r['kredit'])} €*\n"
        f"🏠 *حداکثر قیمت ملک: {f(r['kaufpreis'])} €*\n"
        f"💳 *قسط ماهانه: {f(r['monatsrate'])} €*\n"
        f"📊 سهم سرمایه اولیه: `{r['ek_pct']}%`\n"
        f"📅 مدت بازپرداخت: `{r['jahre']} سال` با نرخ بهره `{ZINS*100:.0f}%`\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"{warn}"
        f"📞 *برای مشاوره رایگان و شخصی همین الان با ما تماس بگیرید!*\n"
        f"👇 دکمه زیر را بزنید"
    )


# ── ذخیره KUNDENPROFIL در CSV ────────────────────────────
def speichern_profil(user, d):
    neu = not os.path.exists(CSV_PROFIL)
    with open(CSV_PROFIL, "a", newline="", encoding="utf-8-sig") as csvf:
        w = csv.writer(csvf)
        if neu:
            w.writerow([
                "Erfassungsdatum", "User ID", "Username", "Name",
                "Eigenkapital (€)", "Nettoeinkommen/Monat (€)",
                "SCHUFA vorhanden", "Suchregion", "Haushaltsgröße",
            ])
        w.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            user.id,
            f"@{user.username}" if user.username else "—",
            user.first_name or "—",
            int(d["eigenkapital"]),
            int(d["netto"]),
            "JA" if d["schufa"] else "NEIN",
            d["region"],
            d["haushalt"],
        ])


# ── ذخیره نتیجه وام در CSV ───────────────────────────────
def speichern_kredit(user, r, d):
    neu = not os.path.exists(CSV_KREDIT)
    with open(CSV_KREDIT, "a", newline="", encoding="utf-8-sig") as csvf:
        w = csv.writer(csvf)
        if neu:
            w.writerow([
                "تاریخ", "User ID", "یوزرنیم", "نام",
                "تعداد نفر", "درآمد خالص (€)", "وضعیت شغلی",
                "بدهی ماهانه (€)", "سرمایه اولیه (€)", "مدت (سال)",
                "وام ممکن (€)", "حداکثر قیمت ملک (€)", "قسط ماهانه (€)"
            ])
        w.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            user.id,
            f"@{user.username}" if user.username else "—",
            user.first_name or "—",
            r["personen"],
            int(d.get("netto", 0)),
            JOB_LABELS[d.get("job", 0)],
            int(d.get("schulden", 0)),
            int(d.get("eigenkapital", 0)),
            r["jahre"],
            r["kredit"],
            r["kaufpreis"],
            r["monatsrate"],
        ])


# ── اطلاع‌رسانی KUNDENPROFIL به ادمین ────────────────────
async def admin_notify_profil(context, user, d):
    tg_link = f"tg://user?id={user.id}"
    schufa = "✅ بله" if d["schufa"] else "❌ خیر"
    msg = (
        "📋 *پروفایل جدید مشتری (Kundenprofil)*\n\n"
        f"👤 نام: [{user.first_name or '—'}]({tg_link})\n"
        f"🔗 یوزرنیم: @{user.username or '—'}\n"
        f"🆔 آیدی: `{user.id}`\n\n"
        f"🏦 سرمایه اولیه (Eigenkapital): `{f(d['eigenkapital'])} €`\n"
        f"💰 درآمد خالص ماهانه: `{f(d['netto'])} €`\n"
        f"📄 شوفا (SCHUFA): {schufa}\n"
        f"📍 منطقه جستجو: `{d['region']}`\n"
        f"👥 تعداد ساکنین: `{d['haushalt']} نفر`\n"
        f"📅 تاریخ ثبت: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )
    await context.bot.send_message(ADMIN_ID, msg,
                                   parse_mode="Markdown",
                                   disable_web_page_preview=True)


# ── اطلاع‌رسانی نتیجه وام به ادمین ───────────────────────
async def admin_notify_kredit(context, user, r, d):
    tg_link = f"tg://user?id={user.id}"
    msg = (
        f"💶 *محاسبه وام تکمیل شد*\n\n"
        f"👤 نام: [{user.first_name or '—'}]({tg_link})\n"
        f"🆔 آیدی: `{user.id}`\n\n"
        f"👥 تعداد وام‌گیرنده: {r['personen']}\n"
        f"💰 درآمد: `{f(d.get('netto',0))} €/ماه`\n"
        f"💳 بدهی: `{f(d.get('schulden',0))} €/ماه`\n"
        f"🏦 سرمایه: `{f(d.get('eigenkapital',0))} €`\n\n"
        f"✅ *وام ممکن: {f(r['kredit'])} €*\n"
        f"🏠 *قیمت ملک: {f(r['kaufpreis'])} €*\n"
        f"💳 قسط: `{f(r['monatsrate'])} €/ماه`\n"
        f"📅 مدت: {r['jahre']} سال"
    )
    await context.bot.send_message(ADMIN_ID, msg,
                                   parse_mode="Markdown",
                                   disable_web_page_preview=True)


# ── گزارش کامل برای ادمین (/liste) ──────────────────────
async def cmd_liste(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not os.path.exists(CSV_PROFIL):
        await update.message.reply_text("هنوز هیچ پروفایلی ثبت نشده.")
        return

    with open(CSV_PROFIL, "r", encoding="utf-8-sig") as csvf:
        rows = list(csv.reader(csvf))

    if len(rows) <= 1:
        await update.message.reply_text("هنوز هیچ پروفایلی ثبت نشده.")
        return

    data_rows = rows[1:]
    total = len(data_rows)

    summary = (
        "📊 *گزارش پروفایل‌های مشتری MelkYab*\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"📅 تاریخ گزارش: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        f"👥 تعداد کل پروفایل‌ها: *{total}*\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "*لیست مشتریان:*\n\n"
    )

    lines = []
    for i, r in enumerate(data_rows, 1):
        # r: تاریخ, ID, یوزر, نام, سرمایه, درآمد, شوفا, منطقه, تعداد نفر
        tg_link = f"tg://user?id={r[1]}"
        lines.append(
            f"*{i}.* [{r[3]}]({tg_link}) | {r[2]}\n"
            f"   🆔 `{r[1]}` | 📅 {r[0]}\n"
            f"   🏦 سرمایه: `{r[4]} €` | 💰 درآمد: `{r[5]} €`\n"
            f"   📄 شوفا: {r[6]} | 📍 {r[7]} | 👥 {r[8]} نفر\n"
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
        document=open(CSV_PROFIL, "rb"),
        filename=f"melkyab_kundenprofile_{datetime.now().strftime('%Y%m%d')}.csv",
        caption="📎 فایل اکسل کامل همه پروفایل‌ها"
    )
    if os.path.exists(CSV_KREDIT):
        await update.message.reply_document(
            document=open(CSV_KREDIT, "rb"),
            filename=f"melkyab_kredit_{datetime.now().strftime('%Y%m%d')}.csv",
            caption="📎 فایل اکسل محاسبات وام"
        )


# ══════════════════════════════════════════════════════════
#  بخش ۱ — کوالیفیکیشن
# ══════════════════════════════════════════════════════════
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    kb = [[InlineKeyboardButton("▶️ شروع", callback_data="qual_start")]]
    await update.message.reply_text(START_MSG, parse_mode="Markdown",
                                    reply_markup=InlineKeyboardMarkup(kb))
    return EIGENKAPITAL


# سؤال ۱ — Eigenkapital
async def cb_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    ctx.user_data.clear()
    await q.edit_message_text(
        "🏦 *سؤال ۱ از ۵ — سرمایه اولیه (Eigenkapital)*\n\n"
        "چه میزان سرمایه نقدی در دسترس دارید؟ (به یورو)\n\n"
        "_(اگر سرمایه‌ای ندارید، عدد ۰ بنویسید)_",
        parse_mode="Markdown")
    return EIGENKAPITAL


async def msg_eigenkapital(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    wert = parse_zahl(update.message.text)
    if wert is None:
        await update.message.reply_text(
            "⚠️ لطفاً یک عدد معتبر وارد کنید. مثال: 50000")
        return EIGENKAPITAL
    ctx.user_data["eigenkapital"] = wert
    await update.message.reply_text(
        f"✅ سرمایه اولیه ثبت شد: *{f(wert)} €*\n\n"
        "💰 *سؤال ۲ از ۵ — درآمد خالص ماهانه*\n\n"
        "درآمد خالص ماهانه شما چقدر است؟ (به یورو)",
        parse_mode="Markdown")
    return NETTOEINKOMMEN


# سؤال ۲ — Nettoeinkommen
async def msg_netto(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    wert = parse_zahl(update.message.text)
    if wert is None:
        await update.message.reply_text(
            "⚠️ لطفاً یک عدد معتبر وارد کنید. مثال: 3500")
        return NETTOEINKOMMEN
    ctx.user_data["netto"] = wert
    kb = [
        [InlineKeyboardButton("✅ بله", callback_data="schufa_ja"),
         InlineKeyboardButton("❌ خیر", callback_data="schufa_nein")],
    ]
    await update.message.reply_text(
        f"✅ درآمد خالص ثبت شد: *{f(wert)} €*\n\n"
        "📄 *سؤال ۳ از ۵ — گزارش شوفا (SCHUFA)*\n\n"
        "آیا گزارش شوفا (SCHUFA-Auskunft) دارید؟",
        parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
    return SCHUFA


# سؤال ۳ — SCHUFA
async def cb_schufa(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    ctx.user_data["schufa"] = (q.data == "schufa_ja")
    antwort = "بله ✅" if ctx.user_data["schufa"] else "خیر ❌"
    await q.edit_message_text(
        f"✅ شوفا ثبت شد: *{antwort}*\n\n"
        "📍 *سؤال ۴ از ۵ — منطقه جستجو*\n\n"
        "در کدام شهر یا منطقه در آلمان دنبال آپارتمان هستید؟\n"
        "_(مثال: کلن، دوسلدورف، سراسر آلمان)_",
        parse_mode="Markdown")
    return REGION


async def msg_schufa_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """اگر کاربر به جای دکمه، متن بله/خیر بنویسد."""
    txt = update.message.text.strip().lower()
    ja_worte = {"بله", "آره", "دارم", "ja", "yes", "y", "بلی", "بله دارم"}
    nein_worte = {"خیر", "نه", "ندارم", "نخیر", "nein", "no", "n"}
    if any(w in txt for w in ja_worte):
        ctx.user_data["schufa"] = True
    elif any(w in txt for w in nein_worte):
        ctx.user_data["schufa"] = False
    else:
        await update.message.reply_text(
            "لطفاً مشخص کنید: آیا گزارش شوفا دارید؟ «بله» یا «خیر»؟")
        return SCHUFA
    antwort = "بله ✅" if ctx.user_data["schufa"] else "خیر ❌"
    await update.message.reply_text(
        f"✅ شوفا ثبت شد: *{antwort}*\n\n"
        "📍 *سؤال ۴ از ۵ — منطقه جستجو*\n\n"
        "در کدام شهر یا منطقه در آلمان دنبال آپارتمان هستید؟\n"
        "_(مثال: کلن، دوسلدورف، سراسر آلمان)_",
        parse_mode="Markdown")
    return REGION


# سؤال ۴ — Suchregion
async def msg_region(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    region = update.message.text.strip()
    if len(region) < 2:
        await update.message.reply_text(
            "می‌شود دقیق‌تر بفرمایید؟ نام شهر یا منطقه را بنویسید.")
        return REGION
    ctx.user_data["region"] = region
    await update.message.reply_text(
        f"✅ منطقه جستجو ثبت شد: *{region}*\n\n"
        "👥 *سؤال ۵ از ۵ — تعداد ساکنین*\n\n"
        "چند نفر در این آپارتمان زندگی خواهند کرد؟",
        parse_mode="Markdown")
    return HAUSHALT


# سؤال ۵ — Haushaltsgröße → نمایش KUNDENPROFIL + پیشنهاد محاسبه وام
async def msg_haushalt(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    wert = parse_zahl(update.message.text)
    if wert is None or wert < 1:
        await update.message.reply_text(
            "⚠️ لطفاً تعداد افراد را به صورت یک عدد معتبر وارد کنید. مثال: 3")
        return HAUSHALT
    d = ctx.user_data
    d["haushalt"] = int(wert)

    speichern_profil(update.effective_user, d)
    await admin_notify_profil(ctx, update.effective_user, d)

    await update.message.reply_text(kundenprofil_text(d), parse_mode="Markdown")

    kb = [
        [InlineKeyboardButton("🏦 محاسبه وام مسکن", callback_data="calc_start")],
        [InlineKeyboardButton("🔄 ثبت پروفایل جدید", callback_data="restart")],
        [InlineKeyboardButton("📞 تماس با مشاور", url=f"tg://user?id={ADMIN_ID}")],
    ]
    await update.message.reply_text(
        "🙏 از همکاری شما سپاسگزاریم!\n\n"
        "اطلاعات شما با موفقیت ثبت شد و مشاور املاک ما از آن برای جستجوی "
        "آپارتمان مناسب شما استفاده خواهد کرد.\n\n"
        "💡 اگر مایلید، می‌توانم همین حالا *حداکثر وام مسکن* شما را هم محاسبه کنم.",
        parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
    return PROFIL_FERTIG


# ══════════════════════════════════════════════════════════
#  بخش ۲ — محاسبه وام مسکن (مقادیر درآمد/سرمایه از قبل موجود است)
# ══════════════════════════════════════════════════════════
async def cb_calc_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    kb = [[InlineKeyboardButton("👤 تنها (۱ نفر)", callback_data="pers_1")],
          [InlineKeyboardButton("👫 با شریک (۲ نفر)", callback_data="pers_2")]]
    await q.edit_message_text(
        "👥 *محاسبه وام — مرحله ۱ از ۴ — تعداد وام‌گیرندگان*\n\n"
        "وام را تنها می‌گیرید یا با شریک/همسر؟",
        parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
    return PERSONEN


async def cb_personen(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    ctx.user_data["personen"] = int(q.data.split("_")[1])
    kb = [
        [InlineKeyboardButton("✅ کارمند — قرارداد دائمی", callback_data="job_0")],
        [InlineKeyboardButton("⚠️ کارمند — قرارداد موقت",  callback_data="job_1")],
        [InlineKeyboardButton("🔶 خوداشتغال / فریلنسر",   callback_data="job_2")],
        [InlineKeyboardButton("🏛️ کارمند دولت / Beamter", callback_data="job_3")],
    ]
    await q.edit_message_text(
        "💼 *محاسبه وام — مرحله ۲ از ۴ — وضعیت شغلی*\n\nکدام گزینه برای شما صدق می‌کند؟",
        parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
    return BESCHAEFTIGUNG


async def cb_job(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    ctx.user_data["job"] = int(q.data.split("_")[1])
    kb = [
        [InlineKeyboardButton("✅ نه، بدهی یا قسط ماهانه ندارم", callback_data="schuld_0")],
        [InlineKeyboardButton("⚠️ بله، قسط/بدهی ماهانه دارم",   callback_data="schuld_1")],
    ]
    await q.edit_message_text(
        "💳 *محاسبه وام — مرحله ۳ از ۴ — بدهی‌های موجود*\n\n"
        "آیا در حال حاضر قسط یا بدهی ماهانه دارید؟\n"
        "_(مثل: وام ماشین، قسط موبایل، نفقه، کارت اعتباری)_",
        parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
    return SCHULDEN


async def cb_schulden_nein(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    ctx.user_data["schulden"] = 0
    return await frage_laufzeit_cb(q)


async def cb_schulden_ja(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    await q.edit_message_text(
        "💳 مجموع اقساط و بدهی‌های ماهانه شما چقدر است؟ (یورو)\n\n"
        "_(مثال: ۳۰۰ برای قسط ماشین)_",
        parse_mode="Markdown")
    return SCHULDEN_BETRAG


async def msg_schulden(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    wert = parse_zahl(update.message.text)
    if wert is None:
        await update.message.reply_text(
            "⚠️ لطفاً یک عدد معتبر وارد کنید. مثال: 300")
        return SCHULDEN_BETRAG
    ctx.user_data["schulden"] = wert
    return await frage_laufzeit_msg(update)


def _laufzeit_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("۱۰ سال", callback_data="lz_0"),
         InlineKeyboardButton("۱۵ سال", callback_data="lz_1")],
        [InlineKeyboardButton("۲۰ سال", callback_data="lz_2"),
         InlineKeyboardButton("۲۵ سال", callback_data="lz_3")],
        [InlineKeyboardButton("۳۰ سال", callback_data="lz_4")],
    ])


async def frage_laufzeit_cb(q):
    await q.edit_message_text(
        "📅 *محاسبه وام — مرحله ۴ از ۴ — مدت بازپرداخت*\n\n"
        "چند سال می‌خواهید وام را بازپرداخت کنید؟",
        parse_mode="Markdown", reply_markup=_laufzeit_kb())
    return LAUFZEIT


async def frage_laufzeit_msg(update):
    await update.message.reply_text(
        "📅 *محاسبه وام — مرحله ۴ از ۴ — مدت بازپرداخت*\n\n"
        "چند سال می‌خواهید وام را بازپرداخت کنید؟",
        parse_mode="Markdown", reply_markup=_laufzeit_kb())
    return LAUFZEIT


async def cb_laufzeit(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    lz_idx = int(q.data.split("_")[1])
    d = ctx.user_data
    r = berechne(d["netto"], d["job"], d["schulden"],
                 d["eigenkapital"], lz_idx, d["personen"])
    speichern_kredit(q.from_user, r, d)
    await admin_notify_kredit(ctx, q.from_user, r, d)

    kb = [
        [InlineKeyboardButton("🔄 شروع مجدد", callback_data="restart")],
        [InlineKeyboardButton("📞 درخواست مشاوره رایگان", url=f"tg://user?id={ADMIN_ID}")],
    ]
    await q.edit_message_text("⏳ در حال محاسبه...")
    await q.message.reply_text(
        ergebnis_fa(r, d), parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb),
        disable_web_page_preview=True)
    return ConversationHandler.END


# ── کنترل‌های عمومی ──────────────────────────────────────
async def cb_restart(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    ctx.user_data.clear()
    kb = [[InlineKeyboardButton("▶️ شروع", callback_data="qual_start")]]
    await q.edit_message_text(START_MSG, parse_mode="Markdown",
                              reply_markup=InlineKeyboardMarkup(kb))
    return EIGENKAPITAL


async def cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ لغو شد. برای شروع مجدد /start بزنید.")
    return ConversationHandler.END


# ── Main ─────────────────────────────────────────────────
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            # بخش کوالیفیکیشن
            EIGENKAPITAL: [
                CallbackQueryHandler(cb_start, pattern="^qual_start$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, msg_eigenkapital),
            ],
            NETTOEINKOMMEN: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, msg_netto),
            ],
            SCHUFA: [
                CallbackQueryHandler(cb_schufa, pattern="^schufa_(ja|nein)$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, msg_schufa_text),
            ],
            REGION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, msg_region),
            ],
            HAUSHALT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, msg_haushalt),
            ],
            # پل
            PROFIL_FERTIG: [
                CallbackQueryHandler(cb_calc_start, pattern="^calc_start$"),
                CallbackQueryHandler(cb_restart, pattern="^restart$"),
            ],
            # بخش محاسبه وام
            PERSONEN: [
                CallbackQueryHandler(cb_personen, pattern="^pers_[12]$"),
            ],
            BESCHAEFTIGUNG: [
                CallbackQueryHandler(cb_job, pattern="^job_"),
            ],
            SCHULDEN: [
                CallbackQueryHandler(cb_schulden_nein, pattern="^schuld_0$"),
                CallbackQueryHandler(cb_schulden_ja,   pattern="^schuld_1$"),
            ],
            SCHULDEN_BETRAG: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, msg_schulden),
            ],
            LAUFZEIT: [
                CallbackQueryHandler(cb_laufzeit, pattern="^lz_"),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CallbackQueryHandler(cb_restart, pattern="^restart$"),
        ],
    )
    app.add_handler(conv)
    app.add_handler(CommandHandler("liste", cmd_liste))
    print("✅ MelkYab Bot läuft — کوالیفیکیشن + محاسبه وام فعال است")
    app.run_polling()


if __name__ == "__main__":
    main()
