/**
 * API Client for Import/Export UI
 *
 * This module provides backwards-compatible API functions for standalone usage.
 * For micro-frontend integration, use the useApiClient() hook instead.
 *
 * @see {@link ../hooks/useApiClient.ts} for hook-based usage
 * @see {@link ./apiClient.ts} for the configurable API client
 */

import { createApiClient, ValidationError, AuthenticationError } from './apiClient'
import type { ImportExportConfig } from '@/providers/ConfigProvider'

// Re-export types and errors for backwards compatibility
export { ValidationError, AuthenticationError }
export type { ValidationErrorDetail } from './apiClient'

// Default configuration for standalone mode
// Use VITE_API_URL if set (for S3 deployment), otherwise use /api (for proxy/CloudFront)
const defaultConfig: ImportExportConfig = {
  apiBaseUrl: import.meta.env.VITE_API_URL || '/api',
  getAuthToken: () => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('auth_token') || ''
    }
    return ''
  },
  onUnauthorized: () => {
    // Clear token on unauthorized
    if (typeof window !== 'undefined') {
      localStorage.removeItem('auth_token')
      localStorage.removeItem('client_id')
    }
    console.error('[Auth] Session expired or invalid. Please log in again.')
  },
}

// Create a default client instance for standalone usage
const defaultClient = createApiClient(defaultConfig)

// Export all API functions for backwards compatibility
// These use the default configuration (standalone mode)

// Schema API
export const getSchema = defaultClient.getSchema

// Export API
export const createExport = defaultClient.createExport
export const previewExport = defaultClient.previewExport
export const getExportResult = defaultClient.getExportResult
export const getExportDownloadUrl = defaultClient.getExportDownloadUrl

// Import API
export const uploadImportFile = defaultClient.uploadImportFile
export const previewImport = defaultClient.previewImport
export const executeImport = defaultClient.executeImport

// Jobs API
export const getJobs = defaultClient.getJobs
export const getJob = defaultClient.getJob
export const createJob = defaultClient.createJob
export const deleteJob = defaultClient.deleteJob
export const updateJob = defaultClient.updateJob
export const cloneJob = defaultClient.cloneJob
export const runJob = defaultClient.runJob
export const getJobRuns = defaultClient.getJobRuns
export const getJobRun = defaultClient.getJobRun

// Health API
export const checkHealth = defaultClient.checkHealth

// Also export the createApiClient for advanced usage
export { createApiClient }
