import { render, screen, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { describe, it, expect, vi } from 'vitest';
import { Sidebar } from '../components/layout/Sidebar';

describe('Sidebar', () => {
  it('renders brand name and navigation items', () => {
    render(
      <BrowserRouter>
        <Sidebar collapsed={false} onToggleCollapse={vi.fn()} />
      </BrowserRouter>
    );

    expect(screen.getByText('ViewStorm')).toBeInTheDocument();
    expect(screen.getByText('Overview')).toBeInTheDocument();
    expect(screen.getByText('Simulations')).toBeInTheDocument();
    expect(screen.getByText('Worker Nodes')).toBeInTheDocument();
    expect(screen.getByText('Analytics')).toBeInTheDocument();
    expect(screen.getByText('Reports')).toBeInTheDocument();
    expect(screen.getByText('Settings')).toBeInTheDocument();
  });

  it('fires toggle collapse callback when toggle button is clicked', () => {
    const handleToggle = vi.fn();
    render(
      <BrowserRouter>
        <Sidebar collapsed={false} onToggleCollapse={handleToggle} />
      </BrowserRouter>
    );

    const toggleButton = screen.getByTitle('Collapse sidebar');
    fireEvent.click(toggleButton);
    expect(handleToggle).toHaveBeenCalledTimes(1);
  });
});
