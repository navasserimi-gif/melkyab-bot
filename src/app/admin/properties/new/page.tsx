import { PropertyForm } from "@/components/admin/property-form";
import { createProperty } from "../actions";

export default function NewPropertyPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Neue Wohnung</h1>
        <p className="mt-1 text-sm text-slate-500">
          Die interne ID wird automatisch vergeben (WHG-XXXXX). Bilder können nach dem Anlegen
          hochgeladen werden.
        </p>
      </div>
      <PropertyForm action={createProperty} />
    </div>
  );
}
