import Link from "next/link";
import { redirect } from "next/navigation";
import { getCurrentProfile } from "@/lib/auth";
import { createClient } from "@/lib/supabase/server";
import { DocumentUploadStep } from "@/components/apply/document-upload-step";

export default async function PortalDocumentsPage() {
  const profile = await getCurrentProfile();
  if (!profile) redirect("/login");
  if (profile.role === "admin" || profile.role === "makler") redirect("/admin");

  const supabase = await createClient();
  const { data: applicant } = await supabase
    .from("applicants")
    .select("id")
    .eq("user_id", profile.id)
    .maybeSingle();

  if (!applicant) redirect("/apply");

  const [{ data: docTypes }, { data: uploadedDocs }] = await Promise.all([
    supabase
      .from("document_types")
      .select("key, label")
      .eq("is_active", true)
      .eq("required", true)
      .order("sort_order"),
    supabase.from("applicant_documents").select("doc_type_key").eq("applicant_id", applicant.id),
  ]);

  const uploadedKeys = Array.from(new Set((uploadedDocs ?? []).map((d) => d.doc_type_key)));

  return (
    <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col px-4 py-12">
      <div className="mb-6">
        <Link href="/portal" className="text-sm text-slate-500 hover:underline">
          ← Zurück zur Übersicht
        </Link>
        <h1 className="mt-2 text-2xl font-semibold text-slate-900">Deine Dokumente</h1>
        <h2 className="text-base font-semibold text-slate-400" dir="rtl" lang="fa">
          مدارک شما
        </h2>
        <p className="mt-1 text-sm text-slate-500">
          Du kannst Dokumente jederzeit ergänzen oder ersetzen.
        </p>
      </div>

      <DocumentUploadStep
        applicantId={applicant.id}
        requiredTypes={(docTypes ?? []).map((d) => ({ key: d.key, label: d.label }))}
        uploadedKeys={uploadedKeys}
        finishHref="/portal"
        finishLabel="Fertig — zurück zur Übersicht"
        finishLabelFa="پایان — بازگشت به نمای کلی"
      />
    </main>
  );
}
