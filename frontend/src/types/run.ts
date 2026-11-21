export type SimulationStatus =
  | 'pending'
  | 'starting'
  | 'waiting_for_workers'
  | 'running'
  | 'degraded'
  | 'stopping'
  | 'stopped'
  | 'completed'
  | 'failed'
  | 'interrupted';

export type ExecutionMode = 'local' | 'distributed';

export type EventType =
  | 'playback_start'
  | 'playback_progress'
  | 'playback_complete'
  | 'playback_exit';

export interface SimulationRun {
  id: string;
  name: string;
  target_environment: string;
  execution_mode: ExecutionMode;
  virtual_users: number;
  spawn_rate: number;
  duration_seconds: number;
  event_type: string;
  watch_duration_min: number;
  watch_duration_max: number;
  status: SimulationStatus;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  error_message: string | null;
}

export interface SimulationRunCreate {
  name: string;
  target_environment?: string;
  execution_mode: ExecutionMode;
  virtual_users: number;
  spawn_rate: number;
  duration_seconds: number;
  event_type?: string;
  watch_duration_min?: number;
  watch_duration_max?: number;
}
