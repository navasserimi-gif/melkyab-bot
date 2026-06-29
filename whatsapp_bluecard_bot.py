"""
WhatsApp Business Bot — Maya Investment GmbH
Blue-Card- / Visa-Personalvermittlung

KI-Assistent auf Basis von Claude (Anthropic).
- Kommuniziert mit Kunden auf Arabisch (alle Dialekte) und Farsi.
- Erkennt aus den ersten Nachrichten Land/Dialekt und antwortet im selben Dialekt.
- Formell, höflich, wie ein persönlicher Assistent.
- Speichert alle Gespräche und erstellt für den Admin eine Liste.
- Der Admin kann jederzeit manuell eingreifen ("übernehmen") und selbst schreiben.

Technik: WhatsApp Cloud API (Meta) + Flask Webhook + Claude.
"""

import os
import json
import sqlite3
import logging
import threading
from datetime import datetime

import requests
from flask import Flask, request, Response
import anthropic

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("bluecard-bot")

# ══════════════════════════════════════════════════════════════════
#  KONFIGURATION  — alle Werte als Umgebungsvariablen setzen
# ══════════════════════════════════════════════════════════════════
ANTHROPIC_API_KEY   = os.environ.get("ANTHROPIC_API_KEY")            # Anthropic API-Schlüssel
WHATSAPP_TOKEN      = os.environ.get("WHATSAPP_TOKEN")              # Meta WhatsApp Access-Token
WHATSAPP_PHONE_ID   = os.environ.get("WHATSAPP_PHONE_NUMBER_ID")    # Phone Number ID aus dem Meta-Dashboard
VERIFY_TOKEN        = os.environ.get("WHATSAPP_VERIFY_TOKEN", "maya-investment-verify")
ADMIN_WHATSAPP      = os.environ.get("ADMIN_WHATSAPP", "")          # Ihre eigene Nummer, z.B. 4915112345678
GRAPH_VERSION       = os.environ.get("WHATSAPP_GRAPH_VERSION", "v21.0")
MODEL               = os.environ.get("CLAUDE_MODEL", "claude-opus-4-8")
DB_PATH             = os.environ.get("DB_PATH", "bluecard.db")

GRAPH_URL = f"https://graph.facebook.com/{GRAPH_VERSION}/{WHATSAPP_PHONE_ID}/messages"

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None

# ══════════════════════════════════════════════════════════════════
#  SYSTEM-PROMPT  — das "Gehirn" und Wissen des Assistenten
# ══════════════════════════════════════════════════════════════════
SYSTEM_PROMPT = """\
أنت المساعد الرسمي لشركة «Maya Investment GmbH» في ألمانيا (شركة وساطة توظيف
ومتخصصة في إجراءات تأشيرة البطاقة الزرقاء «Blue Card / Blaue Karte EU»).
تتحدث نيابة عن الشركة مع عملاء من الدول العربية وإيران.

=== الأسلوب ===
- كن دائماً رسمياً ومهذباً ومحترماً، كأنك مساعد شخصي محترف.
- العميل كتب إليك بلهجته. اكتشف من رسائله الأولى من أي بلد هو (مثلاً سوريا،
  العراق، مصر، المغرب، الجزائر، تونس، السعودية، لبنان، الأردن، الخليج…)
  وأجِبه بنفس لهجته بالضبط بشكل طبيعي ومريح.
- إذا كتب العميل بالفارسية، أجِبه بالفارسية المهذبة.
- حافظ على نفس اللهجة طوال المحادثة. لا تخلط اللهجات.
- اكتب رسائل قصيرة وواضحة ومناسبة للواتساب (لا فقرات طويلة جداً).

=== الخدمة التي نقدّمها ===
نحن نساعد العائلات على القدوم إلى ألمانيا والعمل هنا بشكل قانوني:
1. نؤمّن للعميل عقد عمل وتوظيفاً في ألمانيا.
2. محامونا في ألمانيا يتولون كامل الأعمال الورقية وإجراءات التأشيرة (visa /
   Visumverfahren) من داخل ألمانيا.
3. يأتي العميل وعائلته إلى ألمانيا بالتأشيرة.
4. يمكن للعميل أن يبدأ إمّا كموظف (أجير) أو كصاحب عمل حر (Selbstständigkeit) —
   نحن نساعد في كلا الطريقين.
5. نحن نضمن الحصول على التأشيرة.

=== شروط مهمة يجب توضيحها بصدق ===
- السعر الكامل للخدمة بالكامل لكل عائلة: 50,000 يورو (خمسون ألف يورو).
- يمكن تحويل المبلغ من أي مكان في العالم إلى شركتنا: «Maya Investment GmbH».
- نحن نؤمّن التوظيف/التشغيل لأول 3 أشهر فقط. بعد ذلك على العميل إمّا أن يؤمّن
  استمرار عمله بنفسه، أو نساعده على أن يصبح صاحب عمل حر (مستقل) في ألمانيا.

=== مهمتك ===
أنت تقوم بكل الأعمال التمهيدية والتحضيرية:
- رحّب بالعميل بأدب وعرّفه باختصار على الخدمة.
- اجمع منه بلطف المعلومات الأساسية: الاسم الكامل، بلد الإقامة، عدد أفراد العائلة،
  المهنة / المؤهلات / الخبرة، مستوى اللغة (ألمانية / إنجليزية)، والهدف من القدوم.
- أجِب على أسئلته حول الإجراءات والتكاليف والوقت بصدق ووضوح.
- لا تَعِد بأي شيء خارج ما هو مذكور أعلاه. إن لم تكن متأكداً من تفصيل قانوني دقيق
  قل إنك ستتأكد مع المحامين وتعود إليه، أو أن أحد موظفينا سيتواصل معه.
- عندما يكون العميل جاداً وجاهزاً للخطوة التالية (الدفع أو توقيع العقد)، أخبره
  بأدب أن أحد المسؤولين من الشركة سيتواصل معه شخصياً لإتمام الإجراءات.

=== قواعد ===
- لا تخترع معلومات قانونية غير صحيحة. ألمانيا لديها قوانين هجرة دقيقة؛ التزم بما هو
  مذكور أعلاه فقط، وأحِل التفاصيل القانونية الدقيقة إلى المحامين/الموظفين.
- لا تذكر أبداً أنك ذكاء اصطناعي أو روبوت. أنت «مساعد شركة Maya Investment».
- كن متعاطفاً ومطمئِناً؛ كثير من العملاء قلقون بشأن مستقبلهم وعائلاتهم.
"""

# ══════════════════════════════════════════════════════════════════
#  DATENBANK
# ══════════════════════════════════════════════════════════════════
_db_lock = threading.Lock()


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS customers (
                wa_id       TEXT PRIMARY KEY,
                name        TEXT,
                first_seen  TEXT,
                last_seen   TEXT,
                manual_mode INTEGER DEFAULT 0,
                msg_count   INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS messages (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                wa_id     TEXT,
                role      TEXT,          -- 'user' | 'assistant' | 'admin'
                text      TEXT,
                ts        TEXT
            );
            CREATE TABLE IF NOT EXISTS processed (
                msg_id TEXT PRIMARY KEY
            );
            """
        )
    log.info("Datenbank bereit: %s", DB_PATH)


def already_processed(msg_id: str) -> bool:
    """Verhindert doppelte Verarbeitung (Meta sendet Webhooks ggf. mehrfach)."""
    with _db_lock, db() as conn:
        try:
            conn.execute("INSERT INTO processed (msg_id) VALUES (?)", (msg_id,))
            return False
        except sqlite3.IntegrityError:
            return True


def upsert_customer(wa_id: str, name: str = None):
    now = datetime.now().isoformat(timespec="seconds")
    with _db_lock, db() as conn:
        row = conn.execute("SELECT wa_id FROM customers WHERE wa_id=?", (wa_id,)).fetchone()
        if row:
            conn.execute(
                "UPDATE customers SET last_seen=?, msg_count=msg_count+1, "
                "name=COALESCE(NULLIF(?,''), name) WHERE wa_id=?",
                (now, name or "", wa_id),
            )
            return False  # nicht neu
        conn.execute(
            "INSERT INTO customers (wa_id, name, first_seen, last_seen, msg_count) "
            "VALUES (?,?,?,?,1)",
            (wa_id, name or "", now, now),
        )
        return True  # neuer Kunde


def save_message(wa_id: str, role: str, text: str):
    now = datetime.now().isoformat(timespec="seconds")
    with _db_lock, db() as conn:
        conn.execute(
            "INSERT INTO messages (wa_id, role, text, ts) VALUES (?,?,?,?)",
            (wa_id, role, text, now),
        )


def get_history(wa_id: str, limit: int = 40):
    """Verlauf für Claude. 'admin' und 'assistant' zählen beide als Firmenseite."""
    with db() as conn:
        rows = conn.execute(
            "SELECT role, text FROM messages WHERE wa_id=? ORDER BY id DESC LIMIT ?",
            (wa_id, limit),
        ).fetchall()
    rows = list(reversed(rows))
    history = []
    for r in rows:
        role = "user" if r["role"] == "user" else "assistant"
        history.append({"role": role, "content": r["text"]})
    return history


def is_manual(wa_id: str) -> bool:
    with db() as conn:
        row = conn.execute("SELECT manual_mode FROM customers WHERE wa_id=?", (wa_id,)).fetchone()
    return bool(row and row["manual_mode"])


def set_manual(wa_id: str, value: bool):
    with _db_lock, db() as conn:
        conn.execute("UPDATE customers SET manual_mode=? WHERE wa_id=?", (1 if value else 0, wa_id))


# ══════════════════════════════════════════════════════════════════
#  WHATSAPP SENDEN
# ══════════════════════════════════════════════════════════════════
def send_whatsapp(to: str, text: str):
    if not (WHATSAPP_TOKEN and WHATSAPP_PHONE_ID):
        log.warning("WhatsApp nicht konfiguriert — Nachricht an %s: %s", to, text)
        return
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"preview_url": False, "body": text[:4096]},
    }
    try:
        resp = requests.post(GRAPH_URL, headers=headers, json=payload, timeout=30)
        if resp.status_code >= 400:
            log.error("Senden fehlgeschlagen (%s): %s", resp.status_code, resp.text)
    except Exception as e:
        log.error("Fehler beim Senden an %s: %s", to, e)


def notify_admin(text: str):
    if ADMIN_WHATSAPP:
        send_whatsapp(ADMIN_WHATSAPP, text)


# ══════════════════════════════════════════════════════════════════
#  CLAUDE
# ══════════════════════════════════════════════════════════════════
def ask_claude(wa_id: str) -> str:
    if client is None:
        return "عذراً، الخدمة غير متاحة حالياً. سيتواصل معك أحد موظفينا قريباً."
    history = get_history(wa_id)
    if not history:
        return ""
    try:
        resp = client.messages.create(
            model=MODEL,
            max_tokens=1500,
            system=[{
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }],
            messages=history,
        )
        return next((b.text for b in resp.content if b.type == "text"), "").strip()
    except anthropic.APIStatusError as e:
        log.error("Claude API-Fehler: %s", e)
    except Exception as e:
        log.error("Claude Fehler: %s", e)
    return "عذراً، حدث خطأ مؤقت. سيتواصل معك أحد موظفينا قريباً إن شاء الله."


# ══════════════════════════════════════════════════════════════════
#  ADMIN-BEFEHLE  (vom Admin an den Bot gesendet)
# ══════════════════════════════════════════════════════════════════
ADMIN_HELP = (
    "🛠️ *Admin-Befehle — Maya Investment Bot*\n\n"
    "/liste — alle Gespräche/Leads anzeigen\n"
    "/chat <nummer> — vollständiges Gespräch eines Kunden\n"
    "/stop <nummer> — Bot für diesen Kunden pausieren (Sie übernehmen)\n"
    "/start <nummer> — Bot für diesen Kunden wieder aktivieren\n"
    "/an <nummer> <text> — als Firma direkt eine Nachricht senden\n"
    "/hilfe — diese Hilfe\n\n"
    "Tipp: Nummer im Format 49151… (ohne + und ohne 00)."
)


def handle_admin_command(text: str):
    parts = text.strip().split(maxsplit=2)
    cmd = parts[0].lower()

    if cmd in ("/hilfe", "/help", "/start") and len(parts) == 1:
        notify_admin(ADMIN_HELP)

    elif cmd == "/liste":
        with db() as conn:
            rows = conn.execute(
                "SELECT wa_id, name, last_seen, manual_mode, msg_count "
                "FROM customers ORDER BY last_seen DESC LIMIT 50"
            ).fetchall()
        if not rows:
            notify_admin("📋 Noch keine Gespräche vorhanden.")
            return
        lines = [f"📋 *Gespräche* ({len(rows)})\n"]
        for i, r in enumerate(rows, 1):
            flag = "✋ MANUELL" if r["manual_mode"] else "🤖 Bot"
            name = r["name"] or "—"
            lines.append(
                f"*{i}.* {name}\n   📱 {r['wa_id']} | {flag}\n"
                f"   💬 {r['msg_count']} Nachr. | 🕒 {r['last_seen']}"
            )
        notify_admin("\n".join(lines))

    elif cmd == "/chat" and len(parts) >= 2:
        target = parts[1]
        with db() as conn:
            rows = conn.execute(
                "SELECT role, text, ts FROM messages WHERE wa_id=? ORDER BY id DESC LIMIT 30",
                (target,),
            ).fetchall()
        if not rows:
            notify_admin(f"Keine Nachrichten für {target}.")
            return
        rows = list(reversed(rows))
        icon = {"user": "👤", "assistant": "🤖", "admin": "🧑‍💼"}
        lines = [f"💬 *Gespräch mit {target}*\n"]
        for r in rows:
            lines.append(f"{icon.get(r['role'], '•')} {r['text']}")
        msg = "\n\n".join(lines)
        # In Teilen senden, falls zu lang
        for i in range(0, len(msg), 3800):
            notify_admin(msg[i:i + 3800])

    elif cmd == "/stop" and len(parts) >= 2:
        target = parts[1]
        set_manual(target, True)
        notify_admin(f"✋ Bot für {target} pausiert. Sie übernehmen jetzt.\n"
                     f"Mit /an {target} <text> antworten.")

    elif cmd == "/start" and len(parts) >= 2:
        target = parts[1]
        set_manual(target, False)
        notify_admin(f"🤖 Bot für {target} wieder aktiv.")

    elif cmd == "/an" and len(parts) >= 3:
        target, body = parts[1], parts[2]
        send_whatsapp(target, body)
        save_message(target, "admin", body)
        notify_admin(f"✅ Gesendet an {target}.")

    else:
        notify_admin("❓ Unbekannter Befehl.\n\n" + ADMIN_HELP)


# ══════════════════════════════════════════════════════════════════
#  NACHRICHTENVERARBEITUNG  (im Hintergrund)
# ══════════════════════════════════════════════════════════════════
def process_message(wa_id: str, name: str, text: str):
    # 1) Ist es der Admin? Dann als Admin-Befehl behandeln.
    if ADMIN_WHATSAPP and wa_id == ADMIN_WHATSAPP:
        if text.strip().startswith("/"):
            handle_admin_command(text)
        else:
            notify_admin("ℹ️ Befehl mit / beginnen.\n\n" + ADMIN_HELP)
        return

    # 2) Kunde: speichern
    is_new = upsert_customer(wa_id, name)
    save_message(wa_id, "user", text)

    if is_new:
        notify_admin(f"🆕 *Neuer Kunde*\n👤 {name or '—'}\n📱 {wa_id}\n💬 {text[:200]}")

    # 3) Manueller Modus? Bot schweigt, nur Admin benachrichtigen.
    if is_manual(wa_id):
        notify_admin(f"✋ (manuell) {name or wa_id}: {text[:300]}")
        return

    # 4) Bot antwortet via Claude
    reply = ask_claude(wa_id)
    if reply:
        save_message(wa_id, "assistant", reply)
        send_whatsapp(wa_id, reply)


# ══════════════════════════════════════════════════════════════════
#  FLASK / WEBHOOK
# ══════════════════════════════════════════════════════════════════
app = Flask(__name__)


@app.get("/")
def home():
    return "Maya Investment WhatsApp Bot läuft ✅", 200


@app.get("/webhook")
def verify():
    """Webhook-Verifizierung durch Meta."""
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        log.info("Webhook verifiziert.")
        return Response(challenge or "", status=200)
    return Response("Verification failed", status=403)


@app.post("/webhook")
def webhook():
    data = request.get_json(silent=True) or {}
    try:
        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                # Status-Updates (zugestellt/gelesen) ignorieren
                messages = value.get("messages")
                if not messages:
                    continue
                contacts = value.get("contacts", [])
                name = contacts[0].get("profile", {}).get("name", "") if contacts else ""
                for msg in messages:
                    msg_id = msg.get("id", "")
                    if msg_id and already_processed(msg_id):
                        continue
                    wa_id = msg.get("from", "")
                    mtype = msg.get("type")
                    if mtype == "text":
                        body = msg.get("text", {}).get("body", "")
                    else:
                        body = f"[{mtype}]"  # Bilder/Audio etc. — als Platzhalter
                    if wa_id and body:
                        threading.Thread(
                            target=process_message,
                            args=(wa_id, name, body),
                            daemon=True,
                        ).start()
    except Exception as e:
        log.error("Webhook-Fehler: %s", e)
    # Meta erwartet schnell ein 200
    return Response("OK", status=200)


# ══════════════════════════════════════════════════════════════════
init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    log.info("✅ Maya Investment WhatsApp Bot startet auf Port %s", port)
    app.run(host="0.0.0.0", port=port)
