import Link from "next/link";
import { createClient } from "@/lib/supabase/server";
import type { Applicant, StatusDefinition } from "@/types/models";

const SORT_COLUMNS: Record<string, string> = {
  income: "household_net_income",
  persons: "num_persons",
  created: "created_at",
};

function sortHref(
  params: { q?: string; status?: string; city?: string; sort?: string; order?: string },
  column: string,
) {
  const nextOrder = params.sort === column && params.order === "desc" ? "asc" : "desc";
  const search = new URLSearchParams();
  if (params.q) search.set("q", params.q);
  if (params.status) search.set("status", params.status);
  if (params.city) search.set("city", params.city);
  search.set("sort", column);
  search.set("order", nextOrder);
  return `/admin/applicants?${search.toString()}`;
}

function SortHeader({
  label,
  column,
  params,
}: {
  label: string;
  column: string;
  params: { q?: string; status?: string; city?: string; sort?: string; order?: string };
}) {
  const active = params.sort === column;
  return (
    <Link href={sortHref(params, column)} className="inline-flex items-center gap-1 hover:text-slate-900">
      {label}
      {active && <span>{params.order === "desc" ? "↓" : "↑"}</span>}
    </Link>
  );
}

export default async function ApplicantsPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string; status?: string; city?: string; sort?: string; order?: string }>;
}) {
  const params = await searchParams;
  const supabase = await createClient();

  const sortColumn = SORT_COLUMNS[params.sort ?? ""] ?? "created_at";
  const ascending = params.order === "asc";

  let query = supabase
    .from("applicants")
    .select("*")
    .order(sortColumn, { ascending, nullsFirst: false });

  if (params.status) query = query.eq("status_key", params.status);
  if (params.city) query = query.ilike("desired_city", `%${params.city}%`);
  if (params.q) {
    query = query.or(
      `first_name.ilike.%${params.q}%,last_name.ilike.%${params.q}%,email.ilike.%${params.q}%,internal_code.ilike.%${params.q}%`,
    );
  }

  const [{ data: applicants }, { data: statuses }] = await Promise.all([
    query.limit(200),
    supabase.from("status_definitions").select("*").order("sort_order"),
  ]);

  const statusMap = new Map((statuses ?? []).map((s: StatusDefinition) => [s.key, s.label]));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Interessenten</h1>
          <p className="mt-1 text-sm text-slate-500">
            {applicants?.length ?? 0} Datensätze
          </p>
        </div>
        <Link
          href="/admin/applicants/new"
          className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700"
        >
          Neuer Interessent
        </Link>
      </div>

      <form className="flex flex-wrap gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <input
          name="q"
          defaultValue={params.q}
          placeholder="Name, E-Mail, INT-ID…"
          className="flex-1 min-w-[200px] rounded-lg border border-slate-300 px-3 py-2 text-sm"
        />
        <input
          name="city"
          defaultValue={params.city}
          placeholder="Ort"
          className="w-40 rounded-lg border border-slate-300 px-3 py-2 text-sm"
        />
        <select
          name="status"
          defaultValue={params.status ?? ""}
          className="w-56 rounded-lg border border-slate-300 px-3 py-2 text-sm"
        >
          <option value="">Alle Status</option>
          {(statuses ?? []).map((s: StatusDefinition) => (
            <option key={s.key} value={s.key}>
              {s.label}
            </option>
          ))}
        </select>
        <button
          type="submit"
          className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
        >
          Filtern
        </button>
      </form>

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-slate-200 bg-slate-50 text-xs tracking-wide text-slate-500 uppercase">
            <tr>
              <th className="px-4 py-3">ID</th>
              <th className="px-4 py-3">Name</th>
              <th className="px-4 py-3">Ort</th>
              <th className="px-4 py-3">Budget (Warm)</th>
              <th className="px-4 py-3">
                <SortHeader label="Personen" column="persons" params={params} />
              </th>
              <th className="px-4 py-3">
                <SortHeader label="Nettoeinkommen" column="income" params={params} />
              </th>
              <th className="px-4 py-3">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {(applicants ?? []).map((applicant: Applicant) => (
              <tr key={applicant.id} className="hover:bg-slate-50">
                <td className="px-4 py-3">
                  <Link
                    href={`/admin/applicants/${applicant.id}`}
                    className="font-mono text-xs font-medium text-slate-900 hover:underline"
                  >
                    {applicant.internal_code}
                  </Link>
                </td>
                <td className="px-4 py-3 text-slate-700">
                  {applicant.first_name} {applicant.last_name}
                </td>
                <td className="px-4 py-3 text-slate-500">{applicant.desired_city ?? "–"}</td>
                <td className="px-4 py-3 text-slate-500">
                  {applicant.max_warm_rent ? `${applicant.max_warm_rent} €` : "–"}
                </td>
                <td className="px-4 py-3 text-slate-500">{applicant.num_persons ?? "–"}</td>
                <td className="px-4 py-3 text-slate-500">
                  {applicant.household_net_income ? `${applicant.household_net_income} €` : "–"}
                </td>
                <td className="px-4 py-3">
                  <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700">
                    {statusMap.get(applicant.status_key) ?? applicant.status_key}
                  </span>
                </td>
              </tr>
            ))}
            {(applicants ?? []).length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-10 text-center text-sm text-slate-400">
                  Keine Interessenten gefunden.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
