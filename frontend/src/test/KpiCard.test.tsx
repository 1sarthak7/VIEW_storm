import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { KpiCard } from '../components/common/KpiCard';
import { Zap } from 'lucide-react';

describe('KpiCard', () => {
  it('renders title, value, and unit correctly', () => {
    render(
      <KpiCard
        title="Throughput"
        value="125.4"
        unit="req/s"
        icon={Zap}
        subtitle="Simulated load"
      />
    );

    expect(screen.getByText('Throughput')).toBeInTheDocument();
    expect(screen.getByText('125.4')).toBeInTheDocument();
    expect(screen.getByText('req/s')).toBeInTheDocument();
    expect(screen.getByText('Simulated load')).toBeInTheDocument();
  });

  it('displays loading skeleton when loading=true', () => {
    render(
      <KpiCard
        title="Active Viewers"
        value="5000"
        loading={true}
      />
    );

    expect(screen.getByText('Active Viewers')).toBeInTheDocument();
    expect(screen.queryByText('5000')).not.toBeInTheDocument();
  });
});
