-- Hilfs-View für das Admin-Dashboard ("Wohnungen mit hoher Nachfrage", §18).
-- security_invoker sorgt dafür, dass die RLS-Policies der zugrunde liegenden
-- Tabellen für den abfragenden Nutzer gelten (kein Bypass durch den View-Owner).

create view public.property_demand
  with (security_invoker = true) as
  select property_id, count(*) as match_count
  from public.matches
  group by property_id;
