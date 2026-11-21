import { ApiError } from '../types/api';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

export async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${BASE_URL.replace(/\/$/, '')}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`;

  const headers = new Headers(options.headers);
  if (!headers.has('Content-Type') && options.body && typeof options.body === 'string') {
    headers.set('Content-Type', 'application/json');
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 15000);

  try {
    const response = await fetch(url, {
      ...options,
      headers,
      signal: options.signal || controller.signal,
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      let errorData: any = {};
      try {
        errorData = await response.json();
      } catch {
        errorData = { detail: response.statusText };
      }

      const errorMessage =
        errorData?.message ||
        errorData?.detail ||
        (Array.isArray(errorData?.detail) ? errorData.detail.map((e: any) => e.msg).join(', ') : null) ||
        `Request failed with status ${response.status}`;

      const apiError: ApiError = {
        message: errorMessage,
        statusCode: response.status,
        details: errorData,
      };
      throw apiError;
    }

    if (response.status === 204) {
      return {} as T;
    }

    return (await response.json()) as T;
  } catch (err: any) {
    clearTimeout(timeoutId);
    if (err?.statusCode) {
      throw err;
    }
    if (err?.name === 'AbortError') {
      const timeoutError: ApiError = {
        message: 'Request timed out after 15 seconds',
        statusCode: 408,
      };
      throw timeoutError;
    }
    const networkError: ApiError = {
      message: err?.message || 'Network connection failed. Backend may be offline.',
      statusCode: 0,
    };
    throw networkError;
  }
}
