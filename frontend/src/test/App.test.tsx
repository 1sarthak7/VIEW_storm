import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import App from '../App';

// Mock health query to avoid real network call during smoke test
vi.mock('../api/health', () => ({
  getHealth: vi.fn().mockResolvedValue({
    status: 'healthy',
    version: '1.0.0',
    environment: 'local',
    redis_status: 'healthy',
    database_status: 'healthy',
    uptime_seconds: 120,
  }),
}));

vi.mock('../api/runs', () => ({
  listRuns: vi.fn().mockResolvedValue([]),
}));

vi.mock('../api/workers', () => ({
  listWorkerNodes: vi.fn().mockResolvedValue([]),
}));

describe('App Smoke Test', () => {
  it('renders application shell and overview heading without crashing', async () => {
    render(<App />);
    expect(screen.getByText('ViewStorm')).toBeInTheDocument();
    expect(screen.getByText('Cluster Overview')).toBeInTheDocument();
  });
});
