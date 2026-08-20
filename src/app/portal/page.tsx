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

export default async function PortalPage() {
  const profile = await getCurrentProfile();
  if (!profile) redirect("/login");
  if (profile.role === "admin" || profile.role === "makler") redirect("/admin");

  const supabase = await createClient();
  const { data: applicant } = await supabase
    .from("applicants")
    .select("internal_code, status_key, has_schufa, has_income_proof, has_debt_clearance_cert")
    .eq("user_id", profile.id)
    .maybeSingle();

  const missingDocs = applicant
    ? [
        !applicant.has_schufa && "Schufa-Auskunft",
        !applicant.has_income_proof && "Lohn-/Gehaltsabrechnung",
      ].filter(Boolean)
    : [];

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

            <p className="text-sm text-slate-500">
              Passende Wohnungen, Besichtigungen und Angebote folgen hier, sobald sie verfügbar
              sind.
            </p>
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
