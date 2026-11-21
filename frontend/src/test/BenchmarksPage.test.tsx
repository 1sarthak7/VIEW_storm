import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BenchmarksPage } from '../pages/BenchmarksPage';

// Mock AuthContext
vi.mock('../context/AuthContext', () => ({
  useAuth: () => ({
    user: { username: 'admin', role: 'admin' },
    hasRole: () => true,
    token: 'test-token',
  }),
}));

// Mock request from client
vi.mock('../api/client', () => ({
  request: vi.fn().mockImplementation((url: string) => {
    if (url.includes('/api/v1/benchmarks/profiles')) {
      return Promise.resolve([
        {
          name: 'smoke',
          description: 'Profile 1 — Sanity check to verify all pipeline components.',
          virtual_users: 10,
          spawn_rate: 2.0,
          duration_seconds: 30,
          recommended_mode: 'local',
          max_error_rate_pct: 1.0,
          max_p95_latency_ms: 500.0,
          requires_explicit_approval: false,
          min_worker_nodes: 1,
        },
        {
          name: 'extended',
          description: 'Profile 6 — 25,000 virtual users on dedicated worker infrastructure.',
          virtual_users: 25000,
          spawn_rate: 500.0,
          duration_seconds: 600,
          recommended_mode: 'distributed',
          max_error_rate_pct: 5.0,
          max_p95_latency_ms: 3000.0,
          requires_explicit_approval: true,
          min_worker_nodes: 8,
        },
      ]);
    }
    if (url.includes('/api/v1/benchmarks/preflight')) {
      return Promise.resolve({
        ready: true,
        profile_name: 'smoke',
        required_users: 10,
        available_worker_nodes: 1,
        total_worker_capacity: 500,
        redis_ok: true,
        db_ok: true,
        memory_ok: true,
        requires_explicit_approval: false,
        messages: ['All cluster preflight checks passed.'],
      });
    }
    if (url.includes('/api/v1/benchmarks/results')) {
      return Promise.resolve([
        {
          id: 'bmk_test_1',
          profile_name: 'smoke',
          test_type: 'locust_local',
          virtual_users: 10,
          spawn_rate: 2.0,
          duration_seconds: 30,
          total_requests: 300,
          requests_per_second: 10.0,
          avg_latency_ms: 12.0,
          p50_latency_ms: 10.0,
          p95_latency_ms: 18.0,
          p99_latency_ms: 25.0,
          max_latency_ms: 30.0,
          error_rate_pct: 0.0,
          passed_thresholds: true,
          created_at: '2026-11-21T12:00:00Z',
          preflight_passed: true,
        },
      ]);
    }
    return Promise.resolve({});
  }),
}));

describe('BenchmarksPage Component', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
        },
      },
    });
  });

  it('renders benchmark dashboard header and standard profiles', async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <BenchmarksPage />
      </QueryClientProvider>
    );

    expect(screen.getByText(/Large-Scale Benchmark Management/i)).toBeInTheDocument();
    expect(
      screen.getByText(/Progressive capacity validation from 10 to 200,000 synthetic virtual users/i)
    ).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getAllByText('smoke').length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText('extended')).toBeInTheDocument();
    });
  });

  it('renders preflight readiness checklist and historical benchmark experiments', async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <BenchmarksPage />
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByText(/Cluster Preflight Verification/i)).toBeInTheDocument();
      expect(screen.getByText(/Historical Benchmark Experiments/i)).toBeInTheDocument();
      expect(screen.getByText('SLA Passed')).toBeInTheDocument();
      expect(screen.getByText('10.0 RPS')).toBeInTheDocument();
    });
  });
});
