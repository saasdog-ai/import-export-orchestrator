import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * Format a date string or Date object to a localized date and time string.
 * @param date - The date to format
 * @returns Formatted date and time string (e.g., "1/15/2024, 3:30:45 PM")
 */
export function formatDateTime(date: string | Date): string {
  return new Date(date).toLocaleString()
}

/**
 * Format a date string or Date object to a localized date string.
 * @param date - The date to format
 * @returns Formatted date string (e.g., "1/15/2024")
 */
export function formatDate(date: string | Date): string {
  return new Date(date).toLocaleDateString()
}

/**
 * Format a date string or Date object to a localized time string.
 * @param date - The date to format
 * @returns Formatted time string (e.g., "3:30:45 PM")
 */
export function formatTime(date: string | Date): string {
  return new Date(date).toLocaleTimeString()
}

/**
 * Format a date to a relative time string (e.g., "2 hours ago").
 * @param date - The date to format
 * @returns Relative time string
 */
export function formatRelativeTime(date: string | Date): string {
  const now = new Date()
  const then = new Date(date)
  const diffMs = now.getTime() - then.getTime()
  const diffSeconds = Math.floor(diffMs / 1000)
  const diffMinutes = Math.floor(diffSeconds / 60)
  const diffHours = Math.floor(diffMinutes / 60)
  const diffDays = Math.floor(diffHours / 24)

  if (diffSeconds < 60) {
    return "just now"
  } else if (diffMinutes < 60) {
    return `${diffMinutes} minute${diffMinutes !== 1 ? "s" : ""} ago`
  } else if (diffHours < 24) {
    return `${diffHours} hour${diffHours !== 1 ? "s" : ""} ago`
  } else if (diffDays < 7) {
    return `${diffDays} day${diffDays !== 1 ? "s" : ""} ago`
  } else {
    return formatDate(date)
  }
}

/**
 * Capitalize the first letter of a string.
 * @param str - The string to capitalize
 * @returns Capitalized string
 */
export function capitalize(str: string): string {
  if (!str) return str
  return str.charAt(0).toUpperCase() + str.slice(1)
}
