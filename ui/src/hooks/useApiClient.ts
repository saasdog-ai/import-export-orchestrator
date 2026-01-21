/**
 * Hook to access the API client with configuration from ConfigProvider
 */

import { useMemo } from 'react'
import { useConfig } from '@/providers/ConfigProvider'
import { createApiClient, type ApiClient } from '@/api/apiClient'

/**
 * Hook to get an API client configured from the ImportExportProvider
 *
 * @example
 * ```tsx
 * function MyComponent() {
 *   const api = useApiClient()
 *
 *   const { data } = useQuery({
 *     queryKey: ['jobs'],
 *     queryFn: () => api.getJobs(),
 *   })
 * }
 * ```
 */
export function useApiClient(): ApiClient {
  const config = useConfig()

  const apiClient = useMemo(() => createApiClient(config), [config])

  return apiClient
}
