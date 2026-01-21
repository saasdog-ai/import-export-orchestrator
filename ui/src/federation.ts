/**
 * Module Federation Exports
 *
 * This file provides all exports for host applications consuming
 * this UI as a micro-frontend via Module Federation.
 *
 * Usage in host app (vite.config.ts):
 * ```ts
 * federation({
 *   remotes: {
 *     importExportUI: 'http://localhost:3001/assets/remoteEntry.js',
 *   },
 * })
 * ```
 *
 * Then in your host app:
 * ```tsx
 * import { ImportExportProvider, ExportCreate, JobList } from 'importExportUI/federation'
 *
 * <ImportExportProvider config={{ apiBaseUrl: '/api/import-export', getAuthToken: () => token }}>
 *   <Routes>
 *     <Route path="/exports/new" element={<ExportCreate />} />
 *     <Route path="/jobs" element={<JobList />} />
 *   </Routes>
 * </ImportExportProvider>
 * ```
 */

// Configuration Provider
export {
  ImportExportProvider,
  useConfig,
  type ImportExportConfig,
} from './providers/ConfigProvider'

// API Client
export {
  createApiClient,
  ValidationError,
  AuthenticationError,
  type ApiClient,
  type ValidationErrorDetail,
} from './api/apiClient'

// Hook for API access
export { useApiClient } from './hooks/useApiClient'

// Page Components
export { ExportCreate } from './pages/exports/ExportCreate'
export { ExportList } from './pages/exports/ExportList'
export { ImportCreate } from './pages/imports/ImportCreate'
export { JobList } from './pages/jobs/JobList'
export { JobDetail } from './pages/jobs/JobDetail'
export { Dashboard } from './pages/Dashboard'

// Re-export types for convenience
export type {
  ExportEntity,
  ExportConfig,
  ExportRequest,
  ExportField,
  ExportFilter,
  ExportFilterGroup,
  ImportConfig,
  ImportField,
  ImportMode,
  JobDefinition,
  JobRun,
  JobType,
  JobStatus,
  SchemaEntity,
  SchemaField,
  SchemaResponse,
} from './types'
