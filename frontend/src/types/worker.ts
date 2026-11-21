export type WorkerNodeStatus =
  | 'online'
  | 'busy'
  | 'stale'
  | 'offline'
  | 'incompatible';

export interface WorkerNode {
  id: string;
  worker_identifier: string;
  worker_name: string;
  hostname: string;
  platform: string;
  cpu_cores: number;
  total_memory_bytes: number;
  available_memory_bytes: number;
  locust_version: string;
  software_version: string;
  status: WorkerNodeStatus;
  capacity: number;
  last_heartbeat: string;
  registered_at: string;
}

export interface SimulationWorker {
  id: number;
  run_id: string;
  worker_node_id: string | null;
  worker_identifier: string;
  status: string;
  assigned_users: number;
  active_users: number;
  worker_process_count: number;
  last_heartbeat: string;
  started_at: string | null;
  finished_at: string | null;
  error_message: string | null;
  resource_information?: {
    cpu_utilization?: number;
    ram_utilization?: number;
    available_memory_bytes?: number;
    [key: string]: unknown;
  } | null;
}
