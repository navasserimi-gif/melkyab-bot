import type { createClient } from "@/lib/supabase/server";
import type { Applicant, Property } from "@/types/models";
import { computeMatchScore, weightsFromRows, DEFAULT_WEIGHTS } from "./score";

type SupabaseServerClient = Awaited<ReturnType<typeof createClient>>;

/** Nur diese Status gelten als "noch nicht mit einer Wohnung im Prozess" —
 * nur dann wird der Status durch ein automatisches Angebot vorangetrieben,
 * damit ein bereits laufender Prozess mit einer anderen Wohnung nicht
 * überschrieben wird. */
const PRE_OFFER_STATUSES = [
  "neu",
  "formular_ausgefuellt",
  "vorgeprueft",
  "unterlagen_unvollstaendig",
  "unterlagen_vollstaendig",
  "passende_wohnung_gefunden",
];

const AUTO_SEND_THRESHOLD = 50;
const MAX_AUTO_OFFERS = 15;

/**
 * Berechnet beim Veröffentlichen einer Wohnung automatisch den Match-Score
 * gegen alle Interessenten (§12), speichert die Ergebnisse in `matches` und
 * verschickt automatisch ein Exposé (§13) an die am besten passenden
 * Interessenten, die diese Wohnung noch nicht angeboten bekommen haben.
 * Läuft rein im Portal — kein E-Mail-Versand.
 */
export async function computeAndAutoSendMatches(
  supabase: SupabaseServerClient,
  property: Property,
): Promise<{ matched: number; offered: number }> {
  const [{ data: applicantRows }, { data: weightRows }, { data: existingOfferRows }] =
    await Promise.all([
      supabase.from("applicants").select("*").neq("status_key", "neu").limit(500),
      supabase.from("matching_weights").select("*"),
      supabase.from("property_offers").select("applicant_id").eq("property_id", property.id),
    ]);

  const applicants = (applicantRows ?? []) as Applicant[];
  if (applicants.length === 0) return { matched: 0, offered: 0 };

  const weights = weightRows && weightRows.length > 0 ? weightsFromRows(weightRows) : DEFAULT_WEIGHTS;
  const alreadyOffered = new Set((existingOfferRows ?? []).map((o) => o.applicant_id));

  const scored = applicants
    .filter((a) => a.desired_city)
    .map((applicant) => ({
      applicant,
      ...computeMatchScore(applicant, property, weights),
    }));

  if (scored.length > 0) {
    await supabase.from("matches").upsert(
      scored.map((s) => ({
        applicant_id: s.applicant.id,
        property_id: property.id,
        score: s.score,
        score_breakdown: s.breakdown,
        computed_at: new Date().toISOString(),
      })),
      { onConflict: "applicant_id,property_id" },
    );
  }

  const candidates = scored
    .filter((s) => s.score >= AUTO_SEND_THRESHOLD && !alreadyOffered.has(s.applicant.id))
    .sort((a, b) => b.score - a.score)
    .slice(0, MAX_AUTO_OFFERS);

  let offered = 0;
  for (const candidate of candidates) {
    const { data: offer, error } = await supabase
      .from("property_offers")
      .insert({
        property_id: property.id,
        applicant_id: candidate.applicant.id,
        sent_via: "automatisch",
      })
      .select("id")
      .single();
    if (error || !offer) continue;
    offered += 1;

    if (PRE_OFFER_STATUSES.includes(candidate.applicant.status_key)) {
      await supabase
        .from("applicants")
        .update({ status_key: "wohnung_angeboten" })
        .eq("id", candidate.applicant.id);
    }

    await supabase.rpc("emit_event", {
      p_type: "PROPERTY_OFFERED",
      p_payload: {
        property_id: property.id,
        applicant_id: candidate.applicant.id,
        offer_id: offer.id,
        score: candidate.score,
        automatic: true,
      },
    });
  }

  return { matched: scored.length, offered };
}
