import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import federation from '@originjs/vite-plugin-federation'
import path from 'path'

// AWS Backend Configuration
// Use: npx vite --config vite.config.aws.ts
const AWS_ALB_URL = 'http://import-export-orchestrator-alb-d-735480500.us-east-1.elb.amazonaws.com'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    federation({
      name: 'importExportUI',
      filename: 'remoteEntry.js',
      exposes: {
        './federation': './src/federation.ts',
        './App': './src/App.tsx',
        './AppRoutes': './src/AppRoutes.tsx',
        './MicroFrontend': './src/MicroFrontend.tsx',
        './Provider': './src/providers/ConfigProvider.tsx',
        './ExportCreate': './src/pages/exports/ExportCreate.tsx',
        './ExportList': './src/pages/exports/ExportList.tsx',
        './ImportCreate': './src/pages/imports/ImportCreate.tsx',
        './JobList': './src/pages/jobs/JobList.tsx',
        './JobDetail': './src/pages/jobs/JobDetail.tsx',
        './Dashboard': './src/pages/Dashboard.tsx',
        './apiClient': './src/api/apiClient.ts',
        './useApiClient': './src/hooks/useApiClient.ts',
      },
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
        target: AWS_ALB_URL,
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
    modulePreload: false,
    target: 'esnext',
    minify: false,
    cssCodeSplit: false,
  },
})
