// Entity types
// ExportEntity is now a string to support dynamic entity types from the schema API
// SaaS integrators can define their own entity types without modifying this codebase
export type ExportEntity = string

export type JobType = 'import' | 'export'

export type JobStatus = 'pending' | 'running' | 'succeeded' | 'failed' | 'cancelled'

// Schema types
export interface SchemaField {
  name: string
  type: string
  label: string
  required?: boolean
  description?: string
}

export interface SchemaRelationshipField {
  name: string
  type: string
  label: string
}

export interface SchemaRelationship {
  name: string
  label: string
  entity: string
  type: string
  fields: SchemaRelationshipField[]
}

export interface SchemaEntity {
  name: string
  label: string
  description?: string
  fields: SchemaField[]
  relationships: SchemaRelationship[]
}

export interface SchemaResponse {
  entities: SchemaEntity[]
}

// Export types
export interface ExportField {
  field: string
  as?: string
  format?: string
}

export interface ExportFilter {
  field: string
  operator: string
  value: unknown
}

export interface ExportFilterGroup {
  operator: 'and' | 'or' | 'not'
  filters: ExportFilter[]
  groups?: ExportFilterGroup[]
}

export interface ExportConfig {
  entity: ExportEntity
  fields: ExportField[]
  filters?: ExportFilterGroup
  sort?: Array<{ field: string; direction: 'asc' | 'desc' }>
  limit?: number
  offset?: number
}

export interface ExportRequest {
  entity: ExportEntity
  fields: ExportField[]
  filters?: ExportFilterGroup
  sort?: Array<{ field: string; direction: 'asc' | 'desc' }>
  limit?: number
  offset?: number
}

export interface ExportPreviewResponse {
  entity: ExportEntity
  count: number
  records: Record<string, unknown>[]
  limit: number
  offset: number
}

export interface ExportResultResponse {
  run_id: string
  entity: ExportEntity
  status: JobStatus
  result_metadata?: Record<string, unknown>
  error_message?: string
}

// Import types
export type ImportMode = 'create' | 'update' | 'upsert'

export interface ImportField {
  source: string
  target: string
}

export interface ImportPreviewRequest {
  file_path: string
  entity: ExportEntity
  field_mappings?: ImportField[]
  import_mode?: ImportMode
  match_key?: string
}

export interface ImportPreviewRecordError {
  field: string
  message: string
}

export interface ImportPreviewRecord {
  row: number
  data: Record<string, unknown>
  is_valid: boolean
  errors: ImportPreviewRecordError[]
  action?: string  // Per-record action if _action column present
}

export interface ImportPreviewResponse {
  file_path: string
  entity: ExportEntity
  total_records: number
  valid_count: number
  invalid_count: number
  has_action_column: boolean  // Whether file has _action column for per-record actions
  records: ImportPreviewRecord[]
}

export interface ImportExecuteRequest {
  file_path: string
  entity: ExportEntity
  field_mappings?: ImportField[]
  import_mode?: ImportMode
  match_key?: string
}

export interface ImportUploadResponse {
  status: string
  message: string
  file_path: string
  entity: string
  filename: string
  columns?: string[]
  has_action_column?: boolean
}

// Job types
export interface ImportConfig {
  source: string
  entity: ExportEntity
  fields?: ImportField[]
  options: Record<string, unknown>
}

export interface JobRunSummary {
  id: string
  status: JobStatus
  started_at?: string
  completed_at?: string
  error_message?: string
}

export interface JobDefinition {
  id: string
  client_id: string
  name: string
  job_type: JobType
  export_config?: ExportConfig
  import_config?: ImportConfig
  cron_schedule?: string
  enabled: boolean
  created_at: string
  updated_at: string
  last_run?: JobRunSummary | null
}

export interface JobRun {
  id: string
  job_id: string
  status: JobStatus
  started_at?: string
  completed_at?: string
  error_message?: string
  result_metadata?: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface JobDefinitionCreate {
  client_id: string
  name: string
  job_type: JobType
  export_config?: ExportConfig
  import_config?: ImportConfig
  cron_schedule?: string
  enabled?: boolean
}

export interface JobDefinitionUpdate {
  name?: string
  cron_schedule?: string | null
  enabled?: boolean
}

export interface JobDefinitionClone {
  name: string
  export_config?: ExportConfig
  import_config?: ImportConfig
  cron_schedule?: string
  enabled?: boolean
}

// API Response types
export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface JobsQueryParams {
  page?: number
  page_size?: number
  job_type?: 'import' | 'export'
  entity?: string
  start_date?: string
  end_date?: string
}

export interface ErrorResponse {
  error: string
  detail?: string
}

export interface HealthResponse {
  status: string
  timestamp: string
}
