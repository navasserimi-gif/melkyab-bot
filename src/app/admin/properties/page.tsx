import Link from "next/link";
import { createClient } from "@/lib/supabase/server";
import type { Property } from "@/types/models";

const STATUS_LABEL: Record<string, string> = {
  entwurf: "Entwurf",
  veroeffentlicht: "Veröffentlicht",
  reserviert: "Reserviert",
  vermietet: "Vermietet",
  archiviert: "Archiviert",
};

export default async function PropertiesPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string; city?: string; status?: string }>;
}) {
  const params = await searchParams;
  const supabase = await createClient();

  let query = supabase.from("properties").select("*").order("created_at", { ascending: false });
  if (params.status) query = query.eq("status", params.status);
  if (params.city) query = query.ilike("city", `%${params.city}%`);
  if (params.q) {
    query = query.or(
      `object_name.ilike.%${params.q}%,internal_code.ilike.%${params.q}%,street.ilike.%${params.q}%`,
    );
  }

  const { data: properties } = await query.limit(200);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Wohnungen</h1>
          <p className="mt-1 text-sm text-slate-500">{properties?.length ?? 0} Datensätze</p>
        </div>
        <Link
          href="/admin/properties/new"
          className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700"
        >
          Neue Wohnung
        </Link>
      </div>

      <form className="flex flex-wrap gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <input
          name="q"
          defaultValue={params.q}
          placeholder="Objekt, WHG-ID, Straße…"
          className="flex-1 min-w-[200px] rounded-lg border border-slate-300 px-3 py-2 text-sm"
        />
        <input
          name="city"
          defaultValue={params.city}
          placeholder="Ort"
          className="w-40 rounded-lg border border-slate-300 px-3 py-2 text-sm"
        />
        <select name="status" defaultValue={params.status ?? ""} className="w-48 rounded-lg border border-slate-300 px-3 py-2 text-sm">
          <option value="">Alle Status</option>
          {Object.entries(STATUS_LABEL).map(([key, label]) => (
            <option key={key} value={key}>
              {label}
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
              <th className="px-4 py-3">Objekt / Adresse</th>
              <th className="px-4 py-3">Zimmer</th>
              <th className="px-4 py-3">Warmmiete</th>
              <th className="px-4 py-3">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {(properties ?? []).map((property: Property) => (
              <tr key={property.id} className="hover:bg-slate-50">
                <td className="px-4 py-3">
                  <Link
                    href={`/admin/properties/${property.id}`}
                    className="font-mono text-xs font-medium text-slate-900 hover:underline"
                  >
                    {property.internal_code}
                  </Link>
                </td>
                <td className="px-4 py-3 text-slate-700">
                  {property.object_name ?? (`${property.street ?? ""} ${property.house_number ?? ""}`.trim() || "–")}
                  <span className="ml-1 text-slate-400">{property.city ?? ""}</span>
                </td>
                <td className="px-4 py-3 text-slate-500">{property.rooms ?? "–"}</td>
                <td className="px-4 py-3 text-slate-500">
                  {property.warm_rent ? `${property.warm_rent} €` : "–"}
                </td>
                <td className="px-4 py-3">
                  <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700">
                    {STATUS_LABEL[property.status] ?? property.status}
                  </span>
                </td>
              </tr>
            ))}
            {(properties ?? []).length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-10 text-center text-sm text-slate-400">
                  Keine Wohnungen gefunden.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
