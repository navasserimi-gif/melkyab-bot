import Image from "next/image";
import { AUTH_PANEL_IMAGE_URL } from "@/lib/media";

export default function PortalLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="relative flex min-h-full flex-1 flex-col">
      <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
        <Image
          src={AUTH_PANEL_IMAGE_URL}
          alt=""
          fill
          sizes="100vw"
          className="object-cover opacity-[0.22]"
        />
        <div className="absolute inset-0 bg-gradient-to-b from-slate-50/20 via-slate-50/45 to-slate-50" />
      </div>
      {children}
    </div>
  );
}
