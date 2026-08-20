import Link from "next/link";
import { redirect } from "next/navigation";
import { getCurrentProfile } from "@/lib/auth";
import { createClient } from "@/lib/supabase/server";
import { logout } from "../(auth)/actions";

const STATUS_LABEL: Record<string, string> = {
  neu: "Neu",
  formular_ausgefuellt: "Formular ausgefüllt",
  vorgeprueft: "Vorgeprüft",
  unterlagen_unvollstaendig: "Unterlagen unvollständig",
  unterlagen_vollstaendig: "Unterlagen vollständig",
  passende_wohnung_gefunden: "Passende Wohnung gefunden",
  wohnung_angeboten: "Wohnung angeboten",
  interesse_bestaetigt: "Interesse bestätigt",
  besichtigung_angefragt: "Besichtigung angefragt",
  besichtigung_geplant: "Besichtigung geplant",
  besichtigung_durchgefuehrt: "Besichtigung durchgeführt",
  wohnung_gewuenscht: "Wohnung gewünscht",
  bewerbung_uebermittelt: "Bewerbung übermittelt",
  vermietet: "Vermietet",
  abgesagt: "Abgesagt",
  abgeschlossen: "Abgeschlossen",
};

const REQUIRED_DOC_LABELS: Record<string, string> = {
  schufa: "Schufa-Auskunft",
  einkommensnachweis: "Lohn-/Gehaltsabrechnung",
  ausweis: "Personalausweis",
};

export default async function PortalPage() {
  const profile = await getCurrentProfile();
  if (!profile) redirect("/login");
  if (profile.role === "admin" || profile.role === "makler") redirect("/admin");

  const supabase = await createClient();
  const { data: applicant } = await supabase
    .from("applicants")
    .select("id, internal_code, status_key")
    .eq("user_id", profile.id)
    .maybeSingle();

  let missingDocs: string[] = [];
  let offers: { id: string; response: string; property: { internal_code: string; object_name: string | null; city: string | null } | null }[] = [];

  if (applicant) {
    const [{ data: uploadedDocs }, { data: offerRows }] = await Promise.all([
      supabase.from("applicant_documents").select("doc_type_key").eq("applicant_id", applicant.id),
      supabase
        .from("property_offers")
        .select("id, response, property:properties(internal_code, object_name, city)")
        .eq("applicant_id", applicant.id)
        .order("sent_at", { ascending: false }),
    ]);

    const uploadedKeys = new Set((uploadedDocs ?? []).map((d) => d.doc_type_key));
    missingDocs = Object.entries(REQUIRED_DOC_LABELS)
      .filter(([key]) => !uploadedKeys.has(key))
      .map(([, label]) => label);

    offers = (offerRows ?? []).map((o) => ({
      id: o.id,
      response: o.response,
      property: Array.isArray(o.property) ? (o.property[0] ?? null) : o.property,
    }));
  }

  return (
    <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col px-4 py-16">
      <div className="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <h1 className="text-xl font-semibold text-slate-900">
          Willkommen, {profile.full_name ?? profile.email}
        </h1>

        {applicant ? (
          <div className="mt-4 space-y-4">
            <p className="text-sm text-slate-500">
              Interessenten-ID: <span className="font-mono">{applicant.internal_code}</span>
            </p>
            <p className="text-sm text-slate-600">
              Status:{" "}
              <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700">
                {STATUS_LABEL[applicant.status_key] ?? applicant.status_key}
              </span>
            </p>

            {missingDocs.length > 0 ? (
              <p className="rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-800">
                Es fehlen noch Unterlagen: {missingDocs.join(", ")}.
              </p>
            ) : (
              <p className="rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
                Alle wichtigen Unterlagen sind hochgeladen.
              </p>
            )}

            <Link
              href="/portal/documents"
              className="inline-block rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700"
            >
              Dokumente verwalten
            </Link>

            {offers.length > 0 && (
              <div>
                <h2 className="text-sm font-semibold text-slate-900">Deine Wohnungsangebote</h2>
                <ul className="mt-2 space-y-2">
                  {offers.map((offer) => (
                    <li key={offer.id}>
                      <Link
                        href={`/portal/offers/${offer.id}`}
                        className="flex items-center justify-between rounded-lg border border-slate-200 px-3 py-2 text-sm hover:bg-slate-50"
                      >
                        <span>
                          {offer.property?.object_name ?? offer.property?.internal_code}
                          {offer.property?.city ? ` · ${offer.property.city}` : ""}
                        </span>
                        <span className="text-xs text-slate-400">
                          {offer.response === "offen" ? "Neu" : offer.response}
                        </span>
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        ) : (
          <div className="mt-4 space-y-4">
            <p className="text-sm text-slate-600">
              Du hast noch kein Suchprofil angelegt. Fülle das kurze Formular aus, damit wir
              passende Wohnungen für dich finden können.
            </p>
            <Link
              href="/apply"
              className="inline-block rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700"
            >
              Suchprofil anlegen
            </Link>
          </div>
        )}

        <form action={logout} className="mt-6">
          <button
            type="submit"
            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            Abmelden
          </button>
        </form>
      </div>
    </main>
  );
}
