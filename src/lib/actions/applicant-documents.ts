"use server";

import { revalidatePath } from "next/cache";
import { createClient } from "@/lib/supabase/server";

const FLAG_BY_DOC_TYPE: Record<string, "has_schufa" | "has_income_proof" | "has_debt_clearance_cert"> = {
  schufa: "has_schufa",
  einkommensnachweis: "has_income_proof",
  mietschuldenfreiheit: "has_debt_clearance_cert",
};

export interface UploadDocumentResult {
  ok?: true;
  error?: string;
}

/**
 * Lädt ein Dokument für den EIGENEN Interessenten-Datensatz hoch (Self-Service,
 * §17). Storage-RLS und die RLS-Policy auf applicant_documents stellen sicher,
 * dass hier nur der zugehörige Nutzer (oder Staff) schreiben kann.
 */
export async function uploadApplicantDocument(formData: FormData): Promise<UploadDocumentResult> {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return { error: "Bitte zuerst anmelden." };

  const applicantId = String(formData.get("applicant_id") ?? "");
  const docTypeKey = String(formData.get("doc_type_key") ?? "");
  const file = formData.get("file");

  if (!applicantId || !docTypeKey) return { error: "Fehlende Angaben." };
  if (!(file instanceof File) || file.size === 0) {
    return { error: "Bitte eine Datei auswählen." };
  }
  if (file.size > 15 * 1024 * 1024) {
    return { error: "Datei ist zu groß (max. 15 MB)." };
  }

  const safeName = file.name.replace(/[^a-zA-Z0-9._-]/g, "_");
  const path = `${applicantId}/${crypto.randomUUID()}-${safeName}`;

  const { error: uploadError } = await supabase.storage
    .from("applicant-documents")
    .upload(path, file, { contentType: file.type || undefined });
  if (uploadError) return { error: uploadError.message };

  const { error: insertError } = await supabase.from("applicant_documents").insert({
    applicant_id: applicantId,
    doc_type_key: docTypeKey,
    storage_path: path,
    uploaded_by: user.id,
  });
  if (insertError) return { error: insertError.message };

  const flagColumn = FLAG_BY_DOC_TYPE[docTypeKey];
  if (flagColumn) {
    await supabase
      .from("applicants")
      .update({ [flagColumn]: true })
      .eq("id", applicantId);
  }

  await supabase.rpc("emit_event", {
    p_type: "DOCUMENT_UPLOADED",
    p_payload: { applicant_id: applicantId, doc_type_key: docTypeKey },
  });

  revalidatePath("/portal");
  revalidatePath("/portal/documents");

  return { ok: true };
}
