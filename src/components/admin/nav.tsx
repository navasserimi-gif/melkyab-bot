"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { logout } from "@/app/(auth)/actions";
import type { Profile } from "@/types/models";

const LINKS = [
  { href: "/admin/dashboard", label: "Dashboard" },
  { href: "/admin/applicants", label: "Interessenten" },
  { href: "/admin/properties", label: "Wohnungen" },
  { href: "/admin/viewings", label: "Besichtigungen" },
];

export function AdminNav({ profile }: { profile: Profile }) {
  const pathname = usePathname();

  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
        <div className="flex items-center gap-8">
          <span className="text-sm font-semibold tracking-tight text-slate-900">
            Mietwohnungs-CRM
          </span>
          <nav className="flex items-center gap-1">
            {LINKS.map((link) => {
              const active = pathname.startsWith(link.href);
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`rounded-md px-3 py-1.5 text-sm font-medium transition ${
                    active ? "bg-slate-900 text-white" : "text-slate-600 hover:bg-slate-100"
                  }`}
                >
                  {link.label}
                </Link>
              );
            })}
          </nav>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-sm text-slate-500">
            {profile.full_name ?? profile.email} ·{" "}
            <span className="uppercase">{profile.role}</span>
          </span>
          <form action={logout}>
            <button
              type="submit"
              className="rounded-md border border-slate-300 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50"
            >
              Abmelden
            </button>
          </form>
        </div>
      </div>
    </header>
  );
}
