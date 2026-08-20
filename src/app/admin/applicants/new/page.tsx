import { createClient } from "@/lib/supabase/server";
import { ApplicantForm } from "@/components/admin/applicant-form";
import { createApplicant } from "../actions";

export default async function NewApplicantPage() {
  const supabase = await createClient();
  const { data: statuses } = await supabase.from("status_definitions").select("*").order("sort_order");

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Neuer Interessent</h1>
        <p className="mt-1 text-sm text-slate-500">
          Die interne ID wird automatisch vergeben (INT-XXXXXXX).
        </p>
      </div>
      <ApplicantForm statusOptions={statuses ?? []} action={createApplicant} />
    </div>
  );
}
