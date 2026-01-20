import { BrowserRouter, Routes, Route } from "react-router-dom"
import { Layout } from "@/components/Layout"
import { ErrorBoundary } from "@/components/ErrorBoundary"
import { ToastProvider } from "@/contexts/ToastContext"
import {
  Dashboard,
  ExportList,
  ExportCreate,
  ImportList,
  ImportCreate,
  JobList,
  JobDetail,
} from "@/pages"

function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <ToastProvider>
          <Layout>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/exports" element={<ExportList />} />
              <Route path="/exports/new" element={<ExportCreate />} />
              <Route path="/imports" element={<ImportList />} />
              <Route path="/imports/new" element={<ImportCreate />} />
              <Route path="/jobs" element={<JobList />} />
              <Route path="/jobs/:jobId" element={<JobDetail />} />
            </Routes>
          </Layout>
        </ToastProvider>
      </BrowserRouter>
    </ErrorBoundary>
  )
}

export default App
