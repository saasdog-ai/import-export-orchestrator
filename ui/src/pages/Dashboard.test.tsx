import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@/test/test-utils'
import { Dashboard } from './Dashboard'
import { server } from '@/test/setup'
import { HttpResponse, http } from 'msw'

describe('Dashboard', () => {
  it('should render the dashboard heading', async () => {
    render(<Dashboard />)
    expect(screen.getByText('Dashboard')).toBeInTheDocument()
    expect(screen.getByText('Manage your data imports and exports')).toBeInTheDocument()
  })

  it('should render quick action cards', async () => {
    render(<Dashboard />)
    expect(screen.getByText('Export Data')).toBeInTheDocument()
    expect(screen.getByText('Import Data')).toBeInTheDocument()
    expect(screen.getByText('Scheduled Jobs')).toBeInTheDocument()
  })

  it('should display system status as online when healthy', async () => {
    render(<Dashboard />)
    await waitFor(() => {
      expect(screen.getByText('Online')).toBeInTheDocument()
    })
  })

  it('should display system status as offline when unhealthy', async () => {
    server.use(
      http.get('/api/health', () => {
        return HttpResponse.json({ status: 'unhealthy' })
      })
    )

    render(<Dashboard />)
    await waitFor(() => {
      expect(screen.getByText('Offline')).toBeInTheDocument()
    })
  })

  it('should display job counts', async () => {
    server.use(
      http.get('/api/jobs', ({ request }) => {
        const url = new URL(request.url)
        const jobType = url.searchParams.get('job_type')

        if (jobType === 'export') {
          return HttpResponse.json({
            items: [],
            total: 5,
            page: 1,
            page_size: 1,
            total_pages: 5,
          })
        } else if (jobType === 'import') {
          return HttpResponse.json({
            items: [],
            total: 3,
            page: 1,
            page_size: 1,
            total_pages: 3,
          })
        }

        return HttpResponse.json({
          items: [],
          total: 8,
          page: 1,
          page_size: 5,
          total_pages: 2,
        })
      })
    )

    render(<Dashboard />)
    await waitFor(() => {
      expect(screen.getByText('8')).toBeInTheDocument() // Total jobs
      expect(screen.getByText('5')).toBeInTheDocument() // Export jobs
      expect(screen.getByText('3')).toBeInTheDocument() // Import jobs
    })
  })

  it('should display recent jobs section', async () => {
    render(<Dashboard />)
    expect(screen.getByText('Recent Jobs')).toBeInTheDocument()
  })

  it('should show empty state when no jobs exist', async () => {
    render(<Dashboard />)
    await waitFor(() => {
      expect(screen.getByText('No jobs yet')).toBeInTheDocument()
    })
  })

  it('should render create export link', () => {
    render(<Dashboard />)
    const exportLinks = screen.getAllByRole('link', { name: /Create Export/i })
    expect(exportLinks.length).toBeGreaterThan(0)
    expect(exportLinks[0]).toHaveAttribute('href', '/exports/new')
  })

  it('should render start import link', () => {
    render(<Dashboard />)
    const importLinks = screen.getAllByRole('link', { name: /Start Import/i })
    expect(importLinks.length).toBeGreaterThan(0)
    expect(importLinks[0]).toHaveAttribute('href', '/imports/new')
  })
})
