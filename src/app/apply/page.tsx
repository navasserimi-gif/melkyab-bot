import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { ApplicationForm } from "@/components/apply/application-form";

export default async function ApplyPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) redirect("/login?next=/apply");

  const { data: existing } = await supabase
    .from("applicants")
    .select("id")
    .eq("user_id", user.id)
    .maybeSingle();

  if (existing) redirect("/portal");

  return (
    <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col px-4 py-12">
      <div className="mb-8 text-center">
        <p className="text-sm font-medium tracking-wide text-slate-500 uppercase">
          Mietinteressenten-Formular
        </p>
        <p className="text-xs font-medium tracking-wide text-slate-400" dir="rtl" lang="fa">
          فرم متقاضیان اجاره مسکن
        </p>
        <h1 className="mt-2 text-2xl font-semibold text-slate-900">Dein Suchprofil</h1>
        <h2 className="text-lg font-semibold text-slate-500" dir="rtl" lang="fa">
          پروفایل جستجوی شما
        </h2>
        <p className="mt-2 text-sm text-slate-500">
          Ein paar kurze Schritte — danach lädst du direkt deine Unterlagen hoch.
        </p>
        <p className="text-sm text-slate-400" dir="rtl" lang="fa">
          چند مرحله کوتاه — سپس می‌توانید مدارک خود را مستقیماً بارگذاری کنید.
        </p>
      </div>
      <ApplicationForm defaultEmail={user.email ?? ""} />
    </main>
  );
}
