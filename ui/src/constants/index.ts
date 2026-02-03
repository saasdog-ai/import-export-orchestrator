/**
 * Shared constants for the application.
 * Centralizing these values makes them easier to maintain and update.
 */

// Entity types available in the system
export const ENTITIES = ["bill", "invoice", "vendor", "project"] as const
export type EntityType = (typeof ENTITIES)[number]

// API configuration
export const API_CONFIG = {
  BASE_URL: "/api",
  HEALTH_CHECK_INTERVAL: 30000, // 30 seconds
  JOB_RUNS_POLL_INTERVAL: 5000, // 5 seconds
  SCHEMA_STALE_TIME: 5 * 60 * 1000, // 5 minutes
} as const

// Pagination defaults
export const PAGINATION = {
  DEFAULT_PAGE_SIZE: 20,
  PAGE_SIZE_OPTIONS: [10, 20, 50, 100],
} as const

// Job status values
export const JOB_STATUS = {
  PENDING: "pending",
  RUNNING: "running",
  SUCCEEDED: "succeeded",
  FAILED: "failed",
  CANCELLED: "cancelled",
} as const

// Job types
export const JOB_TYPE = {
  EXPORT: "export",
  IMPORT: "import",
} as const

// Filter operators
export const FILTER_OPERATORS = [
  { value: "eq", label: "equals" },
  { value: "ne", label: "not equals" },
  { value: "gt", label: "greater than" },
  { value: "gte", label: "greater than or equal" },
  { value: "lt", label: "less than" },
  { value: "lte", label: "less than or equal" },
  { value: "contains", label: "contains" },
  { value: "starts_with", label: "starts with" },
  { value: "ends_with", label: "ends with" },
  { value: "in", label: "in list" },
  { value: "between", label: "between" },
] as const

// Relative date options for filters
export const RELATIVE_DATE_OPTIONS = [
  { value: "relative:last_7_days", label: "Last 7 days" },
  { value: "relative:last_30_days", label: "Last 30 days" },
  { value: "relative:last_90_days", label: "Last 90 days" },
  { value: "relative:this_month", label: "This month" },
  { value: "relative:last_month", label: "Last month" },
  { value: "relative:this_quarter", label: "This quarter" },
  { value: "relative:last_quarter", label: "Last quarter" },
  { value: "relative:this_year", label: "This year" },
  { value: "relative:last_year", label: "Last year" },
] as const
