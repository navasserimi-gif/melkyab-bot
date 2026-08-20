"use server";

import { revalidatePath } from "next/cache";
import { createClient } from "@/lib/supabase/server";

export interface RespondResult {
  ok?: true;
  error?: string;
}

const VALID_RESPONSES = ["interesse", "kein_interesse", "besichtigung_angefragt"] as const;
type Response = (typeof VALID_RESPONSES)[number];

/** Interessent beantwortet ein Wohnungsangebot (§13). */
export async function respondToOffer(offerId: string, response: Response): Promise<RespondResult> {
  if (!VALID_RESPONSES.includes(response)) return { error: "Ungültige Antwort." };

  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return { error: "Bitte zuerst anmelden." };

  const { data: offer, error: fetchError } = await supabase
    .from("property_offers")
    .select("id, applicant_id, property_id")
    .eq("id", offerId)
    .single();
  if (fetchError || !offer) return { error: "Angebot nicht gefunden." };

  const { error } = await supabase
    .from("property_offers")
    .update({ response, responded_at: new Date().toISOString() })
    .eq("id", offerId);
  if (error) return { error: error.message };

  if (response === "besichtigung_angefragt") {
    await supabase.from("viewings").insert({
      property_id: offer.property_id,
      applicant_id: offer.applicant_id,
      status: "angefragt",
    });
    await supabase
      .from("applicants")
      .update({ status_key: "besichtigung_angefragt" })
      .eq("id", offer.applicant_id);
    await supabase.rpc("emit_event", {
      p_type: "VIEWING_REQUESTED",
      p_payload: { property_id: offer.property_id, applicant_id: offer.applicant_id },
    });
  } else if (response === "interesse") {
    await supabase
      .from("applicants")
      .update({ status_key: "interesse_bestaetigt" })
      .eq("id", offer.applicant_id);
    await supabase.rpc("emit_event", {
      p_type: "INTEREST_CONFIRMED",
      p_payload: { property_id: offer.property_id, applicant_id: offer.applicant_id },
    });
  }

  revalidatePath(`/portal/offers/${offerId}`);
  revalidatePath("/portal");
  return { ok: true };
}

/** Interessent bestätigt den von Staff vorgeschlagenen Besichtigungstermin. */
export async function confirmViewingTime(viewingId: string): Promise<RespondResult> {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return { error: "Bitte zuerst anmelden." };

  const { data: viewing, error } = await supabase
    .from("viewings")
    .update({ confirmed_at: new Date().toISOString() })
    .eq("id", viewingId)
    .select("property_id, applicant_id")
    .single();
  if (error) return { error: error.message };

  await supabase
    .from("applicants")
    .update({ status_key: "besichtigung_geplant" })
    .eq("id", viewing.applicant_id);

  await supabase.rpc("emit_event", {
    p_type: "VIEWING_CONFIRMED",
    p_payload: {
      viewing_id: viewingId,
      property_id: viewing.property_id,
      applicant_id: viewing.applicant_id,
    },
  });

  revalidatePath("/portal");
  return { ok: true };
}
