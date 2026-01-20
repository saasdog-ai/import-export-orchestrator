import type {
  ExportPreviewResponse,
  ExportRequest,
  ExportResultResponse,
  ImportExecuteRequest,
  ImportPreviewRequest,
  ImportPreviewResponse,
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
import { getAuthToken, handleUnauthorized, AuthenticationError } from '@/lib/auth'

const API_BASE = '/api'

/**
 * Get headers for authenticated API requests.
 * Uses the auth module for secure token retrieval.
 */
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

/**
 * Get auth token for non-JSON requests (e.g., file uploads)
 */
function getAuthTokenHeader(): string | null {
  const token = getAuthToken()
  return token ? `Bearer ${token}` : null
}

/**
 * Handle API response with proper error handling.
 * Handles 401 responses by triggering re-authentication.
 */
async function handleResponse<T>(response: Response): Promise<T> {
  if (response.status === 401) {
    handleUnauthorized()
    throw new AuthenticationError('Session expired. Please log in again.')
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }))
    throw new Error(error.detail || error.message || `HTTP ${response.status}`)
  }
  return response.json()
}

// Schema API
export async function getSchema(): Promise<SchemaResponse> {
  const response = await fetch(`${API_BASE}/schema/entities`, {
    headers: getAuthHeaders(),
  })
  return handleResponse<SchemaResponse>(response)
}

// Export API
export async function createExport(request: ExportRequest): Promise<ExportResultResponse> {
  const response = await fetch(`${API_BASE}/exports`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(request),
  })
  return handleResponse<ExportResultResponse>(response)
}

export async function previewExport(request: ExportRequest): Promise<ExportPreviewResponse> {
  const response = await fetch(`${API_BASE}/exports/preview`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(request),
  })
  return handleResponse<ExportPreviewResponse>(response)
}

export async function getExportResult(runId: string): Promise<ExportResultResponse> {
  const response = await fetch(`${API_BASE}/exports/${runId}/result`, {
    headers: getAuthHeaders(),
  })
  return handleResponse<ExportResultResponse>(response)
}

export async function getExportDownloadUrl(runId: string): Promise<{ download_url: string }> {
  const response = await fetch(`${API_BASE}/exports/${runId}/download`, {
    headers: getAuthHeaders(),
  })
  return handleResponse<{ download_url: string }>(response)
}

// Import API
export async function uploadImportFile(
  file: File,
  entity: string
): Promise<ImportUploadResponse> {
  const formData = new FormData()
  formData.append('file', file)

  const authHeader = getAuthTokenHeader()
  const headers: HeadersInit = {}
  if (authHeader) {
    headers['Authorization'] = authHeader
  }

  const response = await fetch(`${API_BASE}/imports/upload?entity=${entity}`, {
    method: 'POST',
    headers,
    body: formData,
  })
  return handleResponse<ImportUploadResponse>(response)
}

export async function previewImport(
  request: ImportPreviewRequest
): Promise<ImportPreviewResponse> {
  const response = await fetch(`${API_BASE}/imports/preview`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(request),
  })
  return handleResponse<ImportPreviewResponse>(response)
}

export async function executeImport(
  request: ImportExecuteRequest
): Promise<{ job_id: string; run_id: string; status: string }> {
  const response = await fetch(`${API_BASE}/imports/execute`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(request),
  })
  return handleResponse<{ job_id: string; run_id: string; status: string }>(response)
}

// Jobs API
export async function getJobs(
  params: JobsQueryParams = {}
): Promise<PaginatedResponse<JobDefinition>> {
  const searchParams = new URLSearchParams()
  if (params.page) searchParams.set('page', params.page.toString())
  if (params.page_size) searchParams.set('page_size', params.page_size.toString())
  if (params.job_type) searchParams.set('job_type', params.job_type)
  if (params.entity) searchParams.set('entity', params.entity)
  if (params.start_date) searchParams.set('start_date', params.start_date)
  if (params.end_date) searchParams.set('end_date', params.end_date)

  const queryString = searchParams.toString()
  const url = `${API_BASE}/jobs${queryString ? `?${queryString}` : ''}`

  const response = await fetch(url, {
    headers: getAuthHeaders(),
  })
  return handleResponse<PaginatedResponse<JobDefinition>>(response)
}

export async function getJob(jobId: string): Promise<JobDefinition> {
  const response = await fetch(`${API_BASE}/jobs/${jobId}`, {
    headers: getAuthHeaders(),
  })
  return handleResponse<JobDefinition>(response)
}

export async function createJob(job: JobDefinitionCreate): Promise<JobDefinition> {
  const response = await fetch(`${API_BASE}/jobs`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(job),
  })
  return handleResponse<JobDefinition>(response)
}

export async function deleteJob(jobId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/jobs/${jobId}`, {
    method: 'DELETE',
    headers: getAuthHeaders(),
  })
  if (!response.ok) {
    throw new Error(`Failed to delete job: ${response.status}`)
  }
}

export async function updateJob(
  jobId: string,
  data: JobDefinitionUpdate
): Promise<JobDefinition> {
  const response = await fetch(`${API_BASE}/jobs/${jobId}`, {
    method: 'PUT',
    headers: getAuthHeaders(),
    body: JSON.stringify(data),
  })
  return handleResponse<JobDefinition>(response)
}

export async function cloneJob(
  jobId: string,
  data: JobDefinitionClone
): Promise<JobDefinition> {
  const response = await fetch(`${API_BASE}/jobs/${jobId}/clone`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(data),
  })
  return handleResponse<JobDefinition>(response)
}

export async function runJob(jobId: string): Promise<JobRun> {
  const response = await fetch(`${API_BASE}/jobs/${jobId}/run`, {
    method: 'POST',
    headers: getAuthHeaders(),
  })
  return handleResponse<JobRun>(response)
}

export async function getJobRuns(jobId: string): Promise<JobRun[]> {
  const response = await fetch(`${API_BASE}/jobs/${jobId}/runs`, {
    headers: getAuthHeaders(),
  })
  return handleResponse<JobRun[]>(response)
}

export async function getJobRun(jobId: string, runId: string): Promise<JobRun> {
  const response = await fetch(`${API_BASE}/jobs/${jobId}/runs/${runId}`, {
    headers: getAuthHeaders(),
  })
  return handleResponse<JobRun>(response)
}

// Health API
export async function checkHealth(): Promise<{ status: string }> {
  const response = await fetch(`${API_BASE}/health`)
  return handleResponse<{ status: string }>(response)
}
