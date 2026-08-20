import { createClient } from "@/lib/supabase/server";
import { ProposeViewingForm } from "@/components/admin/propose-viewing-form";
import { cancelViewing } from "./actions";

const STATUS_LABEL: Record<string, string> = {
  angefragt: "Angefragt",
  geplant: "Termin vorgeschlagen",
  durchgefuehrt: "Durchgeführt",
  abgesagt: "Abgesagt",
  verschoben: "Verschoben",
};

interface ViewingRow {
  id: string;
  status: string;
  scheduled_at: string | null;
  confirmed_at: string | null;
  property: { internal_code: string; object_name: string | null; city: string | null } | null;
  applicant: { internal_code: string; first_name: string; last_name: string } | null;
}

export default async function AdminViewingsPage() {
  const supabase = await createClient();
  const { data } = await supabase
    .from("viewings")
    .select(
      "id, status, scheduled_at, confirmed_at, property:properties(internal_code, object_name, city), applicant:applicants(internal_code, first_name, last_name)",
    )
    .order("created_at", { ascending: false })
    .limit(200);

  const viewings: ViewingRow[] = (data ?? []).map((v) => ({
    id: v.id,
    status: v.status,
    scheduled_at: v.scheduled_at,
    confirmed_at: v.confirmed_at,
    property: Array.isArray(v.property) ? (v.property[0] ?? null) : v.property,
    applicant: Array.isArray(v.applicant) ? (v.applicant[0] ?? null) : v.applicant,
  }));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Besichtigungen</h1>
        <p className="mt-1 text-sm text-slate-500">{viewings.length} Anfragen/Termine</p>
      </div>

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-slate-200 bg-slate-50 text-xs tracking-wide text-slate-500 uppercase">
            <tr>
              <th className="px-4 py-3">Wohnung</th>
              <th className="px-4 py-3">Interessent</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Termin</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {viewings.map((v) => (
              <tr key={v.id}>
                <td className="px-4 py-3 text-slate-700">
                  {v.property?.object_name ?? v.property?.internal_code ?? "–"}
                  <span className="ml-1 text-slate-400">{v.property?.city ?? ""}</span>
                </td>
                <td className="px-4 py-3 text-slate-700">
                  {v.applicant ? `${v.applicant.first_name} ${v.applicant.last_name}` : "–"}
                  <span className="ml-1 font-mono text-xs text-slate-400">
                    {v.applicant?.internal_code}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700">
                    {STATUS_LABEL[v.status] ?? v.status}
                  </span>
                  {v.confirmed_at && (
                    <span className="ml-2 rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-700">
                      Bestätigt
                    </span>
                  )}
                </td>
                <td className="px-4 py-3 text-slate-500">
                  {v.scheduled_at
                    ? new Date(v.scheduled_at).toLocaleString("de-DE", {
                        dateStyle: "medium",
                        timeStyle: "short",
                      })
                    : "–"}
                </td>
                <td className="px-4 py-3">
                  {v.status !== "abgesagt" && v.status !== "durchgefuehrt" && (
                    <div className="flex flex-col gap-2">
                      <ProposeViewingForm viewingId={v.id} />
                      <form action={cancelViewing.bind(null, v.id)}>
                        <button type="submit" className="text-xs text-red-500 hover:underline">
                          Absagen
                        </button>
                      </form>
                    </div>
                  )}
                </td>
              </tr>
            ))}
            {viewings.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-10 text-center text-sm text-slate-400">
                  Noch keine Besichtigungsanfragen.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
