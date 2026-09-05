export interface User {
  id: string;
  email: string;
  full_name: string;
  organization_name?: string;
  role: string;
  created_at: string;
}

export interface Patient {
  id: string;
  patient_id: string; // e.g. CL-8F29K4
  full_name: string;
  age: number;
  sex: 'male' | 'female' | 'other';
  symptoms?: string;
  existing_conditions?: string;
  allergies?: string;
  current_medications?: string;
  medical_history?: string;
  additional_notes?: string;
  created_by_user_id: string;
  created_at: string;
  updated_at: string;
  report_count: number;
  pending_verifications_count: number;
  conflict_count: number;
}

export interface MedicalReport {
  id: string;
  patient_id: string;
  file_name: string;
  original_file_name: string;
  file_type: string;
  file_size_bytes: number;
  report_date?: string;
  facility_name?: string;
  report_title?: string;
  processing_status: 'UPLOADED' | 'PROCESSING' | 'EXTRACTED' | 'ERROR';
  error_message?: string;
  uploaded_at: string;
  lab_count: number;
  entity_count: number;
}

export type RangeStatus = 'LOW' | 'NORMAL' | 'HIGH' | 'REFERENCE_RANGE_UNAVAILABLE';
export type VerificationStatus = 'AI_EXTRACTED' | 'PENDING_VERIFICATION' | 'HUMAN_VERIFIED' | 'REJECTED';
export type ProvenanceType = 'USER_PROVIDED' | 'AI_EXTRACTED' | 'AI_GENERATED' | 'HUMAN_VERIFIED';

export interface ExtractedLabResult {
  id: string;
  report_id: string;
  patient_id: string;
  test_name: string;
  raw_value: string;
  numeric_value?: number;
  unit?: string;
  raw_reference_range?: string;
  ref_low?: number;
  ref_high?: number;
  range_status: RangeStatus;
  observations?: string;
  page_number: number;
  source_snippet?: string;
  provenance_type: ProvenanceType;
  verification_status: VerificationStatus;
  verified_by_user_id?: string;
  verified_at?: string;
  human_override_notes?: string;
  original_ai_value?: string;
  created_at: string;
  report_file_name?: string;
  report_date?: string;
}

export interface ExtractedClinicalEntity {
  id: string;
  report_id: string;
  patient_id: string;
  entity_type: 'MEDICATION' | 'CONDITION' | 'ALLERGY' | 'OBSERVATION';
  entity_name: string;
  details?: string;
  page_number: number;
  source_snippet?: string;
  provenance_type: ProvenanceType;
  verification_status: VerificationStatus;
  verified_by_user_id?: string;
  verified_at?: string;
  created_at: string;
}

export interface ComparisonItem {
  test_name: string;
  status_tag: 'NEW' | 'CHANGED' | 'UNCHANGED' | 'INCOMPARABLE';
  unit?: string;
  report_a_value?: string;
  report_b_value?: string;
  report_a_range?: string;
  report_b_range?: string;
  report_a_status?: RangeStatus;
  report_b_status?: RangeStatus;
  numeric_delta?: number;
  percentage_delta?: number;
  delta_display?: string;
  notes?: string;
}

export interface ReportComparisonResponse {
  report_a_id: string;
  report_b_id: string;
  report_a_name: string;
  report_b_name: string;
  report_a_date?: string;
  report_b_date?: string;
  items: ComparisonItem[];
  new_count: number;
  changed_count: number;
  unchanged_count: number;
  incomparable_count: number;
}

export interface Inconsistency {
  id: string;
  patient_id: string;
  category: 'ALLERGY' | 'MEDICATION' | 'DEMOGRAPHIC' | 'CLINICAL';
  entity_name: string;
  source_a: {
    type: string;
    text: string;
    date?: string;
  };
  source_b: {
    type: string;
    text: string;
    page?: number;
    date?: string;
  };
  conflict_description: string;
  resolution_status: 'FLAGGED' | 'ACKNOWLEDGED';
  created_at: string;
}

export interface GroundedCitation {
  source_type: string;
  source_title: string;
  page_number?: number;
  snippet?: string;
}

export interface DoctorQueryResponse {
  answer: string;
  citations: GroundedCitation[];
  disclaimer: string;
}

export interface PatientSummaryResponse {
  summary: string;
  grounded_record_count: number;
  disclaimer: string;
}

export interface AuditLogEntry {
  id: string;
  patient_id?: string;
  patient_name?: string;
  user_id: string;
  user_name?: string;
  action: string;
  entity_affected?: string;
  details?: Record<string, any>;
  timestamp: string;
}
