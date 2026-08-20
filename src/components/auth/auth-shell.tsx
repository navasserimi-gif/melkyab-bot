import Image from "next/image";
import { AUTH_PANEL_IMAGE_URL } from "@/lib/media";

export function AuthShell({ children }: { children: React.ReactNode }) {
  return (
    <main className="flex flex-1">
      <div className="relative hidden w-1/2 lg:block">
        <Image
          src={AUTH_PANEL_IMAGE_URL}
          alt="Modernes Wohnzimmer"
          fill
          priority
          sizes="50vw"
          className="object-cover"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-slate-950/70 via-slate-950/10 to-transparent" />
        <div className="absolute bottom-10 left-10 right-10 text-white">
          <p className="text-sm font-semibold tracking-wide text-emerald-300 uppercase">
            Mietwohnungs-CRM
          </p>
          <p className="mt-2 text-2xl font-semibold">
            Vom Suchprofil bis zur Wohnungsübergabe.
          </p>
        </div>
      </div>
      <div className="flex flex-1 items-center justify-center px-4 py-16">{children}</div>
    </main>
  );
}
