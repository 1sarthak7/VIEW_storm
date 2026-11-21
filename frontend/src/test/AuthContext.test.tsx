import { describe, it, expect, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import React from 'react';
import { AuthProvider, useAuth, TOKEN_STORAGE_KEY } from '../context/AuthContext';

describe('AuthContext', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  const wrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
    <AuthProvider>{children}</AuthProvider>
  );

  it('initializes with unauthenticated guest state when storage is empty', () => {
    const { result } = renderHook(() => useAuth(), { wrapper });
    expect(result.current.user).toBeNull();
    expect(result.current.token).toBeNull();
    expect(result.current.isAuthenticated).toBe(false);
  });

  it('correctly evaluates role permissions with hasRole', () => {
    const { result } = renderHook(() => useAuth(), { wrapper });

    expect(result.current.hasRole(['admin'])).toBe(false);

    // Mock authenticated user state
    act(() => {
      localStorage.setItem(TOKEN_STORAGE_KEY, 'test-token');
    });

    expect(result.current.hasRole(['admin', 'operator'])).toBe(false);
  });

  it('clears storage and state on logout', () => {
    localStorage.setItem(TOKEN_STORAGE_KEY, 'dummy-token');
    const { result } = renderHook(() => useAuth(), { wrapper });

    act(() => {
      result.current.logout();
    });

    expect(localStorage.getItem(TOKEN_STORAGE_KEY)).toBeNull();
    expect(result.current.token).toBeNull();
    expect(result.current.user).toBeNull();
  });
});
