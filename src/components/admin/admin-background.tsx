"use client";

import { usePathname } from "next/navigation";
import Image from "next/image";
import { ADMIN_SECTION_BACKGROUNDS } from "@/lib/media";

export function AdminBackground() {
  const pathname = usePathname();
  const match = ADMIN_SECTION_BACKGROUNDS.find((s) => pathname.startsWith(s.prefix));
  if (!match) return null;

  return (
    <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
      <Image
        src={match.url}
        alt=""
        fill
        sizes="100vw"
        className="object-cover"
        style={{ opacity: match.opacity ?? 0.07 }}
      />
      <div className="absolute inset-0 bg-gradient-to-b from-slate-50/40 via-slate-50/70 to-slate-50" />
    </div>
  );
}
