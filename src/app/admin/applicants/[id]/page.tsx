import { notFound } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { getCurrentProfile } from "@/lib/auth";
import { ApplicantForm } from "@/components/admin/applicant-form";
import { updateApplicant, deleteApplicant } from "../actions";

export default async function ApplicantDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const supabase = await createClient();
  const profile = await getCurrentProfile();

  const [{ data: applicant }, { data: statuses }, { data: history }] = await Promise.all([
    supabase.from("applicants").select("*").eq("id", id).single(),
    supabase.from("status_definitions").select("*").order("sort_order"),
    supabase
      .from("applicant_status_history")
      .select("*")
      .eq("applicant_id", id)
      .order("changed_at", { ascending: false })
      .limit(20),
  ]);

  if (!applicant) notFound();

  const boundUpdate = updateApplicant.bind(null, id);
  const boundDelete = deleteApplicant.bind(null, id);

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <p className="font-mono text-xs text-slate-400">{applicant.internal_code}</p>
          <h1 className="mt-1 text-2xl font-semibold text-slate-900">
            {applicant.first_name} {applicant.last_name}
          </h1>
        </div>
        {profile?.role === "admin" && (
          <form
            action={boundDelete}
          >
            <button
              type="submit"
              className="rounded-lg border border-red-200 px-4 py-2 text-sm font-medium text-red-600 hover:bg-red-50"
            >
              Interessent löschen
            </button>
          </form>
        )}
      </div>

      <ApplicantForm applicant={applicant} statusOptions={statuses ?? []} action={boundUpdate} />

      {history && history.length > 0 && (
        <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="text-sm font-semibold text-slate-900">Statusverlauf</h2>
          <ul className="mt-3 space-y-2">
            {history.map((h) => (
              <li key={h.id} className="text-sm text-slate-600">
                <span className="text-slate-400">
                  {new Date(h.changed_at).toLocaleString("de-DE")}
                </span>{" "}
                — {h.old_status ?? "–"} → <span className="font-medium">{h.new_status}</span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
