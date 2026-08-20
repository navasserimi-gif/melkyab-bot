# Mietwohnungs-CRM & Automatisierungsplattform — Architektur

Status: Phase 1 in Umsetzung · Stack: Next.js (App Router) + TypeScript + Tailwind CSS + Supabase (Postgres, Auth, Storage, RLS)

Dieses Dokument ist die verbindliche Referenz für Datenmodell, Rollen, Events, Workflows,
Seiten-/API-Struktur, Sicherheitskonzept und Roadmap. Es wird bei größeren Architekturentscheidungen
fortlaufend aktualisiert.

## 1. Systemarchitektur (Überblick)

```
┌─────────────────────────────────────────────────────────────────┐
│                        Next.js App (Vercel/Railway)               │
│                                                                     │
│  app/(public)     Landingpage, Marketing                          │
│  app/apply         Mehrstufiges Interessenten-Formular             │
│  app/(auth)        Login / Registrierung                          │
│  app/portal        Interessenten-Self-Service                     │
│  app/admin         Admin-/Makler-Backoffice                       │
│  app/api/*         Route Handlers (Webhooks, Signed URLs, Cron)    │
│                                                                     │
│  Server Actions ──► Supabase Server Client (Service Role, nur BE)  │
│  Client Components ─► Supabase Browser Client (anon key, RLS)      │
└───────────────┬─────────────────────────────────┬─────────────────┘
                │                                   │
                ▼                                   ▼
      ┌───────────────────┐               ┌──────────────────────┐
      │ Supabase Postgres   │               │ Supabase Storage       │
      │ + Auth + RLS         │◄─────────────►│ (private Buckets:      │
      │ + DB-Functions/Trig. │   Events       │  documents, property-  │
      └─────────┬───────────┘   Tabelle       │  images)               │
                │                              └──────────────────────┘
                ▼
      ┌───────────────────────┐
      │ Worker-Prozess (Node)   │  Railway "worker" (ersetzt den alten
      │ - Event-Dispatcher      │  Python-Bot-Prozess 1:1 im Deployment)
      │ - Cron: Erinnerungen    │
      │ - Matching-Recompute    │
      │ - Telegram-Bot (optional)│
      │ - E-Mail-Versand        │
      └───────────────────────┘
```

**Kernentscheidung:** Kein n8n. Automatisierung läuft als Event-Log in Postgres
(`events`-Tabelle) + einem schlanken Node-Worker-Prozess, der Events abarbeitet,
Cron-Jobs ausführt (Erinnerungen, Matching) und externe Integrationen (E-Mail,
Telegram, Google Chat) anspricht. Das Web (Next.js) schreibt Events synchron beim
jeweiligen Vorgang (z. B. `VIEWING_CREATED`); der Worker konsumiert sie asynchron.
Das ist bewusst einfach gehalten (kein Redis/Queue-Service nötig) und passt zum
bestehenden Railway-Deployment-Modell (web + worker), das schon für den alten Bot
verwendet wurde.

## 2. Datenmodell (ER-Übersicht)

```
profiles (1) ───< applicants (1) ───< applicant_documents
   │                    │        \
   │                    │         ──< viewings >── properties
   │                    │                              │
   │                    ├──< matches >──────────────────┘
   │                    ├──< property_offers >──────────┘
   │                    ├──< applicant_status_history
   │                    └──< consents
   │
   └──< audit_log (actor_id)

properties (1) ──< property_images
properties (1) ──< property_documents
properties (1) ──< property_notes

status_definitions, document_types, matching_weights,
email_templates, reminder_rules      → Admin-Konfiguration (kein Code-Deploy nötig)

events                                → Automatisierungs-Event-Log
messages                              → Kommunikationsprotokoll (E-Mail/Telegram/System)
```

### Kern-Tabellen (Auszug, vollständig in `supabase/migrations/`)

**profiles** — 1:1 zu `auth.users`. `id, role (admin|makler|interessent), full_name, email, phone, active, created_at`.

**applicants (Interessenten)** — `id, internal_code (INT-0001047, per DB-Sequence), user_id → profiles,`
Stammdaten, Suchprofil (Ort, Stadtteile, Personen, Zimmer, Fläche, Miete, Einzugstermin),
Haushalt (Haustiere, Raucher, Anforderungen), Einkommen, Beschäftigung, Aufenthaltsstatus
(konfigurierbare Kategorie, siehe unten), `status_key → status_definitions`, `assigned_to → profiles`,
`internal_notes`, `created_at, updated_at`.

**properties (Wohnungen)** — `id, internal_code, external_id, company, object_name,`
Adresse (Straße, Nr., PLZ, Ort, Stadtteil), Etage, Zimmer, Fläche, Kaltmiete, Nebenkosten,
Heizkosten, Warmmiete (generated column), Kaution, Einzugsdatum, Ausstattungs-Flags (Balkon,
Terrasse, Garten, Aufzug, Stellplatz, Garage, Keller, Haustiere erlaubt), Energieinfo,
Beschreibung, `status (entwurf|veröffentlicht|reserviert|vermietet|archiviert)`,
`source_provider` (siehe Import-Architektur), `created_at, updated_at`.

**property_images** — `id, property_id, storage_path, category (titelbild|wohnzimmer|schlafzimmer|
küche|bad|balkon|grundriss|sonstige), sort_order`.

**applicant_documents / property_documents** — `id, owner_id, doc_type_id → document_types,
storage_path (privater Bucket), status (ausstehend|geprüft|abgelehnt), valid_until, uploaded_at`.
Zugriff **ausschließlich** über kurzlebige Signed URLs (Server Action), nie öffentliche Pfade.

**viewings (Besichtigungen)** — `id, property_id, applicant_id, scheduled_at, status
(angefragt|geplant|durchgeführt|abgesagt|verschoben), google_calendar_event_id, internal_note,
feedback (möchte_die_wohnung|unsicher|kein_interesse), feedback_at`.

**matches** — `id, applicant_id, property_id, score, score_breakdown (jsonb: {ort,budget,zimmer,
flaeche,einzug,haustier,haushaltsgroesse}), computed_at`. Wird bei relevanten Änderungen
(neues Inserat, geändertes Suchprofil) neu berechnet, nicht bei jedem Seitenaufruf.

**property_offers** — `id, applicant_id, property_id, match_id, sent_at, sent_via, response
(interesse|kein_interesse|besichtigung_angefragt|offen)`.

**status_definitions / matching_weights / document_types / email_templates / reminder_rules** —
reine Konfigurationstabellen, nur für `admin` beschreibbar (RLS), treiben UI + Matching-Engine +
Automatisierung, ohne dass Code geändert werden muss (Anforderung §37).

**consents** — DSGVO-Einwilligungen (`type, granted_at, revoked_at, text_version`).

**audit_log** — `actor_id, action, entity_type, entity_id, diff (jsonb), created_at`. Wird per
DB-Trigger + Server-Action-Wrapper befüllt (§32).

**events** — `id, type, payload (jsonb), created_at, processed_at, error`. Vom Worker konsumiert
(§21/§22).

## 3. Rollen- und Berechtigungskonzept

| Rolle | Interessenten | Wohnungen | Matching-Config | Besichtigungen | Dokumente | Nutzer/Settings |
|---|---|---|---|---|---|---|
| **admin** | voll | voll | voll (Gewichtung, Status) | voll | voll | voll |
| **makler** | lesen/bearbeiten (konfigurierbar je Zuweisung) | lesen | lesen | verwalten | lesen | – |
| **interessent** | nur eigener Datensatz | nur passende/angebotene | – | nur eigene, anfragen | nur eigene, hochladen | nur eigenes Profil |

Durchsetzung **immer in zwei Schichten**: (1) Postgres Row Level Security auf jeder Tabelle
(nicht optional — greift auch bei direktem DB-Zugriff), (2) Next.js Middleware/Server-Action-Checks
für UX (Redirects, UI-Ausblendung). Makler-Feinrechte (z. B. "darf löschen") liegen in einer
`permissions`-Spalte auf `profiles` bzw. einer `role_permissions`-Konfigtabelle, vom Admin editierbar.

## 4. Event-System & Workflows

Events (siehe §21) werden von Server Actions synchron in die `events`-Tabelle geschrieben,
sobald der fachliche Vorgang abgeschlossen ist (z. B. nach erfolgreichem Insert in `viewings`).
Der Worker pollt neue Events (`processed_at IS NULL`), führt konfigurierte Aktionen aus
(E-Mail-Vorlage senden, Telegram-Nachricht, Google-Chat-Post, Status setzen, Reminder planen)
und markiert das Event als verarbeitet. Reminder-Regeln (§22) sind Zeit-getriggerte Cron-Jobs,
die selbst wieder Events erzeugen (`DOCUMENT_MISSING_REMINDER` etc.) — dadurch bleibt alles über
denselben Mechanismus nachvollziehbar und im Audit-Log sichtbar.

## 5. Matching-Engine

Serverseitige, reine Funktion `computeMatchScore(applicant, property, weights)` → Score 0–100 +
Breakdown je Kriterium (Ort, Budget, Zimmer, Fläche, Einzugstermin, Haustier, Haushaltsgröße;
Standardgewichtung wie in §12). Gewichtung kommt aus `matching_weights` (admin-editierbar).
Der Score ist **ausschließlich Entscheidungsunterstützung** — keine automatische Ablehnung,
keine automatische Herausfilterung nach Aufenthaltsstatus oder Staatsangehörigkeit. Neuberechnung
wird durch Events getriggert (`PROPERTY_PUBLISHED`, `PROFILE_COMPLETED`), nicht per Cron-Vollscan.

## 6. Seitenstruktur (Next.js App Router)

```
app/
  (public)/              Landingpage
  apply/                 Öffentliches, mehrstufiges Interessenten-Formular
  (auth)/login
  (auth)/register
  portal/                 Interessenten-Bereich (geschützt, Rolle: interessent)
    profile/ matches/ offers/[id]/ viewings/ documents/
  admin/                  Backoffice (geschützt, Rolle: admin|makler)
    dashboard/
    applicants/[id]/
    properties/[id]/album/
    matching/ viewings/ documents/ messages/
    settings/statuses  settings/matching-weights  settings/document-types
    settings/email-templates  settings/reminders  settings/users
    audit-log/
  api/
    documents/[id]/signed-url/   (Server-only, kurzlebige URL)
    webhooks/telegram/
    cron/reminders/
    cron/match-recompute/
```

## 7. API-/Datenzugriffsstruktur

Primär **Server Actions** (co-located mit den Seiten) statt einer separaten REST-API-Schicht —
weniger Fläche, typsicher End-to-End. Route Handlers (`app/api/*`) nur wo nötig: Webhooks
(Telegram), Signed-URL-Ausgabe, Cron-Endpunkte (vom Worker/Scheduler aufgerufen, per Secret
geschützt). Jede Server Action prüft Rolle serverseitig, bevor sie den Supabase-Server-Client
(mit User-JWT, nicht Service-Role) verwendet — RLS greift dadurch immer zusätzlich.

## 8. Sicherheitskonzept

- Supabase Auth (E-Mail/Passwort), Passwort-Policy, optional Magic Link für Interessenten.
- RLS auf **jeder** Tabelle mit personenbezogenen Daten; Service-Role-Key nie im Client, nur in
  Server Actions/Worker über Env-Variablen.
- Storage-Buckets `documents` und `property-images` privat; Auslieferung sensibler Dokumente
  ausschließlich über zeitlich begrenzte Signed URLs, generiert serverseitig nach Rechteprüfung.
- Keine sensiblen Dokumente über Telegram — Bot verlinkt nur auf das authentifizierte Webportal.
- Audit-Log für alle schreibenden Admin-/Makler-Aktionen.
- DSGVO: Einwilligungsverwaltung (`consents`), Datenexport/-löschung als Server Action pro
  Interessent, konfigurierbare Aufbewahrungsfristen (Cron prüft `retention_until`).
- Aufenthaltsstatus-Feld: neutrale, konfigurierbare Auswahlliste (§5), fließt **nicht** als
  automatisches Ausschlusskriterium ins Matching ein.

## 9. Roadmap / Phasen

| Phase | Inhalt | Status |
|---|---|---|
| **1** | Projektgrundlage, Auth, DB-Schema, Rollen, Admin-Shell, Interessenten- & Wohnungs-CRUD | **läuft (diese Session)** |
| 2 | Öffentliches Mehrstufen-Formular, Matching-Engine, Wohnungsangebote | offen |
| 3 | Dokumente, Besichtigungen, Google-Calendar-Vorbereitung, E-Mail, Telegram | offen |
| 4 | Google Chat, automatische Erinnerungen, Workflow-/Event-Engine, Statistiken | offen |
| 5 | Importsystem (CSV/Excel/API), `PropertyImportProvider`-Schnittstelle für weitere Gesellschaften | offen |

## 10. Wichtige Entscheidungen (Kurzfassung)

1. **n8n bewusst nicht verwendet** — Automatisierung läuft nativ über Event-Tabelle + Worker.
2. **Bestehender Python-Bot wird ersetzt** (Nutzerentscheidung) — Railway-Deployment bleibt im
   Web+Worker-Muster bestehen, nur die Laufzeit wechselt auf Node/Next.js.
3. **Server Actions statt REST-First** — weniger Boilerplate, typsicher, RLS bleibt zweite
   Verteidigungslinie.
4. **Alle Stammdaten (Status, Gewichtung, Dokumenttypen, Vorlagen) sind DB-Konfiguration**, nicht
   Code — Admin kann ohne Deploy anpassen (§37).
5. **Import-Provider-Interface von Anfang an entkoppelt** (`PropertyImportProvider`), auch wenn
   Phase 1 nur manuelle Eingabe enthält — verhindert späteren Umbau bei weiteren
   Wohnungsgesellschaften.
