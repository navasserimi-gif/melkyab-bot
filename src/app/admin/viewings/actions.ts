"use server";

import { revalidatePath } from "next/cache";
import { createClient } from "@/lib/supabase/server";
import { requireStaff } from "@/lib/auth";

export interface ProposeTimeResult {
  ok?: true;
  error?: string;
}

/** Admin/Makler schlägt einen Besichtigungstermin vor (§15). */
export async function proposeViewingTime(
  viewingId: string,
  formData: FormData,
): Promise<ProposeTimeResult> {
  await requireStaff();
  const supabase = await createClient();

  const scheduledAt = String(formData.get("scheduled_at") ?? "");
  if (!scheduledAt) return { error: "Bitte Datum und Uhrzeit angeben." };

  const { data: viewing, error } = await supabase
    .from("viewings")
    .update({ scheduled_at: new Date(scheduledAt).toISOString(), status: "geplant", confirmed_at: null })
    .eq("id", viewingId)
    .select("property_id, applicant_id")
    .single();
  if (error) return { error: error.message };

  await supabase.rpc("emit_event", {
    p_type: "VIEWING_CREATED",
    p_payload: { viewing_id: viewingId, property_id: viewing.property_id, applicant_id: viewing.applicant_id },
  });

  revalidatePath("/admin/viewings");
  revalidatePath("/admin/dashboard");
  return { ok: true };
}

export async function cancelViewing(viewingId: string) {
  await requireStaff();
  const supabase = await createClient();

  const { error } = await supabase.from("viewings").update({ status: "abgesagt" }).eq("id", viewingId);
  if (error) throw new Error(error.message);

  revalidatePath("/admin/viewings");
  revalidatePath("/admin/dashboard");
}
