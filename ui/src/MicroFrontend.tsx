/**
 * MicroFrontend - Content-only component for embedding in host applications
 *
 * This component renders ONLY the import/export functionality without any
 * layout, navigation, or chrome. The host application provides:
 * - Header/navbar
 * - Sidebar navigation
 * - Overall layout
 *
 * This component provides:
 * - The actual import/export pages (content only)
 * - Internal routing between import/export views
 * - Toast notifications (scoped to this component)
 *
 * Usage in host app:
 * ```tsx
 * <Route path="/import-export/*" element={<ImportExportMicroFrontend />} />
 * ```
 */

// Import styles for micro-frontend (Tailwind + component styles)
import "./index.css"

import { Routes, Route, Navigate } from "react-router-dom"
import { ErrorBoundary } from "@/components/ErrorBoundary"
import { ToastProvider } from "@/contexts/ToastContext"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import {
  ExportList,
  ExportCreate,
  ImportList,
  ImportCreate,
  JobList,
  JobDetail,
} from "@/pages"

// Default QueryClient for standalone use
const defaultQueryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,
      retry: 1,
    },
  },
})

interface MicroFrontendProps {
  /**
   * Optional QueryClient from host app for shared caching
   */
  queryClient?: QueryClient
}

/**
 * Import/Export micro-frontend content component.
 * Renders only the page content - no layout, no sidebar.
 *
 * Routes (relative to where this is mounted):
 * - /          → Redirects to /exports
 * - /exports   → Export list
 * - /exports/new → Create export
 * - /imports   → Import list
 * - /imports/new → Create import
 * - /jobs      → Job list
 * - /jobs/:id  → Job detail
 */
export function ImportExportMicroFrontend({ queryClient }: MicroFrontendProps) {
  const client = queryClient || defaultQueryClient

  return (
    <ErrorBoundary>
      <QueryClientProvider client={client}>
        <ToastProvider>
          <div className="import-export-content" style={{ fontFamily: 'inherit' }}>
            <Routes>
              {/* Default route - redirect to exports */}
              <Route index element={<Navigate to="exports" replace />} />

              {/* Export routes */}
              <Route path="exports" element={<ExportList />} />
              <Route path="exports/new" element={<ExportCreate />} />

              {/* Import routes */}
              <Route path="imports" element={<ImportList />} />
              <Route path="imports/new" element={<ImportCreate />} />

              {/* Job routes */}
              <Route path="jobs" element={<JobList />} />
              <Route path="jobs/:jobId" element={<JobDetail />} />

              {/* Catch-all - redirect to exports */}
              <Route path="*" element={<Navigate to="exports" replace />} />
            </Routes>
          </div>
        </ToastProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  )
}

export default ImportExportMicroFrontend
