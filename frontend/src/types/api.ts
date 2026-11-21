export interface ApiError {
  message: string;
  statusCode: number;
  details?: Record<string, unknown>;
}
