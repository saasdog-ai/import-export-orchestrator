import * as React from "react"
import { ToastContainer, type Toast, type ToastVariant } from "@/components/ui/toast"

interface ToastContextValue {
  toasts: Toast[]
  addToast: (toast: Omit<Toast, "id">) => void
  removeToast: (id: string) => void
  success: (title: string, description?: string) => void
  error: (title: string, description?: string) => void
  warning: (title: string, description?: string) => void
  info: (title: string, description?: string) => void
}

const ToastContext = React.createContext<ToastContextValue | null>(null)

const DEFAULT_DURATION = 5000

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = React.useState<Toast[]>([])

  const removeToast = React.useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  const addToast = React.useCallback(
    (toast: Omit<Toast, "id">) => {
      const id = crypto.randomUUID()
      const duration = toast.duration ?? DEFAULT_DURATION

      setToasts((prev) => [...prev, { ...toast, id }])

      // Auto-remove after duration
      if (duration > 0) {
        setTimeout(() => {
          removeToast(id)
        }, duration)
      }
    },
    [removeToast]
  )

  const createToastHelper = React.useCallback(
    (variant: ToastVariant) => (title: string, description?: string) => {
      addToast({ title, description, variant })
    },
    [addToast]
  )

  const value = React.useMemo(
    () => ({
      toasts,
      addToast,
      removeToast,
      success: createToastHelper("success"),
      error: createToastHelper("error"),
      warning: createToastHelper("warning"),
      info: createToastHelper("info"),
    }),
    [toasts, addToast, removeToast, createToastHelper]
  )

  return (
    <ToastContext.Provider value={value}>
      {children}
      <ToastContainer toasts={toasts} onClose={removeToast} />
    </ToastContext.Provider>
  )
}

export function useToast() {
  const context = React.useContext(ToastContext)
  if (!context) {
    throw new Error("useToast must be used within a ToastProvider")
  }
  return context
}
