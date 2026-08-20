-- Besichtigungs-Workflow (§15): Admin schlägt einen Termin vor (scheduled_at +
-- status='geplant'), der Interessent bestätigt ihn separat. confirmed_at
-- unterscheidet "Vorschlag gesendet" von "vom Kunden bestätigt", ohne den
-- bestehenden status-Wertebereich zu erweitern.

alter table public.viewings add column confirmed_at timestamptz;
