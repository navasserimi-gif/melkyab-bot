"""
MelkYab — ربات محاسبه وام مسکن
فقط به زبان فارسی
ذخیره کامل اطلاعات کاربران + گزارش کامل برای ادمین
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
BOT_TOKEN  = os.environ.get("BOT_TOKEN")  # از @BotFather بگیرید
ADMIN_ID   = int(os.environ.get("ADMIN_ID"))              # آیدی عددی تلگرام شما — از @userinfobot بگیرید
CSV_DATEI  = "melkyab_anfragen.csv"
# ══════════════════════════════════════════════════════════

# مراحل مکالمه
(PERSONEN, NETTOEINKOMMEN, BESCHAEFTIGUNG,
 SCHULDEN, SCHULDEN_BETRAG, EIGENKAPITAL, LAUFZEIT) = range(7)

JOB_FAKTOR = [1.0, 0.85, 0.75, 1.05]
LZ_JAHRE   = [10, 15, 20, 25, 30]
ZINS       = 0.04

# ── متن‌های فارسی ─────────────────────────────────────────
START_MSG = (
    "🏠 *به ربات محاسبه وام مسکن MelkYab خوش آمدید!*\n\n"
    "در چند مرحله ساده محاسبه می‌کنم:\n\n"
    "✅ حداکثر مبلغ وامی که می‌توانید بگیرید\n"
    "✅ حداکثر قیمت ملکی که می‌توانید بخرید\n"
    "✅ قسط ماهانه شما\n\n"
    "برای شروع دکمه زیر را بزنید 👇"
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

def f(n):
    return f"{int(n):,}".replace(",", ".")

def ergebnis_fa(r, d):
    schulden_zeile = f"💳 کسر اقساط بدهی موجود: `{f(r['schulden_abzug'])} €` در ماه\n" if r['schulden_abzug'] > 0 else ""
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

# ── ذخیره در CSV ─────────────────────────────────────────
def speichern(user, r, d):
    neu = not os.path.exists(CSV_DATEI)
    with open(CSV_DATEI, "a", newline="", encoding="utf-8-sig") as csvf:
        w = csv.writer(csvf)
        if neu:
            w.writerow([
                "تاریخ", "User ID", "یوزرنیم", "نام",
                "تعداد نفر", "درآمد خالص (€)", "وضعیت شغلی",
                "بدهی ماهانه (€)", "سرمایه اولیه (€)", "مدت (سال)",
                "وام ممکن (€)", "حداکثر قیمت ملک (€)", "قسط ماهانه (€)"
            ])
        job_labels = ["کارمند (دائمی)", "کارمند (موقت)", "خوداشتغال", "کارمند دولت"]
        w.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            user.id,
            f"@{user.username}" if user.username else "—",
            user.first_name or "—",
            r["personen"],
            d.get("netto", 0),
            job_labels[d.get("job", 0)],
            d.get("schulden", 0),
            d.get("eigenkapital", 0),
            r["jahre"],
            r["kredit"],
            r["kaufpreis"],
            r["monatsrate"],
        ])

# ── اطلاع‌رسانی به ادمین (فوری) ──────────────────────────
async def admin_notify(context, user, r, d):
    job_labels = ["کارمند (دائمی)", "کارمند (موقت)", "خوداشتغال", "کارمند دولت"]
    tg_link = f"tg://user?id={user.id}"
    msg = (
        f"📋 *درخواست جدید وام*\n\n"
        f"👤 نام: [{user.first_name or '—'}]({tg_link})\n"
        f"🔗 یوزرنیم: @{user.username or '—'}\n"
        f"🆔 آیدی: `{user.id}`\n\n"
        f"👥 تعداد نفر: {r['personen']}\n"
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
    if not os.path.exists(CSV_DATEI):
        await update.message.reply_text("هنوز هیچ درخواستی ثبت نشده.")
        return

    # خواندن CSV و ساختن خلاصه متنی
    with open(CSV_DATEI, "r", encoding="utf-8-sig") as csvf:
        rows = list(csv.reader(csvf))

    if len(rows) <= 1:
        await update.message.reply_text("هنوز هیچ درخواستی ثبت نشده.")
        return

    data_rows = rows[1:]  # بدون هدر
    total = len(data_rows)
    total_kredit = sum(float(r[10]) for r in data_rows if r[10])
    avg_kredit   = total_kredit / total if total else 0
    max_kredit   = max(float(r[10]) for r in data_rows if r[10])

    summary = (
        f"📊 *گزارش کامل MelkYab*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📅 تاریخ گزارش: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        f"👥 تعداد کل درخواست‌ها: *{total}*\n"
        f"💶 میانگین وام: *{f(avg_kredit)} €*\n"
        f"🏆 بیشترین وام: *{f(max_kredit)} €*\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"*لیست کاربران:*\n\n"
    )

    lines = []
    for i, r in enumerate(data_rows, 1):
        # r: تاریخ, ID, یوزر, نام, نفر, درآمد, شغل, بدهی, سرمایه, مدت, وام, قیمت, قسط
        tg_link = f"tg://user?id={r[1]}"
        lines.append(
            f"*{i}.* [{r[3]}]({tg_link}) | {r[2]}\n"
            f"   🆔 `{r[1]}` | 📅 {r[0]}\n"
            f"   💰 درآمد: `{r[5]} €` | 👥 {r[4]} نفر\n"
            f"   ✅ وام: `{f(float(r[10]))} €` | 🏠 ملک: `{f(float(r[11]))} €`\n"
        )

    # ارسال در چند پیام اگر لیست بزرگ باشد
    full_msg = summary + "\n".join(lines)
    if len(full_msg) <= 4000:
        await update.message.reply_text(full_msg, parse_mode="Markdown",
                                        disable_web_page_preview=True)
    else:
        await update.message.reply_text(summary, parse_mode="Markdown")
        # ارسال لیست در بخش‌های ۱۰تایی
        for i in range(0, len(lines), 10):
            chunk = "\n".join(lines[i:i+10])
            await update.message.reply_text(chunk, parse_mode="Markdown",
                                            disable_web_page_preview=True)

    # همیشه فایل CSV هم ارسال می‌شود
    await update.message.reply_document(
        document=open(CSV_DATEI, "rb"),
        filename=f"melkyab_{datetime.now().strftime('%Y%m%d')}.csv",
        caption="📎 فایل اکسل کامل همه درخواست‌ها"
    )

# ── Handlers ─────────────────────────────────────────────
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    kb = [[InlineKeyboardButton("▶️ شروع محاسبه", callback_data="pers_start")]]
    await update.message.reply_text(START_MSG, parse_mode="Markdown",
                                    reply_markup=InlineKeyboardMarkup(kb))
    return PERSONEN

async def cb_personen_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    kb = [[InlineKeyboardButton("👤 تنها (۱ نفر)", callback_data="pers_1")],
          [InlineKeyboardButton("👫 با شریک (۲ نفر)", callback_data="pers_2")]]
    await q.edit_message_text(
        "👥 *مرحله ۱ از ۶ — تعداد وام‌گیرندگان*\n\nوام را تنها می‌گیرید یا با شریک/همسر؟",
        parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
    return PERSONEN

async def cb_personen(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    ctx.user_data.clear()
    ctx.user_data["personen"] = int(q.data.split("_")[1])
    await q.edit_message_text(
        "💰 *مرحله ۲ از ۶ — درآمد خالص ماهانه*\n\n"
        "درآمد خالص ماهانه چقدر است؟ (یورو)\n\n"
        "_(اگر ۲ نفر هستید، جمع هر دو درآمد را بنویسید)_",
        parse_mode="Markdown")
    return NETTOEINKOMMEN

async def msg_netto(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        ctx.user_data["netto"] = float(update.message.text.replace(",",".").replace("€","").strip())
    except:
        await update.message.reply_text("⚠️ لطفاً یک عدد معتبر وارد کنید. مثال: 3500")
        return NETTOEINKOMMEN
    kb = [
        [InlineKeyboardButton("✅ کارمند — قرارداد دائمی", callback_data="job_0")],
        [InlineKeyboardButton("⚠️ کارمند — قرارداد موقت",  callback_data="job_1")],
        [InlineKeyboardButton("🔶 خوداشتغال / فریلنسر",   callback_data="job_2")],
        [InlineKeyboardButton("🏛️ کارمند دولت / Beamter", callback_data="job_3")],
    ]
    await update.message.reply_text(
        "💼 *مرحله ۳ از ۶ — وضعیت شغلی*\n\nکدام گزینه برای شما صدق می‌کند؟",
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
        "💳 *مرحله ۴ از ۶ — بدهی‌های موجود*\n\n"
        "آیا در حال حاضر قسط یا بدهی ماهانه دارید؟\n"
        "_(مثل: وام ماشین، قسط موبایل، نفقه، کارت اعتباری)_",
        parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
    return SCHULDEN

async def cb_schulden_nein(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    ctx.user_data["schulden"] = 0
    await q.edit_message_text(
        "🏦 *مرحله ۵ از ۶ — سرمایه اولیه*\n\n"
        "چقدر پس‌انداز دارید که می‌توانید وارد خرید کنید؟ (یورو)\n\n"
        "_(اگر ندارید، عدد ۰ بنویسید)_",
        parse_mode="Markdown")
    return EIGENKAPITAL

async def cb_schulden_ja(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    await q.edit_message_text(
        "💳 مجموع اقساط و بدهی‌های ماهانه شما چقدر است؟ (یورو)\n\n"
        "_(مثال: ۳۰۰ برای قسط ماشین)_",
        parse_mode="Markdown")
    return SCHULDEN_BETRAG

async def msg_schulden(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        ctx.user_data["schulden"] = float(update.message.text.replace(",",".").replace("€","").strip())
    except:
        await update.message.reply_text("⚠️ لطفاً یک عدد معتبر وارد کنید. مثال: 300")
        return SCHULDEN_BETRAG
    await update.message.reply_text(
        "🏦 *مرحله ۵ از ۶ — سرمایه اولیه*\n\n"
        "چقدر پس‌انداز دارید؟ (یورو)\n\n"
        "_(اگر ندارید، عدد ۰ بنویسید)_",
        parse_mode="Markdown")
    return EIGENKAPITAL

async def msg_eigenkapital(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        ctx.user_data["eigenkapital"] = float(update.message.text.replace(",",".").replace("€","").strip())
    except:
        await update.message.reply_text("⚠️ لطفاً یک عدد معتبر وارد کنید. مثال: 50000")
        return EIGENKAPITAL
    kb = [
        [InlineKeyboardButton("۱۰ سال", callback_data="lz_0"),
         InlineKeyboardButton("۱۵ سال", callback_data="lz_1")],
        [InlineKeyboardButton("۲۰ سال", callback_data="lz_2"),
         InlineKeyboardButton("۲۵ سال", callback_data="lz_3")],
        [InlineKeyboardButton("۳۰ سال", callback_data="lz_4")],
    ]
    await update.message.reply_text(
        "📅 *مرحله ۶ از ۶ — مدت بازپرداخت وام*\n\nچند سال می‌خواهید وام بازپرداخت کنید؟",
        parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
    return LAUFZEIT

async def cb_laufzeit(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    lz_idx = int(q.data.split("_")[1])
    d = ctx.user_data
    r = berechne(d["netto"], d["job"], d["schulden"], d["eigenkapital"], lz_idx, d["personen"])
    speichern(q.from_user, r, d)
    await admin_notify(ctx, q.from_user, r, d)

    kb = [
        [InlineKeyboardButton("🔄 محاسبه مجدد", callback_data="restart")],
        [InlineKeyboardButton("📞 درخواست مشاوره رایگان", url=f"tg://user?id={ADMIN_ID}")],
    ]
    await q.edit_message_text("⏳ در حال محاسبه...")
    await q.message.reply_text(
        ergebnis_fa(r, d), parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb),
        disable_web_page_preview=True)
    return ConversationHandler.END

async def cb_restart(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    ctx.user_data.clear()
    kb = [[InlineKeyboardButton("▶️ شروع محاسبه", callback_data="pers_start")]]
    await q.edit_message_text(START_MSG, parse_mode="Markdown",
                               reply_markup=InlineKeyboardMarkup(kb))
    return PERSONEN

async def cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ لغو شد. برای شروع مجدد /start بزنید.")
    return ConversationHandler.END

# ── Main ─────────────────────────────────────────────────
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            PERSONEN:       [
                CallbackQueryHandler(cb_personen_start, pattern="^pers_start$"),
                CallbackQueryHandler(cb_personen,       pattern="^pers_[12]$"),
            ],
            NETTOEINKOMMEN: [MessageHandler(filters.TEXT & ~filters.COMMAND, msg_netto)],
            BESCHAEFTIGUNG: [CallbackQueryHandler(cb_job,           pattern="^job_")],
            SCHULDEN:       [
                CallbackQueryHandler(cb_schulden_nein, pattern="^schuld_0$"),
                CallbackQueryHandler(cb_schulden_ja,   pattern="^schuld_1$"),
            ],
            SCHULDEN_BETRAG:[MessageHandler(filters.TEXT & ~filters.COMMAND, msg_schulden)],
            EIGENKAPITAL:   [MessageHandler(filters.TEXT & ~filters.COMMAND, msg_eigenkapital)],
            LAUFZEIT:       [CallbackQueryHandler(cb_laufzeit,      pattern="^lz_")],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CallbackQueryHandler(cb_restart, pattern="^restart$"),
        ],
    )
    app.add_handler(conv)
    app.add_handler(CommandHandler("liste", cmd_liste))
    print("✅ MelkYab Bot läuft — ربات فعال است")
    app.run_polling()

if __name__ == "__main__":
    main()
