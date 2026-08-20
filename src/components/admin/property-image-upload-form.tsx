"use client";

import { useState } from "react";
import { compressImageFile } from "@/lib/image-compress";

const CATEGORY_LABEL: Record<string, string> = {
  titelbild: "Titelbild",
  wohnzimmer: "Wohnzimmer",
  schlafzimmer: "Schlafzimmer",
  kueche: "Küche",
  bad: "Badezimmer",
  balkon: "Balkon",
  grundriss: "Grundriss",
  sonstige: "Weitere Bilder",
};

export function PropertyImageUploadForm({ action }: { action: (formData: FormData) => void }) {
  const [optimizing, setOptimizing] = useState(false);

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const input = e.target;
    const file = input.files?.[0];
    if (!file) return;

    setOptimizing(true);
    const dt = new DataTransfer();
    dt.items.add(await compressImageFile(file));
    input.files = dt.files;
    setOptimizing(false);
  }

  return (
    <form
      action={action}
      onSubmit={(e) => {
        if (optimizing) e.preventDefault();
      }}
      className="mt-5 flex flex-wrap items-end gap-3 border-t border-slate-100 pt-4"
    >
      <div>
        <label className="block text-sm font-medium text-slate-700">Bild</label>
        <input
          type="file"
          name="file"
          accept="image/*"
          required
          onChange={handleFileChange}
          className="mt-1 text-sm"
        />
        <p className="mt-1 text-xs text-slate-400">Wird automatisch verkleinert (max. 8 MB).</p>
      </div>
      <div>
        <label className="block text-sm font-medium text-slate-700">Kategorie</label>
        <select name="category" className="mt-1 rounded-lg border border-slate-300 px-3 py-2 text-sm">
          {Object.entries(CATEGORY_LABEL).map(([key, label]) => (
            <option key={key} value={key}>
              {label}
            </option>
          ))}
        </select>
      </div>
      <button
        type="submit"
        disabled={optimizing}
        className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-60"
      >
        {optimizing ? "Bild wird optimiert…" : "Hochladen"}
      </button>
    </form>
  );
}
