import { getCurrentProfile } from "@/lib/auth";
import { redirect } from "next/navigation";
import { logout } from "../(auth)/actions";

export default async function PortalPage() {
  const profile = await getCurrentProfile();
  if (!profile) redirect("/login");
  if (profile.role === "admin" || profile.role === "makler") redirect("/admin");

  return (
    <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col px-4 py-16">
      <div className="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <h1 className="text-xl font-semibold text-slate-900">
          Willkommen, {profile.full_name ?? profile.email}
        </h1>
        <p className="mt-2 text-sm text-slate-600">
          Dein Interessentenprofil, passende Wohnungen, Besichtigungen und Dokumente findest du
          hier, sobald das mehrstufige Bewerbungsformular (Phase 2) freigeschaltet ist.
        </p>
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
