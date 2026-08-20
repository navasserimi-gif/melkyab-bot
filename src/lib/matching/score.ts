import type { Applicant, MatchingWeight, Property } from "@/types/models";

export type MatchCriterion =
  | "ort"
  | "budget"
  | "zimmer"
  | "flaeche"
  | "einzugstermin"
  | "haustier"
  | "haushaltsgroesse";

export const DEFAULT_WEIGHTS: Record<MatchCriterion, number> = {
  ort: 25,
  budget: 25,
  zimmer: 15,
  flaeche: 10,
  einzugstermin: 10,
  haustier: 5,
  haushaltsgroesse: 10,
};

export interface MatchResult {
  score: number;
  breakdown: Record<MatchCriterion, number>;
}

/**
 * Berechnet einen nachvollziehbaren Match-Score zwischen 0 und 100 (§12).
 *
 * Wichtig: Der Score ist ausschließlich Entscheidungsunterstützung für Admin/
 * Makler. Er berücksichtigt bewusst KEINEN Aufenthaltsstatus und KEINE
 * Staatsangehörigkeit — das wäre eine unzulässige automatische
 * Ausschlussentscheidung (§5/§12).
 */
export function computeMatchScore(
  applicant: Applicant,
  property: Property,
  weights: Record<string, number> = DEFAULT_WEIGHTS,
): MatchResult {
  const w = (key: MatchCriterion) => weights[key] ?? DEFAULT_WEIGHTS[key];
  const breakdown: Record<MatchCriterion, number> = {
    ort: 0,
    budget: 0,
    zimmer: 0,
    flaeche: 0,
    einzugstermin: 0,
    haustier: 0,
    haushaltsgroesse: 0,
  };

  // Ort: volle Punktzahl bei exakter Stadt- oder Stadtteil-Übereinstimmung.
  if (applicant.desired_city && property.city) {
    const sameCity = normalize(applicant.desired_city) === normalize(property.city);
    const sameDistrict =
      !!property.district &&
      applicant.desired_districts.some((d) => normalize(d) === normalize(property.district!));
    if (sameCity || sameDistrict) breakdown.ort = w("ort");
  }

  // Budget: volle Punktzahl wenn Warmmiete im Rahmen liegt, linear abgestuft
  // bis 15% Überschreitung, danach 0.
  if (applicant.max_warm_rent && property.warm_rent != null) {
    const ratio = property.warm_rent / applicant.max_warm_rent;
    if (ratio <= 1) breakdown.budget = w("budget");
    else if (ratio <= 1.15) breakdown.budget = Math.round(w("budget") * (1 - (ratio - 1) / 0.15));
  }

  // Zimmer: volle Punktzahl bei >= gewünschter Mindestanzahl, Teilpunkte bei knapp darunter.
  if (applicant.desired_rooms_min != null && property.rooms != null) {
    const diff = property.rooms - applicant.desired_rooms_min;
    if (diff >= 0) breakdown.zimmer = w("zimmer");
    else if (diff >= -1) breakdown.zimmer = Math.round(w("zimmer") * 0.5);
  }

  // Wohnfläche: innerhalb des gewünschten Bereichs volle Punktzahl.
  if (property.living_area != null) {
    const min = applicant.desired_area_min;
    const max = applicant.desired_area_max;
    if ((min == null || property.living_area >= min) && (max == null || property.living_area <= max)) {
      breakdown.flaeche = w("flaeche");
    } else if (min != null && property.living_area >= min * 0.85) {
      breakdown.flaeche = Math.round(w("flaeche") * 0.5);
    }
  }

  // Einzugstermin: volle Punktzahl wenn Wohnung zum/vor Wunschtermin verfügbar ist.
  if (applicant.desired_move_in && property.move_in_date) {
    const wanted = new Date(applicant.desired_move_in).getTime();
    const available = new Date(property.move_in_date).getTime();
    if (available <= wanted) breakdown.einzugstermin = w("einzugstermin");
    else if (available - wanted <= 30 * 24 * 60 * 60 * 1000) {
      breakdown.einzugstermin = Math.round(w("einzugstermin") * 0.5);
    }
  }

  // Haustier: volle Punktzahl wenn kein Konflikt besteht.
  if (!applicant.has_pets || property.pets_allowed) {
    breakdown.haustier = w("haustier");
  }

  // Haushaltsgröße: grobe Heuristik über Zimmeranzahl vs. Personenzahl.
  if (applicant.num_persons != null && property.rooms != null) {
    const adequate = property.rooms >= Math.ceil(applicant.num_persons / 2);
    breakdown.haushaltsgroesse = adequate ? w("haushaltsgroesse") : Math.round(w("haushaltsgroesse") * 0.3);
  }

  const score = Object.values(breakdown).reduce((sum, v) => sum + v, 0);
  return { score: Math.min(100, score), breakdown };
}

export function weightsFromRows(rows: MatchingWeight[]): Record<string, number> {
  return Object.fromEntries(rows.map((r) => [r.criterion, r.weight]));
}

function normalize(value: string): string {
  return value.trim().toLowerCase();
}
