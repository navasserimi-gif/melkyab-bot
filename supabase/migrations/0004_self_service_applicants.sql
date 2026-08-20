-- Phase 2: Interessenten legen ihr eigenes Profil über das öffentliche
-- Formular (/apply) an. Bisher durfte nur admin einen Datensatz in
-- 'applicants' anlegen — wir ergänzen eine zweite INSERT-Policy für den
-- Self-Service-Fall (Postgres verknüpft mehrere Policies für dieselbe
-- Aktion mit OR).

create policy applicants_self_insert on public.applicants for insert
  with check (user_id = auth.uid());

-- Ein Nutzer soll höchstens ein Interessenten-Profil haben. NULL bleibt
-- mehrfach erlaubt (von Staff angelegte Datensätze ohne verknüpften Nutzer).
alter table public.applicants
  add constraint applicants_user_id_unique unique (user_id);
