"use client";

import { useState } from "react";
import type { Property } from "@/types/models";

const FIELD =
  "mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-slate-500 focus:ring-1 focus:ring-slate-500 focus:outline-none";
const LABEL = "block text-sm font-medium text-slate-700";

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <fieldset className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <legend className="px-1 text-sm font-semibold text-slate-900">{title}</legend>
      <div className="mt-3 grid grid-cols-1 gap-4 sm:grid-cols-2">{children}</div>
    </fieldset>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className={LABEL}>
      {label}
      {children}
    </label>
  );
}

const AMENITIES: { key: keyof Property; label: string }[] = [
  { key: "has_balcony", label: "Balkon" },
  { key: "has_terrace", label: "Terrasse" },
  { key: "has_garden", label: "Garten" },
  { key: "has_elevator", label: "Aufzug" },
  { key: "has_parking_space", label: "Stellplatz" },
  { key: "has_garage", label: "Garage" },
  { key: "has_cellar", label: "Keller" },
  { key: "pets_allowed", label: "Haustiere erlaubt" },
];

export function PropertyForm({
  property,
  action,
}: {
  property?: Property;
  action: (formData: FormData) => void;
}) {
  const [pending, setPending] = useState(false);
  const p = property;

  return (
    <form action={action} onSubmit={() => setPending(true)} className="space-y-6">
      <Section title="Objekt">
        <Field label="Externe Wohnungs-ID">
          <input name="external_id" defaultValue={p?.external_id ?? ""} className={FIELD} />
        </Field>
        <Field label="Wohnungsgesellschaft">
          <input name="company" defaultValue={p?.company ?? ""} className={FIELD} />
        </Field>
        <Field label="Objekt">
          <input name="object_name" defaultValue={p?.object_name ?? ""} className={FIELD} />
        </Field>
        <Field label="Status">
          <select name="status" defaultValue={p?.status ?? "entwurf"} className={FIELD}>
            <option value="entwurf">Entwurf</option>
            <option value="veroeffentlicht">Veröffentlicht</option>
            <option value="reserviert">Reserviert</option>
            <option value="vermietet">Vermietet</option>
            <option value="archiviert">Archiviert</option>
          </select>
        </Field>
      </Section>

      <Section title="Adresse">
        <Field label="Straße">
          <input name="street" defaultValue={p?.street ?? ""} className={FIELD} />
        </Field>
        <Field label="Hausnummer">
          <input name="house_number" defaultValue={p?.house_number ?? ""} className={FIELD} />
        </Field>
        <Field label="PLZ">
          <input name="postal_code" defaultValue={p?.postal_code ?? ""} className={FIELD} />
        </Field>
        <Field label="Ort">
          <input name="city" defaultValue={p?.city ?? ""} className={FIELD} />
        </Field>
        <Field label="Stadtteil">
          <input name="district" defaultValue={p?.district ?? ""} className={FIELD} />
        </Field>
        <Field label="Etage">
          <input name="floor" defaultValue={p?.floor ?? ""} className={FIELD} />
        </Field>
      </Section>

      <Section title="Eckdaten">
        <Field label="Zimmer">
          <input name="rooms" type="number" step="0.5" min={0} defaultValue={p?.rooms ?? ""} className={FIELD} />
        </Field>
        <Field label="Wohnfläche (m²)">
          <input name="living_area" type="number" min={0} defaultValue={p?.living_area ?? ""} className={FIELD} />
        </Field>
        <Field label="Kaltmiete (€)">
          <input name="cold_rent" type="number" min={0} defaultValue={p?.cold_rent ?? ""} className={FIELD} />
        </Field>
        <Field label="Nebenkosten (€)">
          <input
            name="ancillary_costs"
            type="number"
            min={0}
            defaultValue={p?.ancillary_costs ?? ""}
            className={FIELD}
          />
        </Field>
        <Field label="Heizkosten (€)">
          <input name="heating_costs" type="number" min={0} defaultValue={p?.heating_costs ?? ""} className={FIELD} />
        </Field>
        <Field label="Kaution (€)">
          <input name="deposit" type="number" min={0} defaultValue={p?.deposit ?? ""} className={FIELD} />
        </Field>
        <Field label="Einzugsdatum">
          <input name="move_in_date" type="date" defaultValue={p?.move_in_date ?? ""} className={FIELD} />
        </Field>
      </Section>

      <Section title="Ausstattung">
        {AMENITIES.map((a) => (
          <label key={a.key} className="flex items-center gap-2 text-sm text-slate-700">
            <input type="checkbox" name={a.key} defaultChecked={Boolean(p?.[a.key])} />
            {a.label}
          </label>
        ))}
      </Section>

      <Section title="Beschreibung">
        <Field label="Energieinformationen">
          <input name="energy_info" defaultValue={p?.energy_info ?? ""} className={FIELD} />
        </Field>
        <div className="sm:col-span-2">
          <label className={LABEL}>
            Beschreibung
            <textarea name="description" defaultValue={p?.description ?? ""} rows={4} className={FIELD} />
          </label>
        </div>
        <div className="sm:col-span-2">
          <label className={LABEL}>
            Interne Notizen
            <textarea name="internal_notes" defaultValue={p?.internal_notes ?? ""} rows={2} className={FIELD} />
          </label>
        </div>
      </Section>

      {!p && (
        <Section title="Bilder (optional)">
          <div className="sm:col-span-2">
            <label className={LABEL}>
              Fotos direkt mit anlegen — Kategorien (Titelbild, Grundriss, …) kannst du danach auf
              der Wohnungsseite noch zuordnen.
              <input
                type="file"
                name="images"
                accept="image/*"
                multiple
                className="mt-1 block w-full text-sm"
              />
            </label>
          </div>
        </Section>
      )}

      <div className="flex justify-end gap-3">
        <button
          type="submit"
          disabled={pending}
          className="rounded-lg bg-slate-900 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-slate-700 disabled:opacity-60"
        >
          {pending ? "Speichern…" : p ? "Änderungen speichern" : "Wohnung anlegen"}
        </button>
      </div>
    </form>
  );
}
