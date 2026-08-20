import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import { getCurrentProfile } from "@/lib/auth";
import { createClient } from "@/lib/supabase/server";
import { OfferResponse } from "@/components/portal/offer-response";
import { ViewingConfirm } from "@/components/portal/viewing-confirm";

const AMENITY_LABELS: { key: string; label: string }[] = [
  { key: "has_balcony", label: "Balkon" },
  { key: "has_terrace", label: "Terrasse" },
  { key: "has_garden", label: "Garten" },
  { key: "has_elevator", label: "Aufzug" },
  { key: "has_parking_space", label: "Stellplatz" },
  { key: "has_garage", label: "Garage" },
  { key: "has_cellar", label: "Keller" },
  { key: "pets_allowed", label: "Haustiere erlaubt" },
];

export default async function OfferDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const profile = await getCurrentProfile();
  if (!profile) redirect("/login");
  if (profile.role === "admin" || profile.role === "makler") redirect("/admin");

  const supabase = await createClient();
  const { data: offer } = await supabase
    .from("property_offers")
    .select("id, response, applicant_id, property:properties(*)")
    .eq("id", id)
    .single();

  if (!offer || !offer.property) notFound();
  const property = Array.isArray(offer.property) ? offer.property[0] : offer.property;

  const [{ data: images }, { data: viewing }] = await Promise.all([
    supabase.from("property_images").select("*").eq("property_id", property.id).order("sort_order"),
    supabase
      .from("viewings")
      .select("id, scheduled_at, confirmed_at, status")
      .eq("property_id", property.id)
      .eq("applicant_id", offer.applicant_id)
      .order("created_at", { ascending: false })
      .limit(1)
      .maybeSingle(),
  ]);

  const gallery = (images ?? []).map((img) => ({
    ...img,
    url: supabase.storage.from("property-images").getPublicUrl(img.storage_path).data.publicUrl,
  }));

  const activeAmenities = AMENITY_LABELS.filter(
    (a) => (property as Record<string, unknown>)[a.key] === true,
  );

  return (
    <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col px-4 py-12">
      <Link href="/portal" className="mb-6 text-sm text-slate-500 hover:underline">
        ← Zurück zur Übersicht
      </Link>

      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        {gallery.length > 0 && (
          <div className="grid grid-cols-2 gap-1 sm:grid-cols-3">
            {gallery.map((img) => (
              // eslint-disable-next-line @next/next/no-img-element
              <img key={img.id} src={img.url} alt="" className="h-32 w-full object-cover sm:h-40" />
            ))}
          </div>
        )}

        <div className="p-6">
          <p className="font-mono text-xs text-slate-400">{property.internal_code}</p>
          <h1 className="mt-1 text-xl font-semibold text-slate-900">
            {property.object_name ??
              (`${property.street ?? ""} ${property.house_number ?? ""}`.trim() || "Wohnung")}
          </h1>
          <p className="text-sm text-slate-500">
            {property.postal_code} {property.city}
            {property.district ? ` · ${property.district}` : ""}
          </p>

          <div className="mt-4 grid grid-cols-2 gap-3 rounded-lg bg-slate-50 p-4 text-sm sm:grid-cols-3">
            <div>
              <p className="text-slate-400">Zimmer</p>
              <p className="font-medium text-slate-900">{property.rooms ?? "–"}</p>
            </div>
            <div>
              <p className="text-slate-400">Fläche</p>
              <p className="font-medium text-slate-900">
                {property.living_area ? `${property.living_area} m²` : "–"}
              </p>
            </div>
            <div>
              <p className="text-slate-400">Warmmiete</p>
              <p className="font-medium text-slate-900">
                {property.warm_rent ? `${property.warm_rent} €` : "–"}
              </p>
            </div>
            <div>
              <p className="text-slate-400">Etage</p>
              <p className="font-medium text-slate-900">{property.floor ?? "–"}</p>
            </div>
            <div>
              <p className="text-slate-400">Kaution</p>
              <p className="font-medium text-slate-900">
                {property.deposit ? `${property.deposit} €` : "–"}
              </p>
            </div>
            <div>
              <p className="text-slate-400">Einzug</p>
              <p className="font-medium text-slate-900">{property.move_in_date ?? "–"}</p>
            </div>
          </div>

          {activeAmenities.length > 0 && (
            <div className="mt-4 flex flex-wrap gap-2">
              {activeAmenities.map((a) => (
                <span
                  key={a.key}
                  className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-700"
                >
                  {a.label}
                </span>
              ))}
            </div>
          )}

          {property.description && (
            <p className="mt-4 text-sm whitespace-pre-line text-slate-600">
              {property.description}
            </p>
          )}

          <div className="mt-6 border-t border-slate-100 pt-6">
            <OfferResponse offerId={offer.id} currentResponse={offer.response} />
          </div>

          {viewing && viewing.scheduled_at && viewing.status !== "abgesagt" && (
            <div className="mt-4">
              <ViewingConfirm
                viewingId={viewing.id}
                scheduledAt={viewing.scheduled_at}
                confirmedAt={viewing.confirmed_at}
              />
            </div>
          )}
        </div>
      </div>
    </main>
  );
}
