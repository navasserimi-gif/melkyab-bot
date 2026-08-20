"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { requireStaff, requireAdmin } from "@/lib/auth";
import type { Applicant } from "@/types/models";

type ApplicantInput = Omit<
  Applicant,
  "id" | "internal_code" | "created_at" | "updated_at" | "user_id" | "assigned_to"
>;

function parseApplicantForm(formData: FormData): Partial<ApplicantInput> {
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
  const districts = String(formData.get("desired_districts") ?? "")
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);

  return {
    first_name: String(formData.get("first_name") ?? "").trim(),
    last_name: String(formData.get("last_name") ?? "").trim(),
    email: str("email"),
    phone: str("phone"),
    current_address: str("current_address"),
    preferred_contact: str("preferred_contact") as ApplicantInput["preferred_contact"],
    status_key: str("status_key") ?? "neu",

    desired_city: str("desired_city"),
    desired_districts: districts,
    num_persons: num("num_persons"),
    num_adults: num("num_adults"),
    num_children: num("num_children"),
    desired_rooms_min: num("desired_rooms_min"),
    desired_area_min: num("desired_area_min"),
    desired_area_max: num("desired_area_max"),
    max_cold_rent: num("max_cold_rent"),
    max_warm_rent: num("max_warm_rent"),
    desired_move_in: str("desired_move_in"),

    has_pets: bool("has_pets"),
    pet_type: str("pet_type"),
    smoker: bool("smoker"),
    special_requirements: str("special_requirements"),

    household_net_income: num("household_net_income"),
    num_income_earners: num("num_income_earners"),
    employment_status: str("employment_status") as ApplicantInput["employment_status"],
    employment_type: str("employment_type") as ApplicantInput["employment_type"],
    other_income: str("other_income"),

    has_schufa: bool("has_schufa"),
    has_income_proof: bool("has_income_proof"),
    has_debt_clearance_cert: bool("has_debt_clearance_cert"),
    further_documents_note: str("further_documents_note"),

    residence_status: str("residence_status") as ApplicantInput["residence_status"],

    internal_notes: str("internal_notes"),
  };
}

export async function createApplicant(formData: FormData) {
  await requireStaff();
  const supabase = await createClient();
  const input = parseApplicantForm(formData);

  if (!input.first_name || !input.last_name) {
    throw new Error("Vor- und Nachname sind Pflichtfelder.");
  }

  const { data, error } = await supabase.from("applicants").insert(input).select("id").single();
  if (error) throw new Error(error.message);

  await supabase.rpc("emit_event", {
    p_type: "APPLICANT_CREATED",
    p_payload: { applicant_id: data.id },
  });

  revalidatePath("/admin/applicants");
  redirect(`/admin/applicants/${data.id}`);
}

export async function updateApplicant(id: string, formData: FormData) {
  await requireStaff();
  const supabase = await createClient();
  const input = parseApplicantForm(formData);

  if (!input.first_name || !input.last_name) {
    throw new Error("Vor- und Nachname sind Pflichtfelder.");
  }

  const { error } = await supabase.from("applicants").update(input).eq("id", id);
  if (error) throw new Error(error.message);

  revalidatePath("/admin/applicants");
  revalidatePath(`/admin/applicants/${id}`);
}

export async function deleteApplicant(id: string) {
  await requireAdmin();
  const supabase = await createClient();
  const { error } = await supabase.from("applicants").delete().eq("id", id);
  if (error) throw new Error(error.message);

  revalidatePath("/admin/applicants");
  redirect("/admin/applicants");
}
