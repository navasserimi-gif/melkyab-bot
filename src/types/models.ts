// Domain-Typen, die das Schema aus supabase/migrations/0001_init.sql spiegeln.
// Bewusst handgeschrieben statt generiert, da (noch) kein Live-Supabase-Projekt
// für `supabase gen types` an dieses Repo angebunden ist.

export type Role = "admin" | "makler" | "interessent";

export interface Profile {
  id: string;
  role: Role;
  full_name: string | null;
  email: string | null;
  phone: string | null;
  active: boolean;
  permissions: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface StatusDefinition {
  key: string;
  label: string;
  sort_order: number;
  color: string | null;
  is_active: boolean;
}

export interface DocumentType {
  key: string;
  label: string;
  required: boolean;
  sort_order: number;
  is_active: boolean;
}

export interface MatchingWeight {
  criterion: string;
  weight: number;
  updated_at: string;
}

export type PreferredContact = "email" | "telefon" | "telegram";
export type EmploymentStatus =
  | "angestellt"
  | "selbststaendig"
  | "ausbildung"
  | "studium"
  | "rente"
  | "sonstige";
export type EmploymentType = "unbefristet" | "befristet" | "probezeit" | "sonstige";
export type ResidenceStatus =
  | "deutsche_staatsangehoerigkeit"
  | "eu_aufenthaltsstatus"
  | "befristeter_aufenthaltstitel"
  | "unbefristeter_aufenthaltstitel"
  | "sonstiger_status";

export interface Applicant {
  id: string;
  internal_code: string;
  user_id: string | null;
  assigned_to: string | null;
  status_key: string;

  first_name: string;
  last_name: string;
  email: string | null;
  phone: string | null;
  current_address: string | null;
  preferred_contact: PreferredContact | null;

  desired_city: string | null;
  desired_districts: string[];
  num_persons: number | null;
  num_adults: number | null;
  num_children: number | null;
  desired_rooms_min: number | null;
  desired_area_min: number | null;
  desired_area_max: number | null;
  max_cold_rent: number | null;
  max_warm_rent: number | null;
  desired_move_in: string | null;

  has_pets: boolean;
  pet_type: string | null;
  smoker: boolean;
  special_requirements: string | null;

  household_net_income: number | null;
  num_income_earners: number | null;
  employment_status: EmploymentStatus | null;
  employment_type: EmploymentType | null;
  other_income: string | null;

  has_schufa: boolean;
  has_income_proof: boolean;
  has_debt_clearance_cert: boolean;
  further_documents_note: string | null;

  residence_status: ResidenceStatus | null;

  internal_notes: string | null;
  created_at: string;
  updated_at: string;
}

export type PropertyStatus = "entwurf" | "veroeffentlicht" | "reserviert" | "vermietet" | "archiviert";

export interface Property {
  id: string;
  internal_code: string;
  external_id: string | null;
  company: string | null;
  object_name: string | null;
  street: string | null;
  house_number: string | null;
  postal_code: string | null;
  city: string | null;
  district: string | null;
  floor: string | null;
  rooms: number | null;
  living_area: number | null;
  cold_rent: number | null;
  ancillary_costs: number | null;
  heating_costs: number | null;
  warm_rent: number | null;
  deposit: number | null;
  move_in_date: string | null;
  has_balcony: boolean;
  has_terrace: boolean;
  has_garden: boolean;
  has_elevator: boolean;
  has_parking_space: boolean;
  has_garage: boolean;
  has_cellar: boolean;
  pets_allowed: boolean;
  energy_info: string | null;
  description: string | null;
  status: PropertyStatus;
  source_provider: string;
  internal_notes: string | null;
  created_by: string | null;
  created_at: string;
  updated_at: string;
}

export type ImageCategory =
  | "titelbild"
  | "wohnzimmer"
  | "schlafzimmer"
  | "kueche"
  | "bad"
  | "balkon"
  | "grundriss"
  | "sonstige";

export interface PropertyImage {
  id: string;
  property_id: string;
  storage_path: string;
  category: ImageCategory;
  sort_order: number;
  created_at: string;
}

export type ViewingStatus = "angefragt" | "geplant" | "durchgefuehrt" | "abgesagt" | "verschoben";
export type ViewingFeedback = "moechte_die_wohnung" | "unsicher" | "kein_interesse";

export interface Viewing {
  id: string;
  property_id: string;
  applicant_id: string;
  scheduled_at: string | null;
  status: ViewingStatus;
  google_calendar_event_id: string | null;
  internal_note: string | null;
  feedback: ViewingFeedback | null;
  feedback_at: string | null;
  created_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface Match {
  id: string;
  applicant_id: string;
  property_id: string;
  score: number;
  score_breakdown: Record<string, number>;
  computed_at: string;
}

export interface AuditLogEntry {
  id: string;
  actor_id: string | null;
  action: string;
  entity_type: string;
  entity_id: string | null;
  diff: unknown;
  created_at: string;
}
