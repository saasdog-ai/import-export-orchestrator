/**
 * Navigation utilities for micro-frontend context.
 *
 * When running as a Module Federation remote, the micro-frontend
 * may be mounted at various base paths (e.g., /import-export).
 * This hook provides navigation functions that work correctly
 * regardless of where the micro-frontend is mounted.
 */
import { useCallback } from "react"
import { useNavigate, useLocation } from "react-router-dom"

/**
 * Get the base path where the micro-frontend is mounted.
 * For example, if mounted at /import-export, and current URL is
 * /import-export/exports/new, this returns /import-export.
 */
function getBasePath(pathname: string): string {
  // Known internal routes that the micro-frontend defines
  const internalRoutes = [
    "/exports",
    "/imports",
    "/jobs",
  ]

  // Find where our internal routes start in the pathname
  for (const route of internalRoutes) {
    const idx = pathname.indexOf(route)
    if (idx > 0) {
      // Everything before this internal route is the base path
      return pathname.slice(0, idx)
    }
    if (idx === 0) {
      // No base path - micro-frontend is at root
      return ""
    }
  }

  // If we can't determine the base path, try to infer from common patterns
  // Check if pathname contains known base paths
  const commonBases = ["/import-export"]
  for (const base of commonBases) {
    if (pathname.startsWith(base)) {
      return base
    }
  }

  // Fallback: no base path
  return ""
}

/**
 * Hook that provides navigation functions that work correctly
 * in both standalone and micro-frontend contexts.
 */
export function useMicroFrontendNavigation() {
  const navigate = useNavigate()
  const location = useLocation()
  const basePath = getBasePath(location.pathname)

  /**
   * Navigate to a path within the micro-frontend.
   * @param path - The internal path (e.g., "/jobs/123", "/exports")
   * @param options - Navigation options
   */
  const navigateTo = useCallback(
    (path: string, options?: { replace?: boolean }) => {
      // Ensure path starts with /
      const normalizedPath = path.startsWith("/") ? path : `/${path}`
      // Construct full path
      const fullPath = `${basePath}${normalizedPath}`
      navigate(fullPath, options)
    },
    [navigate, basePath]
  )

  /**
   * Navigate to the jobs detail page.
   */
  const navigateToJob = useCallback(
    (jobId: string, options?: { replace?: boolean }) => {
      navigateTo(`/jobs/${jobId}`, options)
    },
    [navigateTo]
  )

  /**
   * Navigate to the exports list.
   */
  const navigateToExports = useCallback(
    (options?: { replace?: boolean }) => {
      navigateTo("/exports", options)
    },
    [navigateTo]
  )

  /**
   * Navigate to the imports list.
   */
  const navigateToImports = useCallback(
    (options?: { replace?: boolean }) => {
      navigateTo("/imports", options)
    },
    [navigateTo]
  )

  /**
   * Navigate to the jobs list.
   */
  const navigateToJobs = useCallback(
    (options?: { replace?: boolean }) => {
      navigateTo("/jobs", options)
    },
    [navigateTo]
  )

  /**
   * Navigate back (relative navigation).
   */
  const navigateBack = useCallback(() => {
    navigate(-1)
  }, [navigate])

  return {
    basePath,
    navigateTo,
    navigateToJob,
    navigateToExports,
    navigateToImports,
    navigateToJobs,
    navigateBack,
  }
}
