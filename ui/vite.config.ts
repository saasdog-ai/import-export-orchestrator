import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import federation from '@originjs/vite-plugin-federation'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    federation({
      name: 'importExportUI',
      filename: 'remoteEntry.js',
      // Expose components for host applications to consume
      exposes: {
        // All-in-one federation export with everything
        './federation': './src/federation.ts',
        // Main app wrapper with all routes (includes BrowserRouter - for standalone)
        './App': './src/App.tsx',
        // Routes only (no BrowserRouter - for micro-frontend embedding)
        './AppRoutes': './src/AppRoutes.tsx',
        // Content-only micro-frontend (no layout/sidebar - recommended for embedding)
        './MicroFrontend': './src/MicroFrontend.tsx',
        // Provider for configuration injection
        './Provider': './src/providers/ConfigProvider.tsx',
        // Individual page components for flexible integration
        './ExportCreate': './src/pages/exports/ExportCreate.tsx',
        './ExportList': './src/pages/exports/ExportList.tsx',
        './ImportCreate': './src/pages/imports/ImportCreate.tsx',
        './JobList': './src/pages/jobs/JobList.tsx',
        './JobDetail': './src/pages/jobs/JobDetail.tsx',
        './Dashboard': './src/pages/Dashboard.tsx',
        // API client for programmatic usage
        './apiClient': './src/api/apiClient.ts',
        // Hook for API access within components
        './useApiClient': './src/hooks/useApiClient.ts',
      },
      // Shared dependencies - host app can provide these
      shared: ['react', 'react-dom', 'react-router-dom', '@tanstack/react-query'],
    }),
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 3000,
    cors: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
  preview: {
    port: 3000,
    cors: true,
  },
  build: {
    // Required for Module Federation
    modulePreload: false,
    target: 'esnext',
    minify: false,
    cssCodeSplit: false,
  },
})
