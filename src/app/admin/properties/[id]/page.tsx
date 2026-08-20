import { notFound } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { PropertyForm } from "@/components/admin/property-form";
import { SendOfferForm } from "@/components/admin/send-offer-form";
import { PropertyImageUploadForm } from "@/components/admin/property-image-upload-form";
import {
  updateProperty,
  deleteProperty,
  uploadPropertyImage,
  deletePropertyImage,
} from "../actions";

const CATEGORY_LABEL: Record<string, string> = {
  titelbild: "Titelbild",
  wohnzimmer: "Wohnzimmer",
  schlafzimmer: "Schlafzimmer",
  kueche: "Küche",
  bad: "Badezimmer",
  balkon: "Balkon",
  grundriss: "Grundriss",
  sonstige: "Weitere Bilder",
};

export default async function PropertyDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const supabase = await createClient();

  const [{ data: property }, { data: images }, { data: applicants }, { data: offers }, { count: matchCount }] =
    await Promise.all([
      supabase.from("properties").select("*").eq("id", id).single(),
      supabase.from("property_images").select("*").eq("property_id", id).order("sort_order"),
      supabase
        .from("applicants")
        .select("id, internal_code, first_name, last_name")
        .order("created_at", { ascending: false })
        .limit(200),
      supabase.from("property_offers").select("applicant_id, sent_via").eq("property_id", id),
      supabase.from("matches").select("id", { count: "exact", head: true }).eq("property_id", id),
    ]);

  if (!property) notFound();

  const boundUpdate = updateProperty.bind(null, id);
  const boundDelete = deleteProperty.bind(null, id);
  const boundUpload = uploadPropertyImage.bind(null, id);

  const gallery = (images ?? []).map((img) => ({
    ...img,
    url: supabase.storage.from("property-images").getPublicUrl(img.storage_path).data.publicUrl,
  }));

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <p className="font-mono text-xs text-slate-400">{property.internal_code}</p>
          <h1 className="mt-1 text-2xl font-semibold text-slate-900">
            {property.object_name ?? (`${property.street ?? ""} ${property.house_number ?? ""}`.trim() || "Wohnung")}
          </h1>
        </div>
        <form action={boundDelete}>
          <button
            type="submit"
            className="rounded-lg border border-red-200 px-4 py-2 text-sm font-medium text-red-600 hover:bg-red-50"
          >
            Wohnung löschen
          </button>
        </form>
      </div>

      <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="text-sm font-semibold text-slate-900">Wohnungsalbum</h2>

        {gallery.length > 0 ? (
          <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4">
            {gallery.map((img) => (
              <div key={img.id} className="group relative overflow-hidden rounded-lg border border-slate-200">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={img.url} alt={CATEGORY_LABEL[img.category]} className="h-32 w-full object-cover" />
                <div className="absolute inset-x-0 bottom-0 flex items-center justify-between bg-black/60 px-2 py-1">
                  <span className="text-xs text-white">{CATEGORY_LABEL[img.category]}</span>
                  <form action={deletePropertyImage.bind(null, id, img.id, img.storage_path)}>
                    <button type="submit" className="text-xs text-red-300 hover:text-red-100">
                      Entfernen
                    </button>
                  </form>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="mt-3 text-sm text-slate-400">Noch keine Bilder hochgeladen.</p>
        )}

        <PropertyImageUploadForm action={boundUpload} />
      </section>

      {property.status === "veroeffentlicht" && (
        <section className="rounded-xl border border-emerald-200 bg-emerald-50 p-5 shadow-sm">
          <h2 className="text-sm font-semibold text-emerald-900">Automatisches Matching</h2>
          <p className="mt-1 text-sm text-emerald-800">
            {matchCount ?? 0} Interessenten mit Suchprofil abgeglichen ·{" "}
            {(offers ?? []).filter((o) => o.sent_via === "automatisch").length} davon automatisch
            per Portal-Angebot benachrichtigt (Match-Score ≥ 50).
          </p>
        </section>
      )}

      <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="text-sm font-semibold text-slate-900">Exposé an Interessenten senden</h2>
        <p className="mt-1 text-sm text-slate-500">
          Der Interessent sieht Fotos, Eckdaten und Beschreibung in seinem Portal und kann mit
          Interesse, kein Interesse oder Besichtigungsanfrage antworten. Bei Veröffentlichung
          werden gut passende Interessenten automatisch benachrichtigt — hier kannst du zusätzlich
          gezielt an Einzelne senden.
        </p>
        <div className="mt-4">
          <SendOfferForm
            propertyId={id}
            applicants={applicants ?? []}
            alreadySentTo={(offers ?? []).map((o) => o.applicant_id)}
          />
        </div>
      </section>

      <PropertyForm property={property} action={boundUpdate} />
    </div>
  );
}
