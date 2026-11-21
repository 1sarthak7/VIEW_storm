# ViewStorm Frontend Performance and Bundle Optimization

This document details the frontend architecture optimizations introduced in Milestone 6, specifically code splitting, bundle chunking, and lazy loading.

---

## 1. Route-Based Code Splitting

Previously, the entire React application, all 7 pages, and third-party libraries (including Recharts) were compiled into a single monolithic bundle of **919.51 KB**.

In Milestone 6, route-based code splitting was implemented using `React.lazy` and React `Suspense`:

```tsx
const OverviewPage = React.lazy(() =>
  import('./pages/OverviewPage').then((m) => ({ default: m.OverviewPage }))
);
const SimulationsPage = React.lazy(() =>
  import('./pages/SimulationsPage').then((m) => ({ default: m.SimulationsPage }))
);
const AnalyticsPage = React.lazy(() =>
  import('./pages/AnalyticsPage').then((m) => ({ default: m.AnalyticsPage }))
);
```

While dynamic chunks load over the network, `<PageSkeleton />` renders an accessible, animated pulse placeholder matching the destination page structure.

---

## 2. Vite & Rollup Manual Chunking Strategy

Vendor libraries were isolated into dedicated, cached chunks via `vite.config.ts`:

```typescript
rollupOptions: {
  output: {
    manualChunks: {
      'vendor-react': ['react', 'react-dom', 'react-router-dom'],
      'vendor-query': ['@tanstack/react-query'],
      'vendor-charts': ['recharts'],
      'vendor-icons': ['lucide-react'],
    },
  },
}
```

---

## 3. Measured Bundle Size Comparison

| Chunk | Milestone 5 Size | Milestone 6 Size | Reduction |
|---|---|---|---|
| **Initial App Entry (`index.js`)** | **919.51 KB** (257.05 KB gzip) | **228.25 KB** (71.34 KB gzip) | **-75.2%** |
| `vendor-charts.js` | *Bundled in entry* | 417.95 KB (112.97 KB gzip) | Isolated to chart pages |
| `vendor-react.js` | *Bundled in entry* | 51.73 KB (18.19 KB gzip) | Cacheable vendor core |
| `vendor-query.js` | *Bundled in entry* | 41.78 KB (12.55 KB gzip) | Cacheable data layer |
| `vendor-icons.js` | *Bundled in entry* | 15.67 KB (3.40 KB gzip) | Icon assets |
| `OverviewPage.js` | *Bundled in entry* | 10.46 KB (2.62 KB gzip) | Dynamic route chunk |
| `LoginPage.js` | *Bundled in entry* | 3.90 KB (1.42 KB gzip) | Dynamic route chunk |
