export type UserRole = 'admin' | 'operator' | 'viewer';

export interface User {
  id: string;
  username: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface EmergencyStopStatus {
  active: boolean;
  reason?: string;
  operator?: string;
  triggered_at?: string;
}

export interface BenchmarkProfile {
  name: string;
  description: string;
  virtual_users: number;
  spawn_rate: number;
  duration_seconds: number;
  recommended_mode: 'local' | 'distributed';
  max_error_rate_pct: number;
  max_p95_latency_ms: number;
}

export interface ThresholdEvaluation {
  passed: boolean;
  max_error_rate_pct: number;
  actual_error_rate_pct: number;
  error_rate_passed: boolean;
  max_p95_latency_ms: number;
  actual_p95_latency_ms: number;
  p95_latency_passed: boolean;
}

export interface BenchmarkResult {
  id: string;
  profile_name: string;
  test_type: string;
  run_id?: string;
  target_environment: string;
  virtual_users: number;
  spawn_rate: number;
  duration_seconds: number;
  total_requests: number;
  requests_per_second: number;
  avg_latency_ms: number;
  p50_latency_ms: number;
  p95_latency_ms: number;
  p99_latency_ms: number;
  error_rate_pct: number;
  passed_thresholds: boolean;
  abort_reason?: string;
  notes?: string;
  created_at: string;
  threshold_evaluation?: ThresholdEvaluation;
}

export interface BenchmarkComparison {
  baseline: BenchmarkResult;
  candidate: BenchmarkResult;
  rps_delta_pct: number;
  p95_latency_delta_pct: number;
  avg_latency_delta_pct: number;
  error_rate_delta_pct: number;
  performance_verdict: 'IMPROVEMENT' | 'REGRESSION' | 'STABLE';
}
