# Geschäftsmodell-Umfrage-Bot (melkyab_business_survey_bot.py)

Zweisprachiger (Deutsch/Persisch) Telegram-Bot für deine Gruppe: Interessenten
klicken auf einen Button, beantworten 7 Fragen im privaten Chat, und du
bekommst sofort eine Benachrichtigung + eine laufende Liste aller Anfragen.

## 1. Neuen Telegram-Bot erstellen

1. Öffne [@BotFather](https://t.me/BotFather) in Telegram.
2. `/newbot` → Namen vergeben (z. B. "MelkYab Business Umfrage").
3. Du bekommst einen **Bot-Token** (z. B. `123456:ABC-...`). Diesen brauchst
   du gleich als Umgebungsvariable `BUSINESS_BOT_TOKEN`.
4. Füge den neuen Bot als Mitglied zu deiner Telegram-Gruppe hinzu (normales
   Mitglied reicht, kein Admin nötig, solange die Gruppe Bots erlaubt, Nachrichten zu schreiben).

## 2. Deployment (Railway — als zweiten Service)

Dieses Repo enthält bereits einen laufenden Service für `melkyab_kredit_bot.py`.
Der neue Umfrage-Bot läuft als **eigener, zweiter Railway-Service** im
gleichen Repo:

1. Railway-Projekt öffnen → **New Service** → **Deploy from GitHub repo** →
   gleiches Repo (`melkyab-bot`) auswählen.
2. Im neuen Service unter **Settings → Deploy**: **Custom Start Command**
   setzen auf:
   ```
   python3 melkyab_business_survey_bot.py
   ```
3. Unter **Variables** folgende Umgebungsvariablen setzen:

   | Variable | Pflicht | Beschreibung |
   |---|---|---|
   | `BUSINESS_BOT_TOKEN` | ✅ | Token vom BotFather (Schritt 1) |
   | `ADMIN_ID` | ✅ | Deine Telegram-User-ID (numerisch, von [@userinfobot](https://t.me/userinfobot)) — kann die gleiche wie beim Kredit-Bot sein |
   | `GOOGLE_SHEETS_CREDENTIALS_JSON` | optional | siehe Abschnitt 3 |
   | `GOOGLE_SHEET_ID` | optional | siehe Abschnitt 3 |
   | `SMTP_USER`, `SMTP_PASSWORD`, `RECIPIENT_EMAIL` | optional | Für zusätzliche E-Mail-Benachrichtigung — gleiche Werte wie beim Immobilien-Analyzer wiederverwenden |

Ohne Google Sheets / SMTP läuft der Bot trotzdem vollständig: Alle Anfragen
landen in `business_leads.csv` und du bekommst bei jeder neuen Antwort sofort
eine Telegram-Nachricht.

## 3. Google Sheets anbinden (optional, kann später nachgeholt werden)

1. Google-Cloud-Projekt anlegen: https://console.cloud.google.com/
2. **Google Sheets API** aktivieren (APIs & Services → Library → "Google Sheets API" → Enable).
3. **Service Account** erstellen (APIs & Services → Credentials → Create Credentials →
   Service Account). Nach dem Anlegen: Tab **Keys** → **Add Key** → **JSON** →
   Datei wird heruntergeladen.
4. Öffne die JSON-Datei, kopiere den **gesamten Inhalt** und setze ihn als
   Wert der Umgebungsvariable `GOOGLE_SHEETS_CREDENTIALS_JSON` (als eine Zeile).
5. In der heruntergeladenen JSON-Datei steht ein Feld `client_email`
   (z. B. `melkyab-bot@dein-projekt.iam.gserviceaccount.com`).
6. Erstelle ein neues Google Sheet (sheets.google.com), öffne **Freigeben**
   und gib genau diese `client_email`-Adresse als **Bearbeiter** frei.
7. Kopiere die **Sheet-ID** aus der URL:
   `https://docs.google.com/spreadsheets/d/DIESE_ID_HIER/edit` → als
   `GOOGLE_SHEET_ID` setzen.
8. Optional: `GOOGLE_SHEET_WORKSHEET` setzen, falls das Tabellenblatt nicht
   "Leads" heißen soll (Standardwert: `Leads`).

Der Bot legt beim ersten Eintrag automatisch die Kopfzeile im Tabellenblatt an.

## 4. Benutzung

- **In der Gruppe:** Als Admin `/umfrage` schreiben → der Bot postet die
  zweisprachige Ankündigung mit Button "▶️ Umfrage starten / شروع پرسشنامه".
- **Privater Chat:** Klick auf den Button öffnet den Bot-Chat, Sprache wählen,
  7 Fragen beantworten (Geschäftsmodell, Kapital, Stadt, Telefon, Name,
  E-Mail, Startzeitpunkt).
- **Als Admin:** `/liste` im privaten Chat mit dem Bot zeigt eine
  Zusammenfassung aller Anfragen und schickt die CSV-Datei zum Download.
- Bei jeder neuen, abgeschlossenen Anfrage bekommst du sofort eine
  Telegram-Nachricht vom Bot (und optional eine E-Mail, falls SMTP gesetzt ist).

## 5. Abgefragte Punkte

1. Welches Geschäftsmodell (Kiosk, Gastronomie, Industriebetrieb, Handel, frei)
2. Eigenkapital / Budget (€)
3. Stadt
4. Telefonnummer
5. Vor- und Nachname
6. E-Mail-Adresse
7. Ab wann soll gestartet werden
