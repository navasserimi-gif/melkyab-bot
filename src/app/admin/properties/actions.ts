"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { requireAdmin } from "@/lib/auth";
import type { ImageCategory, Property } from "@/types/models";
import { computeAndAutoSendMatches } from "@/lib/matching/auto-match";

type PropertyInput = Omit<
  Property,
  "id" | "internal_code" | "created_at" | "updated_at" | "created_by" | "warm_rent"
>;

function parsePropertyForm(formData: FormData): Partial<PropertyInput> {
  const str = (key: string) => {
    const v = formData.get(key);
    return v === null || v === "" ? null : String(v);
  };
  const num = (key: string) => {
    const v = formData.get(key);
    if (v === null || v === "") return null;
    const n = Number(v);
    return Number.isFinite(n) ? n : null;
  };
  const bool = (key: string) => formData.get(key) === "on";

  return {
    external_id: str("external_id"),
    company: str("company"),
    object_name: str("object_name"),
    street: str("street"),
    house_number: str("house_number"),
    postal_code: str("postal_code"),
    city: str("city"),
    district: str("district"),
    floor: str("floor"),
    rooms: num("rooms"),
    living_area: num("living_area"),
    cold_rent: num("cold_rent"),
    ancillary_costs: num("ancillary_costs"),
    heating_costs: num("heating_costs"),
    deposit: num("deposit"),
    move_in_date: str("move_in_date"),
    has_balcony: bool("has_balcony"),
    has_terrace: bool("has_terrace"),
    has_garden: bool("has_garden"),
    has_elevator: bool("has_elevator"),
    has_parking_space: bool("has_parking_space"),
    has_garage: bool("has_garage"),
    has_cellar: bool("has_cellar"),
    pets_allowed: bool("pets_allowed"),
    energy_info: str("energy_info"),
    description: str("description"),
    status: (str("status") ?? "entwurf") as PropertyInput["status"],
    internal_notes: str("internal_notes"),
  };
}

export async function createProperty(formData: FormData) {
  await requireAdmin();
  const supabase = await createClient();
  const input = parsePropertyForm(formData);

  const { data, error } = await supabase.from("properties").insert(input).select("id").single();
  if (error) throw new Error(error.message);

  const images = formData
    .getAll("images")
    .filter((f): f is File => f instanceof File && f.size > 0 && f.size <= 8 * 1024 * 1024);
  for (const [index, file] of images.entries()) {
    const safeName = file.name.replace(/[^a-zA-Z0-9._-]/g, "_");
    const path = `${data.id}/${crypto.randomUUID()}-${safeName}`;
    const { error: uploadError } = await supabase.storage
      .from("property-images")
      .upload(path, file, { contentType: file.type || undefined });
    if (uploadError) continue;
    await supabase
      .from("property_images")
      .insert({ property_id: data.id, storage_path: path, category: "sonstige", sort_order: index });
  }

  await supabase.rpc("emit_event", {
    p_type: "PROPERTY_CREATED",
    p_payload: { property_id: data.id },
  });

  if (input.status === "veroeffentlicht") {
    const { data: property } = await supabase.from("properties").select("*").eq("id", data.id).single();
    if (property) await computeAndAutoSendMatches(supabase, property as Property);
  }

  revalidatePath("/admin/properties");
  redirect(`/admin/properties/${data.id}`);
}

export async function updateProperty(id: string, formData: FormData) {
  const admin = await requireAdmin();
  const supabase = await createClient();
  const input = parsePropertyForm(formData);

  const { data: current } = await supabase.from("properties").select("status").eq("id", id).single();

  const { error } = await supabase.from("properties").update(input).eq("id", id);
  if (error) throw new Error(error.message);

  if (current?.status !== "veroeffentlicht" && input.status === "veroeffentlicht") {
    await supabase.rpc("emit_event", {
      p_type: "PROPERTY_PUBLISHED",
      p_payload: { property_id: id, published_by: admin.id },
    });

    const { data: property } = await supabase.from("properties").select("*").eq("id", id).single();
    if (property) await computeAndAutoSendMatches(supabase, property as Property);
  }

  revalidatePath("/admin/properties");
  revalidatePath(`/admin/properties/${id}`);
  revalidatePath("/admin/dashboard");
}

export async function deleteProperty(id: string) {
  await requireAdmin();
  const supabase = await createClient();
  const { error } = await supabase.from("properties").delete().eq("id", id);
  if (error) throw new Error(error.message);

  revalidatePath("/admin/properties");
  redirect("/admin/properties");
}

export async function uploadPropertyImage(propertyId: string, formData: FormData) {
  await requireAdmin();
  const supabase = await createClient();

  const file = formData.get("file");
  const category = String(formData.get("category") ?? "sonstige") as ImageCategory;
  if (!(file instanceof File) || file.size === 0) {
    throw new Error("Bitte eine Bilddatei auswählen.");
  }
  if (file.size > 8 * 1024 * 1024) {
    throw new Error("Bild ist zu groß (max. 8 MB).");
  }

  const safeName = file.name.replace(/[^a-zA-Z0-9._-]/g, "_");
  const path = `${propertyId}/${crypto.randomUUID()}-${safeName}`;

  const { error: uploadError } = await supabase.storage
    .from("property-images")
    .upload(path, file, { contentType: file.type || undefined });
  if (uploadError) throw new Error(uploadError.message);

  const { error: insertError } = await supabase
    .from("property_images")
    .insert({ property_id: propertyId, storage_path: path, category });
  if (insertError) throw new Error(insertError.message);

  revalidatePath(`/admin/properties/${propertyId}`);
}

export async function deletePropertyImage(propertyId: string, imageId: string, storagePath: string) {
  await requireAdmin();
  const supabase = await createClient();

  await supabase.storage.from("property-images").remove([storagePath]);
  const { error } = await supabase.from("property_images").delete().eq("id", imageId);
  if (error) throw new Error(error.message);

  revalidatePath(`/admin/properties/${propertyId}`);
}

export interface SendOfferResult {
  ok?: true;
  error?: string;
}

/** Sendet ein Wohnungsangebot (Exposé) an einen registrierten Interessenten (§13). */
export async function sendPropertyOffer(
  propertyId: string,
  formData: FormData,
): Promise<SendOfferResult> {
  await requireAdmin();
  const supabase = await createClient();

  const applicantId = String(formData.get("applicant_id") ?? "");
  if (!applicantId) return { error: "Bitte einen Interessenten auswählen." };

  const { data, error } = await supabase
    .from("property_offers")
    .insert({ property_id: propertyId, applicant_id: applicantId, sent_via: "portal" })
    .select("id")
    .single();
  if (error) return { error: error.message };

  await supabase
    .from("applicants")
    .update({ status_key: "wohnung_angeboten" })
    .eq("id", applicantId);

  await supabase.rpc("emit_event", {
    p_type: "PROPERTY_OFFERED",
    p_payload: { property_id: propertyId, applicant_id: applicantId, offer_id: data.id },
  });

  revalidatePath(`/admin/properties/${propertyId}`);
  revalidatePath("/portal");
  return { ok: true };
}
