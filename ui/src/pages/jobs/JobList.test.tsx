import { describe, it, expect } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@/test/test-utils'
import { JobList } from './JobList'
import { server } from '@/test/setup'
import { HttpResponse, http } from 'msw'

describe('JobList', () => {
  it('should render the jobs heading', async () => {
    render(<JobList />)
    expect(screen.getByText('Jobs')).toBeInTheDocument()
    expect(
      screen.getByText('Manage your import and export job definitions')
    ).toBeInTheDocument()
  })

  it('should render filter dropdowns', async () => {
    render(<JobList />)
    expect(screen.getByDisplayValue('All Types')).toBeInTheDocument()
    expect(screen.getByDisplayValue('All Entities')).toBeInTheDocument()
  })

  it('should render date range filters', async () => {
    render(<JobList />)
    expect(screen.getByText('Created From')).toBeInTheDocument()
    expect(screen.getByText('Created To')).toBeInTheDocument()
  })

  it('should show empty state when no jobs', async () => {
    render(<JobList />)
    await waitFor(() => {
      expect(screen.getByText('No jobs found')).toBeInTheDocument()
    })
  })

  it('should display jobs when available', async () => {
    server.use(
      http.get('/api/jobs', () => {
        return HttpResponse.json({
          items: [
            {
              id: '1',
              client_id: '00000000-0000-0000-0000-000000000000',
              name: 'Test Export Job',
              job_type: 'export',
              export_config: { entity: 'bill', fields: [{ field: 'id' }] },
              enabled: true,
              created_at: '2024-01-01T00:00:00Z',
              updated_at: '2024-01-01T00:00:00Z',
            },
          ],
          total: 1,
          page: 1,
          page_size: 20,
          total_pages: 1,
        })
      })
    )

    render(<JobList />)
    await waitFor(() => {
      expect(screen.getByText('Test Export Job')).toBeInTheDocument()
    })
  })

  it('should filter by job type', async () => {
    render(<JobList />)
    const typeSelect = screen.getByDisplayValue('All Types')
    fireEvent.change(typeSelect, { target: { value: 'export' } })
    expect(typeSelect).toHaveValue('export')
  })

  it('should filter by entity', async () => {
    render(<JobList />)
    const entitySelect = screen.getByDisplayValue('All Entities')
    fireEvent.change(entitySelect, { target: { value: 'bill' } })
    expect(entitySelect).toHaveValue('bill')
  })

  it('should show Clear Filters button when filters are active', async () => {
    render(<JobList />)

    // Initially, no clear filters button
    expect(screen.queryByText('Clear Filters')).not.toBeInTheDocument()

    // Apply a filter
    const typeSelect = screen.getByDisplayValue('All Types')
    fireEvent.change(typeSelect, { target: { value: 'export' } })

    // Now the button should appear
    await waitFor(() => {
      expect(screen.getByText('Clear Filters')).toBeInTheDocument()
    })
  })

  it('should render pagination when multiple pages', async () => {
    server.use(
      http.get('/api/jobs', () => {
        return HttpResponse.json({
          items: Array(20).fill({
            id: '1',
            client_id: '00000000-0000-0000-0000-000000000000',
            name: 'Test Job',
            job_type: 'export',
            export_config: { entity: 'bill', fields: [{ field: 'id' }] },
            enabled: true,
            created_at: '2024-01-01T00:00:00Z',
            updated_at: '2024-01-01T00:00:00Z',
          }).map((job, i) => ({ ...job, id: String(i) })),
          total: 50,
          page: 1,
          page_size: 20,
          total_pages: 3,
        })
      })
    )

    render(<JobList />)
    await waitFor(() => {
      expect(screen.getByText('Page 1 of 3 (50 total jobs)')).toBeInTheDocument()
      expect(screen.getByText('Previous')).toBeInTheDocument()
      expect(screen.getByText('Next')).toBeInTheDocument()
    })
  })

  it('should render New Export and New Import buttons', () => {
    render(<JobList />)
    expect(screen.getByRole('link', { name: /New Export/i })).toHaveAttribute(
      'href',
      '/exports/new'
    )
    expect(screen.getByRole('link', { name: /New Import/i })).toHaveAttribute(
      'href',
      '/imports/new'
    )
  })
})
