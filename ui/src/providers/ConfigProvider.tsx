/**
 * Configuration Provider for Import/Export UI
 *
 * This provider allows host applications to inject configuration when using
 * this UI as a micro-frontend via Module Federation.
 *
 * Usage in host app:
 * ```tsx
 * import { ImportExportProvider } from 'importExportUI/Provider'
 *
 * <ImportExportProvider
 *   config={{
 *     apiBaseUrl: 'https://api.example.com',
 *     getAuthToken: () => myAuthService.getToken(),
 *     routePrefix: '/import-export',
 *   }}
 * >
 *   <ImportExportApp />
 * </ImportExportProvider>
 * ```
 */

import { createContext, useContext, useMemo, type ReactNode } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

/**
 * Configuration interface for the Import/Export UI
 */
export interface ImportExportConfig {
  /**
   * Base URL for the API (e.g., 'https://api.example.com' or '/api')
   * @default '/api'
   */
  apiBaseUrl: string

  /**
   * Function to retrieve the current auth token
   * Return empty string if no token (for unauthenticated requests)
   */
  getAuthToken: () => string

  /**
   * Optional route prefix for all routes (e.g., '/import-export')
   * Used when embedding in a host app with its own routing
   * @default ''
   */
  routePrefix?: string

  /**
   * Optional callback when user session expires (401 response)
   * Host app can use this to trigger re-authentication
   */
  onUnauthorized?: () => void

  /**
   * Optional client ID for multi-tenant scenarios
   * If not provided, the backend will determine from the auth token
   */
  clientId?: string
}

const ConfigContext = createContext<ImportExportConfig | null>(null)

// Default configuration for standalone mode
// Use VITE_API_URL if set (for S3 deployment), otherwise use /api (for proxy/CloudFront)
const defaultConfig: ImportExportConfig = {
  apiBaseUrl: import.meta.env.VITE_API_URL || '/api',
  getAuthToken: () => {
    // In standalone mode, try to get token from localStorage
    if (typeof window !== 'undefined') {
      return localStorage.getItem('auth_token') || ''
    }
    return ''
  },
  routePrefix: '',
  onUnauthorized: () => {
    console.warn('[ImportExport] Unauthorized - please implement onUnauthorized handler')
  },
}

/**
 * Hook to access the Import/Export configuration
 * @throws Error if used outside of ImportExportProvider
 */
export function useConfig(): ImportExportConfig {
  const context = useContext(ConfigContext)
  if (!context) {
    // Return default config if not in provider (standalone mode)
    return defaultConfig
  }
  return context
}

interface ImportExportProviderProps {
  /**
   * Configuration for the Import/Export UI
   * If not provided, uses default standalone configuration
   */
  config?: Partial<ImportExportConfig>

  /**
   * Optional existing QueryClient from host app
   * If provided, shared dependencies can be optimized
   */
  queryClient?: QueryClient

  children: ReactNode
}

// Create a default QueryClient for standalone use
const defaultQueryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      retry: 1,
    },
  },
})

/**
 * Provider component for Import/Export UI configuration
 *
 * Wrap your Import/Export components with this provider to inject
 * configuration from your host application.
 */
export function ImportExportProvider({
  config,
  queryClient,
  children,
}: ImportExportProviderProps) {
  // Merge provided config with defaults
  const mergedConfig = useMemo<ImportExportConfig>(
    () => ({
      ...defaultConfig,
      ...config,
    }),
    [config]
  )

  const client = queryClient || defaultQueryClient

  return (
    <ConfigContext.Provider value={mergedConfig}>
      <QueryClientProvider client={client}>
        {children}
      </QueryClientProvider>
    </ConfigContext.Provider>
  )
}

/**
 * Export the context for advanced use cases
 */
export { ConfigContext }
