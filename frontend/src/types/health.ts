export interface HealthResponse {
  status: 'healthy' | 'degraded' | 'unreachable';
  version: string;
  environment: string;
  redis_status: 'healthy' | 'unreachable';
  database_status: 'healthy' | 'unreachable';
  uptime_seconds: number;
}
