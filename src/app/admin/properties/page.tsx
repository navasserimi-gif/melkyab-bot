import Link from "next/link";
import { createClient } from "@/lib/supabase/server";
import { SendOfferForm } from "@/components/admin/send-offer-form";
import type { Property } from "@/types/models";

const STATUS_LABEL: Record<string, string> = {
  entwurf: "Entwurf",
  veroeffentlicht: "Veröffentlicht",
  reserviert: "Reserviert",
  vermietet: "Vermietet",
  archiviert: "Archiviert",
};

const STATUS_COLOR: Record<string, string> = {
  entwurf: "bg-slate-100 text-slate-700",
  veroeffentlicht: "bg-emerald-100 text-emerald-700",
  reserviert: "bg-amber-100 text-amber-700",
  vermietet: "bg-blue-100 text-blue-700",
  archiviert: "bg-slate-100 text-slate-400",
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
  const propertyIds = (properties ?? []).map((p) => p.id);

  const [{ data: images }, { data: applicants }, { data: offers }] = await Promise.all([
    propertyIds.length
      ? supabase
          .from("property_images")
          .select("property_id, storage_path, sort_order")
          .in("property_id", propertyIds)
          .order("sort_order")
      : Promise.resolve({ data: [] }),
    supabase
      .from("applicants")
      .select("id, internal_code, first_name, last_name")
      .neq("status_key", "neu")
      .order("created_at", { ascending: false })
      .limit(200),
    propertyIds.length
      ? supabase.from("property_offers").select("property_id, applicant_id").in("property_id", propertyIds)
      : Promise.resolve({ data: [] }),
  ]);

  const coverByProperty = new Map<string, string>();
  for (const img of images ?? []) {
    if (!coverByProperty.has(img.property_id)) {
      coverByProperty.set(
        img.property_id,
        supabase.storage.from("property-images").getPublicUrl(img.storage_path).data.publicUrl,
      );
    }
  }

  const sentByProperty = new Map<string, string[]>();
  for (const offer of offers ?? []) {
    const list = sentByProperty.get(offer.property_id) ?? [];
    list.push(offer.applicant_id);
    sentByProperty.set(offer.property_id, list);
  }

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

      {(properties ?? []).length === 0 ? (
        <p className="rounded-xl border border-slate-200 bg-white px-4 py-10 text-center text-sm text-slate-400">
          Keine Wohnungen gefunden.
        </p>
      ) : (
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {(properties ?? []).map((property: Property) => (
            <div
              key={property.id}
              className="flex flex-col overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm"
            >
              <Link href={`/admin/properties/${property.id}`} className="block">
                <div className="h-40 w-full bg-slate-100">
                  {coverByProperty.has(property.id) ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={coverByProperty.get(property.id)}
                      alt=""
                      className="h-full w-full object-cover"
                    />
                  ) : (
                    <div className="flex h-full w-full items-center justify-center text-xs text-slate-400">
                      Kein Bild
                    </div>
                  )}
                </div>
                <div className="p-4 pb-2">
                  <div className="flex items-center justify-between">
                    <p className="font-mono text-xs text-slate-400">{property.internal_code}</p>
                    <span
                      className={`rounded-full px-2.5 py-1 text-xs font-medium ${STATUS_COLOR[property.status] ?? "bg-slate-100 text-slate-700"}`}
                    >
                      {STATUS_LABEL[property.status] ?? property.status}
                    </span>
                  </div>
                  <p className="mt-1 font-medium text-slate-900 hover:underline">
                    {property.object_name ??
                      (`${property.street ?? ""} ${property.house_number ?? ""}`.trim() || "Wohnung")}
                  </p>
                  <p className="text-sm text-slate-500">{property.city ?? "–"}</p>
                  <div className="mt-2 flex gap-4 text-sm text-slate-600">
                    <span>{property.rooms ?? "–"} Zimmer</span>
                    <span>{property.warm_rent ? `${property.warm_rent} €` : "–"}</span>
                  </div>
                </div>
              </Link>

              <div className="mt-auto border-t border-slate-100 p-4 pt-3">
                <p className="mb-2 text-xs font-medium text-slate-500">Exposé senden</p>
                <SendOfferForm
                  propertyId={property.id}
                  applicants={applicants ?? []}
                  alreadySentTo={sentByProperty.get(property.id) ?? []}
                />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
