/**
 * AppRoutes - Routes without BrowserRouter wrapper
 *
 * Use this component when embedding the Import/Export UI as a micro-frontend.
 * The host application provides its own BrowserRouter.
 *
 * For standalone usage, use App.tsx which includes BrowserRouter.
 */

import { Routes, Route } from "react-router-dom"
import { Layout } from "@/components/Layout"
import { ErrorBoundary } from "@/components/ErrorBoundary"
import { ToastProvider } from "@/contexts/ToastContext"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import {
  Dashboard,
  ExportList,
  ExportCreate,
  ImportList,
  ImportCreate,
  JobList,
  JobDetail,
} from "@/pages"

// Create a default QueryClient for standalone use
const defaultQueryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,
      retry: 1,
    },
  },
})

interface AppRoutesProps {
  /**
   * Base path for all routes (e.g., "/import-export")
   * Routes will be relative to this path
   */
  basePath?: string
  /**
   * Optional QueryClient from host app
   */
  queryClient?: QueryClient
}

export function AppRoutes({ basePath = "", queryClient }: AppRoutesProps) {
  const client = queryClient || defaultQueryClient

  // Helper to prefix routes with basePath
  const route = (path: string) => `${basePath}${path}`

  return (
    <ErrorBoundary>
      <QueryClientProvider client={client}>
        <ToastProvider>
          <Layout>
            <Routes>
              <Route path={route("/")} element={<Dashboard />} />
              <Route path={route("/exports")} element={<ExportList />} />
              <Route path={route("/exports/new")} element={<ExportCreate />} />
              <Route path={route("/imports")} element={<ImportList />} />
              <Route path={route("/imports/new")} element={<ImportCreate />} />
              <Route path={route("/jobs")} element={<JobList />} />
              <Route path={route("/jobs/:jobId")} element={<JobDetail />} />
              {/* Catch-all route to handle sub-paths */}
              <Route path={route("/*")} element={<Dashboard />} />
            </Routes>
          </Layout>
        </ToastProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  )
}

export default AppRoutes
