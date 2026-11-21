import React, { Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from './context/AuthContext';
import { AppLayout } from './components/layout/AppLayout';
import { PageSkeleton } from './components/common/PageSkeleton';

// Route-based code splitting with React.lazy
const OverviewPage = React.lazy(() =>
  import('./pages/OverviewPage').then((m) => ({ default: m.OverviewPage }))
);
const SimulationsPage = React.lazy(() =>
  import('./pages/SimulationsPage').then((m) => ({ default: m.SimulationsPage }))
);
const SimulationDetailPage = React.lazy(() =>
  import('./pages/SimulationDetailPage').then((m) => ({ default: m.SimulationDetailPage }))
);
const WorkerNodesPage = React.lazy(() =>
  import('./pages/WorkerNodesPage').then((m) => ({ default: m.WorkerNodesPage }))
);
const AnalyticsPage = React.lazy(() =>
  import('./pages/AnalyticsPage').then((m) => ({ default: m.AnalyticsPage }))
);
const ReportsPage = React.lazy(() =>
  import('./pages/ReportsPage').then((m) => ({ default: m.ReportsPage }))
);
const SettingsPage = React.lazy(() =>
  import('./pages/SettingsPage').then((m) => ({ default: m.SettingsPage }))
);
const LoginPage = React.lazy(() =>
  import('./pages/LoginPage').then((m) => ({ default: m.LoginPage }))
);

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2,
      refetchOnWindowFocus: true,
      staleTime: 3000,
    },
  },
});

export const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route element={<AppLayout />}>
              <Route
                index
                element={
                  <Suspense fallback={<PageSkeleton />}>
                    <OverviewPage />
                  </Suspense>
                }
              />
              <Route
                path="simulations"
                element={
                  <Suspense fallback={<PageSkeleton />}>
                    <SimulationsPage />
                  </Suspense>
                }
              />
              <Route
                path="simulations/:runId"
                element={
                  <Suspense fallback={<PageSkeleton />}>
                    <SimulationDetailPage />
                  </Suspense>
                }
              />
              <Route
                path="workers"
                element={
                  <Suspense fallback={<PageSkeleton />}>
                    <WorkerNodesPage />
                  </Suspense>
                }
              />
              <Route
                path="analytics"
                element={
                  <Suspense fallback={<PageSkeleton />}>
                    <AnalyticsPage />
                  </Suspense>
                }
              />
              <Route
                path="reports"
                element={
                  <Suspense fallback={<PageSkeleton />}>
                    <ReportsPage />
                  </Suspense>
                }
              />
              <Route
                path="settings"
                element={
                  <Suspense fallback={<PageSkeleton />}>
                    <SettingsPage />
                  </Suspense>
                }
              />
              <Route
                path="login"
                element={
                  <Suspense fallback={<PageSkeleton />}>
                    <LoginPage />
                  </Suspense>
                }
              />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
};

export default App;
