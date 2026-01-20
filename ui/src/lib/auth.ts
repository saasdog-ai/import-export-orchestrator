/**
 * Authentication utilities for the application.
 *
 * SECURITY NOTES:
 * - In production, tokens should be managed via httpOnly cookies set by the backend
 * - This module provides a client-side abstraction that can be swapped for a more
 *   secure implementation (e.g., using a proper auth provider like Auth0, Clerk, etc.)
 * - localStorage is used here for development convenience but is NOT recommended
 *   for production as it's vulnerable to XSS attacks
 */

const AUTH_TOKEN_KEY = 'auth_token'
const CLIENT_ID_KEY = 'client_id'

// Check if we're in development mode
const isDevelopment = import.meta.env.DEV

/**
 * Authentication error thrown when no valid token is available
 */
export class AuthenticationError extends Error {
  constructor(message: string = 'Authentication required') {
    super(message)
    this.name = 'AuthenticationError'
  }
}

/**
 * Get the current auth token.
 * Throws AuthenticationError if no token is available and not in development mode.
 */
export function getAuthToken(): string {
  const token = localStorage.getItem(AUTH_TOKEN_KEY)

  if (!token) {
    if (isDevelopment) {
      // In development, warn but allow requests to proceed
      // The backend should handle this appropriately
      console.warn(
        '[Auth] No auth token found. In development mode, requests will proceed without authentication. ' +
        'Set a token with setAuthToken() or configure the backend to accept unauthenticated requests.'
      )
      return ''
    }
    throw new AuthenticationError('No authentication token available. Please log in.')
  }

  return token
}

/**
 * Set the auth token (typically after login)
 */
export function setAuthToken(token: string): void {
  if (!token) {
    throw new Error('Token cannot be empty')
  }
  localStorage.setItem(AUTH_TOKEN_KEY, token)
}

/**
 * Clear the auth token (typically on logout)
 */
export function clearAuthToken(): void {
  localStorage.removeItem(AUTH_TOKEN_KEY)
  localStorage.removeItem(CLIENT_ID_KEY)
}

/**
 * Check if user is authenticated
 */
export function isAuthenticated(): boolean {
  return !!localStorage.getItem(AUTH_TOKEN_KEY)
}

/**
 * Get the current client ID from stored user info
 */
export function getClientId(): string | null {
  return localStorage.getItem(CLIENT_ID_KEY)
}

/**
 * Set the client ID (typically extracted from JWT after login)
 */
export function setClientId(clientId: string): void {
  if (!clientId) {
    throw new Error('Client ID cannot be empty')
  }
  localStorage.setItem(CLIENT_ID_KEY, clientId)
}

/**
 * Handle 401 Unauthorized responses
 * Can be extended to trigger a login redirect
 */
export function handleUnauthorized(): void {
  clearAuthToken()
  // In a real app, you would redirect to login or trigger a re-auth flow
  console.error('[Auth] Session expired or invalid. Please log in again.')
}
