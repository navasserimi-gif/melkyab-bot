# Maya Investment GmbH — WhatsApp Business Bot 🤖

KI-Assistent für die **Blue-Card- / Visa-Personalvermittlung**.
Der Bot kommuniziert mit Kunden auf **Arabisch (alle Dialekte)** und **Farsi**,
erkennt aus den ersten Nachrichten das Herkunftsland und antwortet im selben
Dialekt — formell, höflich, wie ein persönlicher Assistent.

Sie als Inhaber können **jederzeit manuell eingreifen** und bekommen **alle
Gespräche als Liste**.

---

## Was der Bot kann

- **Mehrsprachig & dialektgenau** – arabische Dialekte (Syrien, Irak, Ägypten,
  Maghreb, Golf, Levante …) + Farsi. Antwortet automatisch im Dialekt des Kunden.
- **Berät & sammelt Infos** – erklärt die Leistung, beantwortet Fragen, sammelt
  Name, Land, Familiengröße, Beruf/Qualifikation, Sprachniveau.
- **Kennt alle Eckdaten** – 50.000 € pro Familie, Überweisung an *Maya
  Investment GmbH*, erste 3 Monate Beschäftigung gesichert, danach Anstellung
  selbst oder Selbstständigkeit, Visumverfahren über die Anwälte in Deutschland.
- **Admin-Steuerung über WhatsApp** – Liste aller Gespräche, einzelnes Gespräch
  ansehen, Bot pausieren/aktivieren, selbst als Firma antworten.
- **Speichert alles** – jede Konversation wird in einer Datenbank gesichert.

---

## Admin-Befehle (von Ihrer Nummer an den Bot senden)

| Befehl | Wirkung |
|---|---|
| `/liste` | Alle Gespräche/Leads anzeigen |
| `/chat <nummer>` | Vollständiges Gespräch eines Kunden |
| `/stop <nummer>` | Bot für diesen Kunden pausieren — **Sie übernehmen** |
| `/start <nummer>` | Bot wieder aktivieren |
| `/an <nummer> <text>` | Als Firma direkt eine Nachricht senden |
| `/hilfe` | Hilfe anzeigen |

> Nummern im Format `4915112345678` (ohne `+`, ohne `00`).
> Bei jedem **neuen Kunden** bekommen Sie automatisch eine Benachrichtigung.

---

## Einrichtung in 4 Schritten

### 1. Meta / WhatsApp Cloud API einrichten
1. Bei [developers.facebook.com](https://developers.facebook.com) ein App-/Business-Konto anlegen.
2. Produkt **WhatsApp** hinzufügen → Sie erhalten:
   - **Access-Token** → `WHATSAPP_TOKEN`
   - **Phone Number ID** → `WHATSAPP_PHONE_NUMBER_ID`
3. Für den Dauerbetrieb einen **permanenten System-User-Token** erstellen
   (der Test-Token läuft nach 24 h ab).

### 2. Umgebungsvariablen setzen
Siehe `.env.example`. In Ihrer Hosting-Umgebung (z. B. Railway/Render) eintragen:

```
ANTHROPIC_API_KEY=sk-ant-...          ← Ihr Anthropic-Schlüssel
WHATSAPP_TOKEN=EAAG...
WHATSAPP_PHONE_NUMBER_ID=123456789012345
WHATSAPP_VERIFY_TOKEN=maya-investment-verify
ADMIN_WHATSAPP=4915112345678          ← Ihre eigene Nummer
```

### 3. Deployen
Das Projekt enthält `Procfile`, `nixpacks.toml` und `requirements.txt` —
läuft direkt auf Railway, Render o. ä. als **Web-Service**.
Sie bekommen eine öffentliche URL, z. B. `https://ihr-bot.up.railway.app`.

### 4. Webhook bei Meta verbinden
Im Meta-Dashboard unter **WhatsApp → Configuration → Webhook**:
- **Callback-URL:** `https://ihr-bot.up.railway.app/webhook`
- **Verify-Token:** derselbe Wert wie `WHATSAPP_VERIFY_TOKEN`
- Feld **`messages`** abonnieren.

Fertig — sobald ein Kunde Ihre WhatsApp-Nummer anschreibt, antwortet der Bot.

---

## Lokal testen

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
python3 whatsapp_bluecard_bot.py
```

Der Server läuft dann auf `http://localhost:8080`.

---

## Wichtige Hinweise

- **24-Stunden-Fenster:** WhatsApp erlaubt freie Antworten nur innerhalb von 24 h
  nach der letzten Kundennachricht. Da Kunden den Bot anschreiben, ist das hier
  normalerweise kein Problem. Für Erstkontakt durch Sie wären *Message Templates*
  nötig.
- **Sprache des Bots:** Die Geschäftsregeln stehen im `SYSTEM_PROMPT` in
  `whatsapp_bluecard_bot.py`. Preise/Bedingungen können Sie dort jederzeit anpassen.
- **Datenschutz:** Die Datei `bluecard.db` enthält Kundengespräche und ist per
  `.gitignore` vom Repository ausgeschlossen. Behandeln Sie sie vertraulich (DSGVO).
- **Bilder/Sprachnachrichten** werden aktuell nur als Platzhalter erkannt
  (`[image]`, `[audio]`). Bei Bedarf erweiterbar.

---

## Dateien

| Datei | Zweck |
|---|---|
| `whatsapp_bluecard_bot.py` | Der WhatsApp-Bot (Flask + Claude) |
| `requirements.txt` | Python-Abhängigkeiten |
| `Procfile` / `nixpacks.toml` | Start-/Deploy-Konfiguration |
| `.env.example` | Vorlage für Umgebungsvariablen |
| `melkyab_kredit_bot.py` | Älterer Telegram-Kreditrechner-Bot (separat, unverändert) |
