import { requireStaff } from "@/lib/auth";
import { AdminNav } from "@/components/admin/nav";

export default async function AdminLayout({ children }: { children: React.ReactNode }) {
  const profile = await requireStaff();

  return (
    <div className="flex min-h-full flex-1 flex-col">
      <AdminNav profile={profile} />
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8">{children}</main>
    </div>
  );
}
