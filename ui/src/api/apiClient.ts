/**
 * Configurable API Client for Import/Export UI
 *
 * This module provides API functions that use configuration from the ConfigProvider.
 * It supports both hook-based usage (recommended) and standalone usage.
 */

import type {
  ExportPreviewResponse,
  ExportRequest,
  ExportResultResponse,
  ImportExecuteRequest,
  ImportPreviewRequest,
  ImportPreviewResponse,
  ImportRequestUploadResponse,
  ImportUploadResponse,
  JobDefinition,
  JobDefinitionClone,
  JobDefinitionCreate,
  JobDefinitionUpdate,
  JobRun,
  JobsQueryParams,
  PaginatedResponse,
  SchemaResponse,
} from '@/types'
import type { ImportExportConfig } from '@/providers/ConfigProvider'

/**
 * Validation error with detailed error information
 */
export interface ValidationErrorDetail {
  row?: number
  field?: string
  message: string
}

export class ValidationError extends Error {
  public readonly status: string
  public readonly validationErrors: ValidationErrorDetail[]
  public readonly errorCount: number

  constructor(
    message: string,
    validationErrors: ValidationErrorDetail[] = [],
    errorCount: number = 0
  ) {
    super(message)
    this.name = 'ValidationError'
    this.status = 'validation_failed'
    this.validationErrors = validationErrors
    this.errorCount = errorCount
  }
}

export class AuthenticationError extends Error {
  constructor(message: string = 'Authentication required') {
    super(message)
    this.name = 'AuthenticationError'
  }
}

/**
 * Create an API client with the given configuration
 */
export function createApiClient(config: ImportExportConfig) {
  const { apiBaseUrl, getAuthToken, onUnauthorized } = config

  function getAuthHeaders(): HeadersInit {
    const token = getAuthToken()
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    }
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }
    return headers
  }

  function getAuthTokenHeader(): string | null {
    const token = getAuthToken()
    return token ? `Bearer ${token}` : null
  }

  async function handleResponse<T>(response: Response): Promise<T> {
    if (response.status === 401) {
      onUnauthorized?.()
      throw new AuthenticationError('Session expired. Please log in again.')
    }
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }))
      throw new Error(error.detail || error.message || `HTTP ${response.status}`)
    }
    return response.json()
  }

  return {
    // Schema API
    async getSchema(): Promise<SchemaResponse> {
      const response = await fetch(`${apiBaseUrl}/schema/entities`, {
        headers: getAuthHeaders(),
      })
      return handleResponse<SchemaResponse>(response)
    },

    // Export API
    async createExport(request: ExportRequest): Promise<ExportResultResponse> {
      const response = await fetch(`${apiBaseUrl}/exports`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(request),
      })
      return handleResponse<ExportResultResponse>(response)
    },

    async previewExport(request: ExportRequest): Promise<ExportPreviewResponse> {
      const response = await fetch(`${apiBaseUrl}/exports/preview`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(request),
      })
      return handleResponse<ExportPreviewResponse>(response)
    },

    async getExportResult(runId: string): Promise<ExportResultResponse> {
      const response = await fetch(`${apiBaseUrl}/exports/${runId}/result`, {
        headers: getAuthHeaders(),
      })
      return handleResponse<ExportResultResponse>(response)
    },

    async getExportDownloadUrl(runId: string): Promise<{ download_url: string }> {
      const response = await fetch(`${apiBaseUrl}/exports/${runId}/download`, {
        headers: getAuthHeaders(),
      })
      return handleResponse<{ download_url: string }>(response)
    },

    // Import API
    async uploadImportFile(file: File, entity: string): Promise<ImportUploadResponse> {
      const contentType = file.type || 'text/csv'

      // Step 1: Request presigned upload URL
      const requestUploadResponse = await fetch(`${apiBaseUrl}/imports/request-upload`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          filename: file.name,
          entity,
          content_type: contentType,
        }),
      })

      if (!requestUploadResponse.ok) {
        const errorData = await requestUploadResponse.json().catch(() => ({ detail: 'Unknown error' }))
        throw new Error(errorData.detail || errorData.message || `HTTP ${requestUploadResponse.status}`)
      }

      const { upload_url, file_key } = await requestUploadResponse.json() as ImportRequestUploadResponse

      // Step 2: Upload file directly to cloud storage via presigned URL
      const uploadResponse = await fetch(upload_url, {
        method: 'PUT',
        body: file,
        headers: { 'Content-Type': contentType },
      })

      if (!uploadResponse.ok) {
        throw new Error(`Direct upload failed: HTTP ${uploadResponse.status}`)
      }

      // Step 3: Confirm upload and validate
      const confirmResponse = await fetch(`${apiBaseUrl}/imports/confirm-upload`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          file_key,
          entity,
        }),
      })

      if (!confirmResponse.ok) {
        const errorData = await confirmResponse.json().catch(() => ({ message: 'Unknown error' }))
        if (errorData.status === 'validation_failed' && errorData.validation_errors) {
          throw new ValidationError(
            errorData.message || 'File validation failed',
            errorData.validation_errors,
            errorData.error_count || errorData.validation_errors.length
          )
        }
        throw new Error(errorData.detail || errorData.message || `HTTP ${confirmResponse.status}`)
      }

      return confirmResponse.json()
    },

    async previewImport(request: ImportPreviewRequest): Promise<ImportPreviewResponse> {
      const response = await fetch(`${apiBaseUrl}/imports/preview`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(request),
      })
      return handleResponse<ImportPreviewResponse>(response)
    },

    async executeImport(
      request: ImportExecuteRequest
    ): Promise<{ job_id: string; run_id: string; status: string }> {
      const response = await fetch(`${apiBaseUrl}/imports/execute`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(request),
      })
      return handleResponse<{ job_id: string; run_id: string; status: string }>(response)
    },

    // Jobs API
    async getJobs(params: JobsQueryParams = {}): Promise<PaginatedResponse<JobDefinition>> {
      const searchParams = new URLSearchParams()
      if (params.page) searchParams.set('page', params.page.toString())
      if (params.page_size) searchParams.set('page_size', params.page_size.toString())
      if (params.job_type) searchParams.set('job_type', params.job_type)
      if (params.entity) searchParams.set('entity', params.entity)
      if (params.start_date) searchParams.set('start_date', params.start_date)
      if (params.end_date) searchParams.set('end_date', params.end_date)

      const queryString = searchParams.toString()
      const url = `${apiBaseUrl}/jobs${queryString ? `?${queryString}` : ''}`

      const response = await fetch(url, {
        headers: getAuthHeaders(),
      })
      return handleResponse<PaginatedResponse<JobDefinition>>(response)
    },

    async getJob(jobId: string): Promise<JobDefinition> {
      const response = await fetch(`${apiBaseUrl}/jobs/${jobId}`, {
        headers: getAuthHeaders(),
      })
      return handleResponse<JobDefinition>(response)
    },

    async createJob(job: JobDefinitionCreate): Promise<JobDefinition> {
      const response = await fetch(`${apiBaseUrl}/jobs`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(job),
      })
      return handleResponse<JobDefinition>(response)
    },

    async deleteJob(jobId: string): Promise<void> {
      const response = await fetch(`${apiBaseUrl}/jobs/${jobId}`, {
        method: 'DELETE',
        headers: getAuthHeaders(),
      })
      if (!response.ok) {
        throw new Error(`Failed to delete job: ${response.status}`)
      }
    },

    async updateJob(jobId: string, data: JobDefinitionUpdate): Promise<JobDefinition> {
      const response = await fetch(`${apiBaseUrl}/jobs/${jobId}`, {
        method: 'PUT',
        headers: getAuthHeaders(),
        body: JSON.stringify(data),
      })
      return handleResponse<JobDefinition>(response)
    },

    async cloneJob(jobId: string, data: JobDefinitionClone): Promise<JobDefinition> {
      const response = await fetch(`${apiBaseUrl}/jobs/${jobId}/clone`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(data),
      })
      return handleResponse<JobDefinition>(response)
    },

    async runJob(jobId: string): Promise<JobRun> {
      const response = await fetch(`${apiBaseUrl}/jobs/${jobId}/run`, {
        method: 'POST',
        headers: getAuthHeaders(),
      })
      return handleResponse<JobRun>(response)
    },

    async getJobRuns(jobId: string): Promise<JobRun[]> {
      const response = await fetch(`${apiBaseUrl}/jobs/${jobId}/runs`, {
        headers: getAuthHeaders(),
      })
      return handleResponse<JobRun[]>(response)
    },

    async getJobRun(jobId: string, runId: string): Promise<JobRun> {
      const response = await fetch(`${apiBaseUrl}/jobs/${jobId}/runs/${runId}`, {
        headers: getAuthHeaders(),
      })
      return handleResponse<JobRun>(response)
    },

    // Health API
    async checkHealth(): Promise<{ status: string }> {
      const response = await fetch(`${apiBaseUrl}/health`)
      return handleResponse<{ status: string }>(response)
    },
  }
}

/**
 * Type for the API client returned by createApiClient
 */
export type ApiClient = ReturnType<typeof createApiClient>
