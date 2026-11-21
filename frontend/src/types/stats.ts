import { SimulationStatus } from './run';

export interface SimulationStats {
  run_id: string;
  status: SimulationStatus;
  total_events: number;
  accepted_events: number;
  rejected_events: number;
  duplicate_events: number;
  unique_viewers_count: number;
  events_by_type: Record<string, number>;
  total_watch_duration_ms: number;
  average_watch_duration_ms: number;
  started_at: string | null;
  elapsed_seconds: number;
  current_rps: number;
}

export interface MetricPoint {
  timestamp: string;
  active_users: number;
  requests_per_second: number;
  successful_requests: number;
  failed_requests: number;
  average_latency_ms: number;
  p50_latency_ms: number;
  p95_latency_ms: number;
  p99_latency_ms: number;
}

export interface SimulationMetrics {
  run_id: string;
  metrics: MetricPoint[];
}

export interface SimulationReport {
  run_id: string;
  name: string;
  target_environment: string;
  status: SimulationStatus;
  configured_users: number;
  duration_seconds: number;
  actual_duration_seconds: number;

  total_submissions: number;
  accepted_events: number;
  rejected_events: number;
  duplicate_events: number;
  unique_viewers: number;
  total_watch_duration_ms: number;
  average_watch_duration_ms: number;
  events_breakdown: Record<string, number>;
  average_throughput_eps: number;

  total_http_requests: number;
  successful_http_requests: number;
  failed_http_requests: number;
  requests_per_second: number;
  min_latency_ms: number;
  avg_latency_ms: number;
  p50_latency_ms: number;
  p95_latency_ms: number;
  p99_latency_ms: number;
  max_latency_ms: number;

  resource_observations?: Record<string, unknown> | null;
  started_at: string | null;
  finished_at: string | null;
}
