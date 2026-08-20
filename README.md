# Mietwohnungs-CRM & Automatisierungsplattform

Plattform zur Verwaltung von Mietinteressenten, Wohnungen, Matching, Besichtigungen und
Bewerbungsprozessen. Architektur, Datenmodell, Rollen- und Sicherheitskonzept sowie die
Roadmap stehen in [ARCHITECTURE.md](./ARCHITECTURE.md).

Stack: Next.js (App Router) · TypeScript · Tailwind CSS · Supabase (Postgres, Auth, Storage, RLS)

## Setup

1. Supabase-Projekt anlegen und die Migrationen aus `supabase/migrations/` in der
   angegebenen Reihenfolge ausführen (SQL-Editor oder `supabase db push`).
2. `.env.local` aus `.env.example` erstellen und mit den Projektwerten befüllen.
3. Abhängigkeiten installieren und Dev-Server starten:

   ```bash
   npm install
   npm run dev
   ```

4. Ersten Admin-Account anlegen: über `/register` registrieren (Standardrolle
   `interessent`), anschließend in Supabase die `role`-Spalte des Profils in der
   Tabelle `profiles` manuell auf `admin` setzen.

## Projektstruktur

```
src/app/(auth)/        Login, Registrierung
src/app/portal/         Interessenten-Self-Service (Phase 2+)
src/app/admin/           Admin-/Makler-Backoffice (Dashboard, Interessenten, Wohnungen)
src/lib/supabase/        Browser-/Server-/Middleware-Clients
src/lib/matching/        Matching-Engine (§12)
src/types/models.ts       Domain-Typen passend zum DB-Schema
supabase/migrations/     SQL-Schema, RLS-Policies, Storage-Buckets, Views
```

## Status

Phase 1 (Projektgrundlage, Auth, DB-Schema, Rollen, Admin-Bereich, Interessenten- und
Wohnungs-CRUD) ist umgesetzt. Weitere Phasen siehe Roadmap in `ARCHITECTURE.md`.

## Deployment (Railway)

`nixpacks.toml` baut und startet die Next.js-App (`npm ci && npm run build`, Start über
`npm run start`, Port aus `$PORT`). Umgebungsvariablen aus `.env.example` müssen im
Railway-Projekt hinterlegt werden.
