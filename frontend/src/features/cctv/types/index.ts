// TypeScript interfaces for WBPIS

export type CameraId = 'CAM-01' | 'CAM-02' | 'CAM-03';
export type DepartmentCode = 'ENG' | 'PRODUCT' | 'OPERATIONS' | 'SALES';

export type ActivityCode =
  | 'ACT-01' // Workstation Seated
  | 'ACT-02' // Standing at Workstation / Active Interaction
  | 'ACT-03' // Walking / In Transit
  | 'ACT-04' // Workstation Interaction
  | 'ACT-05' // Active Collaboration
  | 'ACT-06' // Away from Monitored Desk / Personal Screen
  | 'ACT-07'; // Unknown / Occluded

export interface SystemHealth {
  status: 'HEALTHY' | 'DEGRADED' | 'DOWN';
  timestamp: string;
  version: string;
  detector_initialized: boolean;
  database_backend: string;
}

export interface SessionStatus {
  camera_id: string;
  is_alive: boolean;
  fps: number;
  active_tracks_count: number;
  total_frames_processed: number;
  dropped_frames_count: number;
  observation_coverage_pct: number;
}

export interface ActiveTrack {
  track_id: string;
  zone_id: string | null;
  activity: string;
  confidence: number;
  velocity: number;
  dwell_duration_seconds: number;
  transitions_count: number;
  interruption_events: number;
  waiting_seconds: number;
  activity_breakdown: Record<string, number>;
}

export interface LiveTelemetrySnapshot {
  timestamp: string;
  camera_id: string;
  fps: number;
  active_tracks: ActiveTrack[];
  zones_occupancy: Record<string, string>;
  observation_coverage_pct: number;
}

export interface SpatialZone {
  zone_id: string;
  camera_id: string;
  name: string;
  zone_type: 'WORKSTATION' | 'COLLABORATION' | 'CORRIDOR' | 'FOCUS_ROOM' | 'SERVICE_RESOURCE';
  capacity: number;
  polygon_coords: [number, number][];
  created_at?: string;
}

export interface ScorecardA {
  scorecard_name: string;
  composite_score: number;
  confidence: string;
  metrics: {
    focus_interruption_freq?: number;
    congestion_ratio_pct?: number;
    waiting_ratio_pct?: number;
    zone_transition_frequency?: number;
    [key: string]: any;
  };
}

export interface ScorecardB {
  scorecard_name: string;
  composite_score: number;
  confidence: string;
  metrics: {
    activity_shares?: Record<string, number>;
    interaction_ratio_pct?: number;
    movement_ratio_pct?: number;
    transition_rate?: number;
    unknown_ratio_pct?: number;
    [key: string]: any;
  };
}

export interface ScorecardC {
  scorecard_name: string;
  composite_score: number;
  confidence: string;
  metrics: {
    workstation_occupancy_rate_pct?: number;
    away_time_ratio_pct?: number;
    total_presence_seconds?: number;
    [key: string]: any;
  };
}

export interface ScorecardD {
  scorecard_name: string;
  composite_score: number | null;
  status?: 'AVAILABLE' | 'UNAVAILABLE';
  source_system?: string;
  confidence?: string;
  metrics: {
    throughput_rate_pct?: number;
    quality_rate_pct?: number;
    timeliness_rate_pct?: number;
    rework_rate_pct?: number;
    [key: string]: any;
  };
}

export interface ScorecardSuite {
  camera_id: string;
  scorecard_a: ScorecardA;
  scorecard_b: ScorecardB;
  scorecard_c: ScorecardC;
  scorecard_d: ScorecardD;
}

export interface Recommendation {
  recommendation_id: string;
  rule_code: string;
  hypothesis: string;
  observed_metric_evidence: string;
  recommended_action: string;
  target_metric: string;
  expected_impact_pct: number;
  mitigation_notes: string;
}

export interface AuditLog {
  log_id: string;
  timestamp: string | null;
  user_id: string;
  user_role: string;
  action_type: string;
  resource_id: string;
  client_ip: string;
  status_code: number;
  details: any;
}

export interface ExportStatus {
  job_id: string;
  status: 'QUEUED' | 'RENDERING' | 'READY' | 'FAILED';
  progress_pct: number;
  frames_rendered: number;
  total_frames: number;
  error_message: string | null;
  download_url: string | null;
}
