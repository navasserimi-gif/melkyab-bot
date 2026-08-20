-- Mietwohnungs-CRM — initiales Schema (Phase 1)
-- Reihenfolge: Erweiterungen -> Hilfsfunktionen -> Konfigurationstabellen -> Kern-Tabellen -> Trigger -> RLS

create extension if not exists "pgcrypto";

-- ============================================================================
-- 1. profiles (1:1 zu auth.users) + Rollen-Hilfsfunktionen
-- ============================================================================

create table public.profiles (
  id uuid primary key references auth.users (id) on delete cascade,
  role text not null default 'interessent' check (role in ('admin', 'makler', 'interessent')),
  full_name text,
  email text,
  phone text,
  active boolean not null default true,
  permissions jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

comment on table public.profiles is 'Erweitert auth.users um Rolle und Stammdaten. Rolle wird nie aus Client-Metadaten übernommen (Schutz vor Selbst-Eskalation).';

create or replace function public.current_role()
returns text
language sql stable security definer set search_path = public as $$
  select role from public.profiles where id = auth.uid();
$$;

create or replace function public.is_staff()
returns boolean
language sql stable security definer set search_path = public as $$
  select public.current_role() in ('admin', 'makler');
$$;

create or replace function public.is_admin()
returns boolean
language sql stable security definer set search_path = public as $$
  select public.current_role() = 'admin';
$$;

-- Neuen Auth-User automatisch als 'interessent' anlegen. Rolle ausschließlich
-- server-/adminseitig über UPDATE profiles.role änderbar (siehe Trigger unten).
create or replace function public.handle_new_user()
returns trigger
language plpgsql security definer set search_path = public as $$
begin
  insert into public.profiles (id, email, full_name, role)
  values (new.id, new.email, new.raw_user_meta_data ->> 'full_name', 'interessent');
  return new;
end;
$$;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();

create or replace function public.prevent_role_self_escalation()
returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if new.role is distinct from old.role and not public.is_admin() then
    new.role := old.role;
  end if;
  return new;
end;
$$;

create trigger trg_prevent_role_escalation
  before update on public.profiles
  for each row execute procedure public.prevent_role_self_escalation();

-- ============================================================================
-- 2. Konfigurationstabellen (admin-editierbar, ohne Deploy)
-- ============================================================================

create table public.status_definitions (
  key text primary key,
  label text not null,
  sort_order int not null default 0,
  color text,
  is_active boolean not null default true
);

create table public.document_types (
  key text primary key,
  label text not null,
  required boolean not null default false,
  sort_order int not null default 0,
  is_active boolean not null default true
);

create table public.matching_weights (
  criterion text primary key,
  weight int not null check (weight >= 0),
  updated_at timestamptz not null default now()
);

create table public.email_templates (
  key text primary key,
  subject text not null,
  body text not null,
  updated_at timestamptz not null default now()
);

create table public.reminder_rules (
  key text primary key,
  trigger_event text not null,
  delay_hours int not null,
  is_active boolean not null default true
);

insert into public.status_definitions (key, label, sort_order) values
  ('neu', 'Neu', 10),
  ('formular_ausgefuellt', 'Formular ausgefüllt', 20),
  ('vorgeprueft', 'Vorgeprüft', 30),
  ('unterlagen_unvollstaendig', 'Unterlagen unvollständig', 40),
  ('unterlagen_vollstaendig', 'Unterlagen vollständig', 50),
  ('passende_wohnung_gefunden', 'Passende Wohnung gefunden', 60),
  ('wohnung_angeboten', 'Wohnung angeboten', 70),
  ('interesse_bestaetigt', 'Interesse bestätigt', 80),
  ('besichtigung_angefragt', 'Besichtigung angefragt', 90),
  ('besichtigung_geplant', 'Besichtigung geplant', 100),
  ('besichtigung_durchgefuehrt', 'Besichtigung durchgeführt', 110),
  ('wohnung_gewuenscht', 'Wohnung gewünscht', 120),
  ('bewerbung_uebermittelt', 'Bewerbung übermittelt', 130),
  ('vermietet', 'Vermietet', 140),
  ('abgesagt', 'Abgesagt', 150),
  ('abgeschlossen', 'Abgeschlossen', 160);

insert into public.document_types (key, label, required, sort_order) values
  ('einkommensnachweis', 'Einkommensnachweis', true, 10),
  ('schufa', 'Schufa-Auskunft', true, 20),
  ('mietschuldenfreiheit', 'Mietschuldenfreiheitsbescheinigung', true, 30),
  ('arbeitsvertrag', 'Arbeitsvertrag', false, 40),
  ('ausweis', 'Ausweisdokument', false, 50),
  ('sonstiges', 'Sonstiges', false, 60);

insert into public.matching_weights (criterion, weight) values
  ('ort', 25), ('budget', 25), ('zimmer', 15), ('flaeche', 10),
  ('einzugstermin', 10), ('haustier', 5), ('haushaltsgroesse', 10);

-- ============================================================================
-- 3. Interessenten (applicants)
-- ============================================================================

create sequence public.applicant_code_seq start 1;

create table public.applicants (
  id uuid primary key default gen_random_uuid(),
  internal_code text unique not null
    default ('INT-' || lpad(nextval('public.applicant_code_seq')::text, 7, '0')),
  user_id uuid references public.profiles (id) on delete set null,
  assigned_to uuid references public.profiles (id) on delete set null,
  status_key text not null default 'neu' references public.status_definitions (key),

  -- Persönliche Daten
  first_name text not null,
  last_name text not null,
  email text,
  phone text,
  current_address text,
  preferred_contact text check (preferred_contact in ('email', 'telefon', 'telegram')),

  -- Wohnungssuche
  desired_city text,
  desired_districts text[] not null default '{}',
  num_persons int,
  num_adults int,
  num_children int,
  desired_rooms_min numeric,
  desired_area_min numeric,
  desired_area_max numeric,
  max_cold_rent numeric,
  max_warm_rent numeric,
  desired_move_in date,

  -- Haushalt
  has_pets boolean not null default false,
  pet_type text,
  smoker boolean not null default false,
  special_requirements text,

  -- Einkommen / Beschäftigung
  household_net_income numeric,
  num_income_earners int,
  employment_status text check (employment_status in ('angestellt', 'selbststaendig', 'ausbildung', 'studium', 'rente', 'sonstige')),
  employment_type text check (employment_type in ('unbefristet', 'befristet', 'probezeit', 'sonstige')),
  other_income text,

  -- Bewerbungsinformationen (Nachweis-Flags; Dateien liegen in applicant_documents)
  has_schufa boolean not null default false,
  has_income_proof boolean not null default false,
  has_debt_clearance_cert boolean not null default false,
  further_documents_note text,

  -- Aufenthaltsstatus: neutrale, konfigurierbare Kategorie — kein automatisches
  -- Ausschlusskriterium im Matching (siehe lib/matching).
  residence_status text check (residence_status in ('deutsche_staatsangehoerigkeit', 'eu_aufenthaltsstatus', 'befristeter_aufenthaltstitel', 'unbefristeter_aufenthaltstitel', 'sonstiger_status')),

  internal_notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index applicants_status_idx on public.applicants (status_key);
create index applicants_user_idx on public.applicants (user_id);
create index applicants_city_idx on public.applicants (desired_city);

create table public.applicant_status_history (
  id uuid primary key default gen_random_uuid(),
  applicant_id uuid not null references public.applicants (id) on delete cascade,
  old_status text,
  new_status text not null,
  changed_by uuid references public.profiles (id),
  changed_at timestamptz not null default now(),
  note text
);

create table public.consents (
  id uuid primary key default gen_random_uuid(),
  applicant_id uuid not null references public.applicants (id) on delete cascade,
  type text not null,
  granted_at timestamptz,
  revoked_at timestamptz,
  text_version text
);

-- ============================================================================
-- 4. Wohnungen (properties)
-- ============================================================================

create sequence public.property_code_seq start 1;

create table public.properties (
  id uuid primary key default gen_random_uuid(),
  internal_code text unique not null
    default ('WHG-' || lpad(nextval('public.property_code_seq')::text, 5, '0')),
  external_id text,
  company text,
  object_name text,
  street text,
  house_number text,
  postal_code text,
  city text,
  district text,
  floor text,
  rooms numeric,
  living_area numeric,
  cold_rent numeric,
  ancillary_costs numeric,
  heating_costs numeric,
  warm_rent numeric generated always as
    (coalesce(cold_rent, 0) + coalesce(ancillary_costs, 0) + coalesce(heating_costs, 0)) stored,
  deposit numeric,
  move_in_date date,
  has_balcony boolean not null default false,
  has_terrace boolean not null default false,
  has_garden boolean not null default false,
  has_elevator boolean not null default false,
  has_parking_space boolean not null default false,
  has_garage boolean not null default false,
  has_cellar boolean not null default false,
  pets_allowed boolean not null default false,
  energy_info text,
  description text,
  status text not null default 'entwurf' check (status in ('entwurf', 'veroeffentlicht', 'reserviert', 'vermietet', 'archiviert')),
  -- Import-Architektur (§11/§33): 'manual' heute, später z.B. 'csv', 'excel', <provider-key>.
  source_provider text not null default 'manual',
  internal_notes text,
  created_by uuid references public.profiles (id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index properties_status_idx on public.properties (status);
create index properties_city_idx on public.properties (city);

create table public.property_images (
  id uuid primary key default gen_random_uuid(),
  property_id uuid not null references public.properties (id) on delete cascade,
  storage_path text not null,
  category text not null default 'sonstige' check (category in ('titelbild', 'wohnzimmer', 'schlafzimmer', 'kueche', 'bad', 'balkon', 'grundriss', 'sonstige')),
  sort_order int not null default 0,
  created_at timestamptz not null default now()
);

create table public.property_documents (
  id uuid primary key default gen_random_uuid(),
  property_id uuid not null references public.properties (id) on delete cascade,
  label text not null,
  storage_path text not null,
  uploaded_by uuid references public.profiles (id),
  created_at timestamptz not null default now()
);

-- ============================================================================
-- 5. Dokumente, Besichtigungen, Matching, Angebote, Nachrichten
-- ============================================================================

create table public.applicant_documents (
  id uuid primary key default gen_random_uuid(),
  applicant_id uuid not null references public.applicants (id) on delete cascade,
  doc_type_key text not null references public.document_types (key),
  storage_path text not null,
  status text not null default 'ausstehend' check (status in ('ausstehend', 'geprueft', 'abgelehnt')),
  valid_until date,
  uploaded_by uuid references public.profiles (id),
  uploaded_at timestamptz not null default now()
);

create table public.viewings (
  id uuid primary key default gen_random_uuid(),
  property_id uuid not null references public.properties (id) on delete cascade,
  applicant_id uuid not null references public.applicants (id) on delete cascade,
  scheduled_at timestamptz,
  status text not null default 'angefragt' check (status in ('angefragt', 'geplant', 'durchgefuehrt', 'abgesagt', 'verschoben')),
  google_calendar_event_id text,
  internal_note text,
  feedback text check (feedback in ('moechte_die_wohnung', 'unsicher', 'kein_interesse')),
  feedback_at timestamptz,
  created_by uuid references public.profiles (id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.matches (
  id uuid primary key default gen_random_uuid(),
  applicant_id uuid not null references public.applicants (id) on delete cascade,
  property_id uuid not null references public.properties (id) on delete cascade,
  score numeric not null,
  score_breakdown jsonb not null default '{}'::jsonb,
  computed_at timestamptz not null default now(),
  unique (applicant_id, property_id)
);

create table public.property_offers (
  id uuid primary key default gen_random_uuid(),
  applicant_id uuid not null references public.applicants (id) on delete cascade,
  property_id uuid not null references public.properties (id) on delete cascade,
  match_id uuid references public.matches (id) on delete set null,
  sent_at timestamptz not null default now(),
  sent_via text not null default 'system',
  response text not null default 'offen' check (response in ('interesse', 'kein_interesse', 'besichtigung_angefragt', 'offen')),
  responded_at timestamptz
);

create table public.messages (
  id uuid primary key default gen_random_uuid(),
  applicant_id uuid references public.applicants (id) on delete set null,
  channel text not null check (channel in ('email', 'telegram', 'system')),
  recipient text,
  subject text,
  content text,
  status text not null default 'ausstehend' check (status in ('ausstehend', 'gesendet', 'fehlgeschlagen')),
  error text,
  created_at timestamptz not null default now(),
  sent_at timestamptz
);

-- ============================================================================
-- 6. Audit-Log & Events (Automatisierungs-Grundlage, §21/§32)
-- ============================================================================

create table public.audit_log (
  id uuid primary key default gen_random_uuid(),
  actor_id uuid references public.profiles (id),
  action text not null,
  entity_type text not null,
  entity_id text,
  diff jsonb,
  created_at timestamptz not null default now()
);

create table public.events (
  id uuid primary key default gen_random_uuid(),
  type text not null,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  processed_at timestamptz,
  error text
);

create index events_unprocessed_idx on public.events (created_at) where processed_at is null;

-- Server Actions rufen diese Funktion statt eines direkten INSERTs auf, damit
-- authentifizierte (nicht nur Service-Role-)Clients Events schreiben können,
-- ohne dass 'events' generell für Clients lesbar/schreibbar sein muss.
create or replace function public.emit_event(p_type text, p_payload jsonb default '{}'::jsonb)
returns uuid
language plpgsql security definer set search_path = public as $$
declare
  v_id uuid;
begin
  insert into public.events (type, payload) values (p_type, p_payload) returning id into v_id;
  return v_id;
end;
$$;

grant execute on function public.emit_event(text, jsonb) to authenticated;

-- ============================================================================
-- 7. Generische Trigger: updated_at, Audit-Log, Status-Historie
-- ============================================================================

create or replace function public.set_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create trigger trg_updated_at_profiles before update on public.profiles
  for each row execute procedure public.set_updated_at();
create trigger trg_updated_at_applicants before update on public.applicants
  for each row execute procedure public.set_updated_at();
create trigger trg_updated_at_properties before update on public.properties
  for each row execute procedure public.set_updated_at();
create trigger trg_updated_at_viewings before update on public.viewings
  for each row execute procedure public.set_updated_at();

create or replace function public.log_audit()
returns trigger
language plpgsql security definer set search_path = public as $$
declare
  v_entity_id text;
begin
  v_entity_id := (case when tg_op = 'DELETE' then old.id else new.id end)::text;
  insert into public.audit_log (actor_id, action, entity_type, entity_id, diff)
  values (
    auth.uid(),
    tg_op,
    tg_table_name,
    v_entity_id,
    case tg_op
      when 'INSERT' then to_jsonb(new)
      when 'UPDATE' then jsonb_build_object('old', to_jsonb(old), 'new', to_jsonb(new))
      when 'DELETE' then to_jsonb(old)
    end
  );
  return coalesce(new, old);
end;
$$;

create trigger trg_audit_applicants after insert or update or delete on public.applicants
  for each row execute procedure public.log_audit();
create trigger trg_audit_properties after insert or update or delete on public.properties
  for each row execute procedure public.log_audit();
create trigger trg_audit_viewings after insert or update or delete on public.viewings
  for each row execute procedure public.log_audit();

create or replace function public.log_status_change()
returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if new.status_key is distinct from old.status_key then
    insert into public.applicant_status_history (applicant_id, old_status, new_status, changed_by)
    values (new.id, old.status_key, new.status_key, auth.uid());
  end if;
  return new;
end;
$$;

create trigger trg_status_history after update on public.applicants
  for each row execute procedure public.log_status_change();

-- ============================================================================
-- 8. Row Level Security
-- ============================================================================

alter table public.profiles enable row level security;
alter table public.status_definitions enable row level security;
alter table public.document_types enable row level security;
alter table public.matching_weights enable row level security;
alter table public.email_templates enable row level security;
alter table public.reminder_rules enable row level security;
alter table public.applicants enable row level security;
alter table public.applicant_status_history enable row level security;
alter table public.consents enable row level security;
alter table public.properties enable row level security;
alter table public.property_images enable row level security;
alter table public.property_documents enable row level security;
alter table public.applicant_documents enable row level security;
alter table public.viewings enable row level security;
alter table public.matches enable row level security;
alter table public.property_offers enable row level security;
alter table public.messages enable row level security;
alter table public.audit_log enable row level security;
alter table public.events enable row level security;

-- profiles
create policy profiles_select on public.profiles for select
  using (id = auth.uid() or public.is_staff());
create policy profiles_update on public.profiles for update
  using (id = auth.uid() or public.is_admin());

-- Konfigurationstabellen: Status/Dokumenttypen öffentlich lesbar (werden auch
-- im späteren öffentlichen Formular benötigt), Rest nur für Staff lesbar.
-- Schreiben überall nur admin.
create policy status_definitions_select on public.status_definitions for select using (true);
create policy status_definitions_write on public.status_definitions for all
  using (public.is_admin()) with check (public.is_admin());

create policy document_types_select on public.document_types for select using (true);
create policy document_types_write on public.document_types for all
  using (public.is_admin()) with check (public.is_admin());

create policy matching_weights_select on public.matching_weights for select using (public.is_staff());
create policy matching_weights_write on public.matching_weights for all
  using (public.is_admin()) with check (public.is_admin());

create policy email_templates_select on public.email_templates for select using (public.is_staff());
create policy email_templates_write on public.email_templates for all
  using (public.is_admin()) with check (public.is_admin());

create policy reminder_rules_select on public.reminder_rules for select using (public.is_staff());
create policy reminder_rules_write on public.reminder_rules for all
  using (public.is_admin()) with check (public.is_admin());

-- applicants: Staff sieht/bearbeitet alle, admin erstellt/löscht, Interessent nur eigenen Datensatz.
create policy applicants_select on public.applicants for select
  using (public.is_staff() or user_id = auth.uid());
create policy applicants_insert on public.applicants for insert
  with check (public.is_admin());
create policy applicants_update on public.applicants for update
  using (public.is_staff() or user_id = auth.uid());
create policy applicants_delete on public.applicants for delete
  using (public.is_admin());

create policy applicant_status_history_select on public.applicant_status_history for select
  using (public.is_staff() or exists (
    select 1 from public.applicants a where a.id = applicant_id and a.user_id = auth.uid()
  ));

create policy consents_select on public.consents for select
  using (public.is_staff() or exists (
    select 1 from public.applicants a where a.id = applicant_id and a.user_id = auth.uid()
  ));
create policy consents_write on public.consents for all
  using (public.is_staff() or exists (
    select 1 from public.applicants a where a.id = applicant_id and a.user_id = auth.uid()
  ))
  with check (public.is_staff() or exists (
    select 1 from public.applicants a where a.id = applicant_id and a.user_id = auth.uid()
  ));

-- properties: Staff sieht alles; Interessenten nur veröffentlichte Wohnungen,
-- für die ein Match mit ihrem eigenen Interessenten-Datensatz existiert.
-- Schreiben ausschließlich admin (§4 Rollenmatrix: Makler nur "ansehen").
create policy properties_select on public.properties for select
  using (
    public.is_staff()
    or (
      status = 'veroeffentlicht' and exists (
        select 1 from public.matches m
        join public.applicants a on a.id = m.applicant_id
        where m.property_id = properties.id and a.user_id = auth.uid()
      )
    )
  );
create policy properties_write on public.properties for all
  using (public.is_admin()) with check (public.is_admin());

create policy property_images_select on public.property_images for select
  using (
    public.is_staff()
    or exists (
      select 1 from public.properties p where p.id = property_id and p.status = 'veroeffentlicht' and exists (
        select 1 from public.matches m join public.applicants a on a.id = m.applicant_id
        where m.property_id = p.id and a.user_id = auth.uid()
      )
    )
  );
create policy property_images_write on public.property_images for all
  using (public.is_admin()) with check (public.is_admin());

create policy property_documents_select on public.property_documents for select using (public.is_staff());
create policy property_documents_write on public.property_documents for all
  using (public.is_admin()) with check (public.is_admin());

-- applicant_documents: Staff alles, Interessent nur eigene (inkl. Upload).
create policy applicant_documents_select on public.applicant_documents for select
  using (public.is_staff() or exists (
    select 1 from public.applicants a where a.id = applicant_id and a.user_id = auth.uid()
  ));
create policy applicant_documents_write on public.applicant_documents for all
  using (public.is_staff() or exists (
    select 1 from public.applicants a where a.id = applicant_id and a.user_id = auth.uid()
  ))
  with check (public.is_staff() or exists (
    select 1 from public.applicants a where a.id = applicant_id and a.user_id = auth.uid()
  ));

-- viewings: Staff verwaltet alle (Makler inklusive), Interessent sieht/erstellt eigene.
create policy viewings_select on public.viewings for select
  using (public.is_staff() or exists (
    select 1 from public.applicants a where a.id = applicant_id and a.user_id = auth.uid()
  ));
create policy viewings_write on public.viewings for all
  using (public.is_staff() or exists (
    select 1 from public.applicants a where a.id = applicant_id and a.user_id = auth.uid()
  ))
  with check (public.is_staff() or exists (
    select 1 from public.applicants a where a.id = applicant_id and a.user_id = auth.uid()
  ));

-- matches: Staff sieht/verwaltet alle, Interessent sieht nur eigene (kein Schreibzugriff —
-- Score wird serverseitig/durch die Matching-Engine berechnet).
create policy matches_select on public.matches for select
  using (public.is_staff() or exists (
    select 1 from public.applicants a where a.id = applicant_id and a.user_id = auth.uid()
  ));
create policy matches_write on public.matches for all
  using (public.is_staff()) with check (public.is_staff());

-- property_offers: Staff verwaltet alle, Interessent sieht/beantwortet eigene.
create policy property_offers_select on public.property_offers for select
  using (public.is_staff() or exists (
    select 1 from public.applicants a where a.id = applicant_id and a.user_id = auth.uid()
  ));
create policy property_offers_insert on public.property_offers for insert
  with check (public.is_staff());
create policy property_offers_update on public.property_offers for update
  using (public.is_staff() or exists (
    select 1 from public.applicants a where a.id = applicant_id and a.user_id = auth.uid()
  ));

-- messages: nur Staff sieht das Kommunikationsprotokoll im Adminbereich.
-- Schreiben erfolgt über Server Actions/Worker (service role) — kein Client-Insert.
create policy messages_select on public.messages for select using (public.is_staff());

-- audit_log: nur admin sieht die Historie. Insert ausschließlich über die
-- SECURITY DEFINER Trigger-Funktion (bypasst RLS), kein Client-Insert.
create policy audit_log_select on public.audit_log for select using (public.is_admin());

-- events: keine Client-Policies — nur service role (Worker) und emit_event()
-- (SECURITY DEFINER) können schreiben; lesbar nur für den Worker (service role).
