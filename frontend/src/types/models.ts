export type Role = 'admin' | 'curator' | 'marketing';

export interface User {
  id: string;
  email: string;
  display_name: string;
  role: Role;
  is_active: boolean;
  role_label?: string;
}

export type RunStatus = 'queued' | 'running' | 'succeeded' | 'failed';
export type CandidateDecision = 'auto' | 'review' | 'reject';
export type CandidateStatus = 'pending' | 'confirmed' | 'rejected';
export type ClusterStatus = 'auto_merged' | 'pending_review' | 'confirmed';
export type GoldenStatus = 'active' | 'provisional';

export interface Run {
  id: string;
  rule_id: string | null;
  run_label: string;
  status: RunStatus;
  params: Record<string, unknown>;
  blocking_keys: string[];
  records_scanned: number;
  blocked_pairs_raw: number;
  pruned_pairs: number;
  candidate_pairs: number;
  auto_pairs: number;
  review_pairs: number;
  rejected_pairs: number;
  clusters_auto: number;
  clusters_review: number;
  golden_records: number;
  duration_ms: number;
  distribution: number[];
  error_message: string | null;
  error_code: string | null;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
}

export interface SourceRecord {
  id: string;
  source_system: 'pos' | 'ecommerce' | 'service';
  source_label: string;
  external_id: string;
  full_name: string | null;
  phone: string | null;
  email: string | null;
  address: string | null;
  city: string | null;
  normalized_name: string | null;
  normalized_phone: string | null;
  normalized_email: string | null;
  normalized_address: string | null;
  source_updated_at: string | null;
  raw_payload?: Record<string, unknown>;
}

export interface FeatureDetail {
  field: string;
  method: string;
  weight: number;
  left_value: string | null;
  right_value: string | null;
  similarity: number | null;
  contribution: number;
}

export interface Candidate {
  id: string;
  run_id: string;
  left_record_id: string;
  right_record_id: string;
  score: number;
  decision: CandidateDecision;
  status: CandidateStatus;
  blocking_keys: string[];
  features: Record<string, FeatureDetail>;
  available_weight: number | null;
  thresholds: { auto: number; review: number } | null;
  reviewed_at: string | null;
  review_note: string | null;
  left?: SourceRecord;
  right?: SourceRecord;
  cluster_id?: string | null;
}

export interface Cluster {
  id: string;
  run_id: string;
  cluster_key: string;
  member_ids: string[];
  member_keys: string[];
  record_count: number;
  confidence: number;
  status: ClusterStatus;
  edge_type: 'auto' | 'review';
  members?: SourceRecord[];
  edges?: Array<{
    id: string;
    left_record_id: string;
    right_record_id: string;
    score: number;
    decision: CandidateDecision;
    status: CandidateStatus;
  }>;
}

export interface GoldenField {
  field: string;
  label: string;
  value: string | null;
  source_system: string | null;
  source_record_id: string | null;
  source_external_id: string | null;
  reliability: number;
  reason: string;
  conflict: boolean;
  alternatives: Array<{
    value: string;
    source_system: string;
    source_external_id: string;
    reliability: number;
  }>;
}

export interface GoldenRecord {
  id: string;
  run_id: string;
  cluster_id: string;
  entity_key: string;
  fields: GoldenField[];
  conflict_fields: string[];
  confidence: number;
  status: GoldenStatus;
  display?: Record<string, string | null>;
  cluster?: {
    id: string;
    cluster_key: string;
    record_count: number;
    confidence: number;
    status: ClusterStatus;
    member_keys: string[];
  };
}

export interface MergeRule {
  id: string;
  name: string;
  field_weights: Record<string, number>;
  source_reliability: Record<string, number>;
  auto_threshold: number;
  review_threshold: number;
  normalization: Record<string, unknown>;
  version: number;
  is_active: boolean;
  updated_at: string;
}

export interface Overview {
  counts: {
    source_records: number;
    match_candidates: number;
    pending_reviews: number;
    clusters: number;
    golden_records: number;
    merge_rules: number;
    resolution_runs: number;
  };
  latest_run: Run | null;
  labels: Record<string, Record<string, string>>;
  enums: Record<string, string[]>;
  roles: Record<string, string[]>;
  time_decay_half_life_days: number;
}

export interface Page<T> {
  items: T[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

export interface AuditLog {
  id: string;
  actor_email: string;
  action: string;
  entity_type: string;
  entity_id: string | null;
  payload: Record<string, unknown>;
  created_at: string | null;
}
