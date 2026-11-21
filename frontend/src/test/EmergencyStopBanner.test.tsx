import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import { EmergencyStopBanner } from '../components/layout/EmergencyStopBanner';
import { AuthProvider } from '../context/AuthContext';

describe('EmergencyStopBanner', () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  it('renders nothing when emergency stop is inactive', () => {
    const { container } = render(
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <EmergencyStopBanner />
        </AuthProvider>
      </QueryClientProvider>
    );

    expect(container.firstChild).toBeNull();
  });
});
