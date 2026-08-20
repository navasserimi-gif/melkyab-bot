"use server";

import { createClient } from "@/lib/supabase/server";

export interface CreateApplicantResult {
  id?: string;
  error?: string;
}

/** Self-Service: Interessent legt sein eigenes Profil über das öffentliche Formular an (§5). */
export async function createOwnApplicant(formData: FormData): Promise<CreateApplicantResult> {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return { error: "Bitte zuerst anmelden." };

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

  const firstName = String(formData.get("first_name") ?? "").trim();
  const lastName = String(formData.get("last_name") ?? "").trim();
  if (!firstName || !lastName) return { error: "Bitte Vor- und Nachname angeben." };

  const { data, error } = await supabase
    .from("applicants")
    .insert({
      user_id: user.id,
      status_key: "formular_ausgefuellt",
      first_name: firstName,
      last_name: lastName,
      email: str("email") ?? user.email,
      phone: str("phone"),
      current_address: str("current_address"),
      preferred_contact: str("preferred_contact"),

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
      employment_status: str("employment_status"),
      employment_type: str("employment_type"),
      other_income: str("other_income"),

      residence_status: str("residence_status"),
    })
    .select("id")
    .single();

  if (error) {
    if (error.code === "23505") {
      return { error: "Du hast bereits ein Profil angelegt." };
    }
    return { error: error.message };
  }

  await supabase.rpc("emit_event", {
    p_type: "PROFILE_COMPLETED",
    p_payload: { applicant_id: data.id, user_id: user.id },
  });

  return { id: data.id };
}
