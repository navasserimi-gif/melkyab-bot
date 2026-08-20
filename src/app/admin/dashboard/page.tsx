import Link from "next/link";
import { createClient } from "@/lib/supabase/server";

async function loadCounts() {
  const supabase = await createClient();
  const sevenDaysAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString();

  const [applicants, properties, matches, openViewings, newApplicants, missingDocs, demand] =
    await Promise.all([
      supabase.from("applicants").select("id", { count: "exact", head: true }),
      supabase.from("properties").select("id", { count: "exact", head: true }),
      supabase.from("matches").select("id", { count: "exact", head: true }),
      supabase
        .from("viewings")
        .select("id", { count: "exact", head: true })
        .in("status", ["angefragt", "geplant"]),
      supabase
        .from("applicants")
        .select("id", { count: "exact", head: true })
        .gte("created_at", sevenDaysAgo),
      supabase
        .from("applicants")
        .select("id", { count: "exact", head: true })
        .or("has_schufa.eq.false,has_income_proof.eq.false,has_debt_clearance_cert.eq.false"),
      supabase
        .from("property_demand")
        .select("property_id, match_count")
        .order("match_count", { ascending: false })
        .limit(5),
    ]);

  let topProperties: { internal_code: string; city: string | null; match_count: number }[] = [];
  if (demand.data && demand.data.length > 0) {
    const { data: props } = await supabase
      .from("properties")
      .select("id, internal_code, city")
      .in(
        "id",
        demand.data.map((d) => d.property_id),
      );
    const byId = new Map((props ?? []).map((p) => [p.id, p]));
    topProperties = demand.data
      .map((d) => {
        const p = byId.get(d.property_id);
        return p ? { internal_code: p.internal_code, city: p.city, match_count: d.match_count } : null;
      })
      .filter((v): v is { internal_code: string; city: string | null; match_count: number } => v !== null);
  }

  return {
    applicants: applicants.count ?? 0,
    properties: properties.count ?? 0,
    matches: matches.count ?? 0,
    openViewings: openViewings.count ?? 0,
    newApplicants: newApplicants.count ?? 0,
    missingDocs: missingDocs.count ?? 0,
    topProperties,
  };
}

async function loadRecentActivity() {
  const supabase = await createClient();
  const { data } = await supabase
    .from("audit_log")
    .select("id, action, entity_type, entity_id, created_at")
    .order("created_at", { ascending: false })
    .limit(10);
  return data ?? [];
}

interface ConfirmedViewing {
  id: string;
  scheduled_at: string;
  confirmed_at: string;
  property: { internal_code: string; object_name: string | null } | null;
  applicant: { internal_code: string; first_name: string; last_name: string } | null;
}

async function loadConfirmedViewings(): Promise<ConfirmedViewing[]> {
  const supabase = await createClient();
  const { data } = await supabase
    .from("viewings")
    .select(
      "id, scheduled_at, confirmed_at, property:properties(internal_code, object_name), applicant:applicants(internal_code, first_name, last_name)",
    )
    .not("confirmed_at", "is", null)
    .order("confirmed_at", { ascending: false })
    .limit(5);

  return (data ?? []).map((v) => ({
    id: v.id,
    scheduled_at: v.scheduled_at as string,
    confirmed_at: v.confirmed_at as string,
    property: Array.isArray(v.property) ? (v.property[0] ?? null) : v.property,
    applicant: Array.isArray(v.applicant) ? (v.applicant[0] ?? null) : v.applicant,
  }));
}

export default async function DashboardPage() {
  const [counts, activity, confirmedViewings] = await Promise.all([
    loadCounts(),
    loadRecentActivity(),
    loadConfirmedViewings(),
  ]);

  const tiles = [
    { label: "Interessenten", value: counts.applicants, href: "/admin/applicants" },
    { label: "Wohnungen", value: counts.properties, href: "/admin/properties" },
    { label: "Passende Matches", value: counts.matches, href: "/admin/applicants" },
    { label: "Offene Besichtigungen", value: counts.openViewings, href: "/admin/viewings" },
    { label: "Fehlende Unterlagen", value: counts.missingDocs, href: "/admin/applicants" },
    { label: "Neue Interessenten (7 Tage)", value: counts.newApplicants, href: "/admin/applicants" },
  ];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Dashboard</h1>
        <p className="mt-1 text-sm text-slate-500">Überblick über den aktuellen Prozessstand.</p>
      </div>

      {confirmedViewings.length > 0 && (
        <section className="rounded-xl border border-emerald-200 bg-emerald-50 p-5 shadow-sm">
          <h2 className="text-sm font-semibold text-emerald-900">
            ✓ Kürzlich bestätigte Besichtigungstermine
          </h2>
          <ul className="mt-3 divide-y divide-emerald-100">
            {confirmedViewings.map((v) => (
              <li key={v.id} className="flex flex-wrap items-center justify-between gap-2 py-2 text-sm">
                <span className="text-emerald-900">
                  {v.applicant ? `${v.applicant.first_name} ${v.applicant.last_name}` : "–"} ·{" "}
                  {v.property?.object_name ?? v.property?.internal_code}
                </span>
                <span className="text-emerald-700">
                  {new Date(v.scheduled_at).toLocaleString("de-DE", {
                    dateStyle: "medium",
                    timeStyle: "short",
                  })}
                </span>
              </li>
            ))}
          </ul>
          <Link
            href="/admin/viewings"
            className="mt-3 inline-block text-sm font-medium text-emerald-700 hover:underline"
          >
            Alle Besichtigungen ansehen →
          </Link>
        </section>
      )}

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
        {tiles.map((tile) => (
          <Link
            key={tile.label}
            href={tile.href}
            className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-slate-300"
          >
            <p className="text-sm text-slate-500">{tile.label}</p>
            <p className="mt-2 text-3xl font-semibold text-slate-900">{tile.value}</p>
          </Link>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="text-sm font-semibold text-slate-900">Wohnungen mit hoher Nachfrage</h2>
          {counts.topProperties.length === 0 ? (
            <p className="mt-3 text-sm text-slate-400">Noch keine Matches berechnet.</p>
          ) : (
            <ul className="mt-3 divide-y divide-slate-100">
              {counts.topProperties.map((p) => (
                <li key={p.internal_code} className="flex items-center justify-between py-2 text-sm">
                  <span className="text-slate-700">
                    {p.internal_code}
                    {p.city ? ` · ${p.city}` : ""}
                  </span>
                  <span className="font-medium text-slate-900">{p.match_count} Matches</span>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="text-sm font-semibold text-slate-900">Aktivitäten</h2>
          {activity.length === 0 ? (
            <p className="mt-3 text-sm text-slate-400">Noch keine Aktivitäten protokolliert.</p>
          ) : (
            <ul className="mt-3 divide-y divide-slate-100">
              {activity.map((entry) => (
                <li key={entry.id} className="py-2 text-sm text-slate-600">
                  <span className="font-medium text-slate-900">{entry.action}</span>{" "}
                  {entry.entity_type} {entry.entity_id ? `(${entry.entity_id.slice(0, 8)}…)` : ""}
                  <span className="ml-2 text-xs text-slate-400">
                    {new Date(entry.created_at).toLocaleString("de-DE")}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </div>
  );
}
