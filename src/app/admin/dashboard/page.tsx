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

const PIPELINE_STATUSES = [
  "wohnung_angeboten",
  "interesse_bestaetigt",
  "besichtigung_angefragt",
  "besichtigung_geplant",
  "besichtigung_durchgefuehrt",
];

const PIPELINE_STATUS_LABEL: Record<string, string> = {
  wohnung_angeboten: "Wohnung angeboten",
  interesse_bestaetigt: "Interesse bestätigt",
  besichtigung_angefragt: "Besichtigung angefragt",
  besichtigung_geplant: "Besichtigung geplant",
  besichtigung_durchgefuehrt: "Besichtigung durchgeführt",
};

interface PipelineApplicant {
  id: string;
  internal_code: string;
  first_name: string;
  last_name: string;
  num_persons: number | null;
  household_net_income: number | null;
  status_key: string;
  property: { internal_code: string; object_name: string | null } | null;
}

async function loadPipelineApplicants(
  sortColumn: "household_net_income" | "num_persons",
  ascending: boolean,
): Promise<PipelineApplicant[]> {
  const supabase = await createClient();
  const { data: applicants } = await supabase
    .from("applicants")
    .select("id, internal_code, first_name, last_name, num_persons, household_net_income, status_key")
    .in("status_key", PIPELINE_STATUSES)
    .order(sortColumn, { ascending, nullsFirst: false })
    .limit(20);

  if (!applicants || applicants.length === 0) return [];

  const { data: offers } = await supabase
    .from("property_offers")
    .select("applicant_id, sent_at, property:properties(internal_code, object_name)")
    .in(
      "applicant_id",
      applicants.map((a) => a.id),
    )
    .order("sent_at", { ascending: false });

  const propertyByApplicant = new Map<string, PipelineApplicant["property"]>();
  for (const offer of offers ?? []) {
    if (propertyByApplicant.has(offer.applicant_id)) continue;
    const property = Array.isArray(offer.property) ? (offer.property[0] ?? null) : offer.property;
    propertyByApplicant.set(offer.applicant_id, property);
  }

  return applicants.map((a) => ({ ...a, property: propertyByApplicant.get(a.id) ?? null }));
}

export default async function DashboardPage({
  searchParams,
}: {
  searchParams: Promise<{ psort?: string; porder?: string }>;
}) {
  const params = await searchParams;
  const sortColumn = params.psort === "persons" ? "num_persons" : "household_net_income";
  const ascending = params.porder === "asc";

  const [counts, activity, confirmedViewings, pipelineApplicants] = await Promise.all([
    loadCounts(),
    loadRecentActivity(),
    loadConfirmedViewings(),
    loadPipelineApplicants(sortColumn, ascending),
  ]);

  function pipelineSortHref(column: "income" | "persons") {
    const nextOrder = params.psort === column && params.porder === "desc" ? "asc" : "desc";
    return `/admin/dashboard?psort=${column}&porder=${nextOrder}`;
  }

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

      <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-900">
            Kunden im Bewerbungsprozess ({pipelineApplicants.length})
          </h2>
          <div className="flex gap-3 text-xs">
            <Link
              href={pipelineSortHref("income")}
              className={`hover:text-slate-900 ${sortColumn === "household_net_income" ? "font-semibold text-slate-900" : "text-slate-500"}`}
            >
              Nach Einkommen {sortColumn === "household_net_income" && (ascending ? "↑" : "↓")}
            </Link>
            <Link
              href={pipelineSortHref("persons")}
              className={`hover:text-slate-900 ${sortColumn === "num_persons" ? "font-semibold text-slate-900" : "text-slate-500"}`}
            >
              Nach Personenzahl {sortColumn === "num_persons" && (ascending ? "↑" : "↓")}
            </Link>
          </div>
        </div>
        <p className="mt-1 text-sm text-slate-500">
          Alle Kunden, die sich aktiv für eine Wohnung interessieren — vom gesendeten Exposé bis zur
          bestätigten Besichtigung. Reine Neuanmeldungen ohne Wohnungsbezug stehen unter
          &bdquo;Interessenten&ldquo;.
        </p>
        {pipelineApplicants.length === 0 ? (
          <p className="mt-3 text-sm text-slate-400">
            Noch keine Kunden im Bewerbungsprozess — sende dazu ein Exposé auf einer Wohnungsseite.
          </p>
        ) : (
          <div className="mt-3 overflow-x-auto">
            <table className="w-full min-w-[640px] text-left text-sm">
              <thead className="text-xs tracking-wide text-slate-400 uppercase">
                <tr>
                  <th className="py-2 pr-4">Kunde</th>
                  <th className="py-2 pr-4">Wohnung</th>
                  <th className="py-2 pr-4">Personen</th>
                  <th className="py-2 pr-4">Nettoeinkommen</th>
                  <th className="py-2 pr-4">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {pipelineApplicants.map((a) => (
                  <tr key={a.id} className="hover:bg-slate-50">
                    <td className="py-2 pr-4">
                      <Link href={`/admin/applicants/${a.id}`} className="font-medium text-slate-900 hover:underline">
                        {a.first_name} {a.last_name}
                      </Link>
                      <span className="ml-1 font-mono text-xs text-slate-400">{a.internal_code}</span>
                    </td>
                    <td className="py-2 pr-4 text-slate-600">
                      {a.property?.object_name ?? a.property?.internal_code ?? "–"}
                    </td>
                    <td className="py-2 pr-4 text-slate-600">{a.num_persons ?? "–"}</td>
                    <td className="py-2 pr-4 text-slate-600">
                      {a.household_net_income ? `${a.household_net_income} €` : "–"}
                    </td>
                    <td className="py-2 pr-4">
                      <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700">
                        {PIPELINE_STATUS_LABEL[a.status_key] ?? a.status_key}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

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
