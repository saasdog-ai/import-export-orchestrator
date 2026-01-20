import '@testing-library/jest-dom'
import { afterAll, afterEach, beforeAll, beforeEach, vi } from 'vitest'
import { cleanup } from '@testing-library/react'
import { setupServer } from 'msw/node'
import { HttpResponse, http } from 'msw'

// Mock the auth module for tests
vi.mock('@/lib/auth', () => ({
  getAuthToken: () => 'test-token',
  getClientId: () => '00000000-0000-0000-0000-000000000000',
  handleUnauthorized: vi.fn(),
  AuthenticationError: class AuthenticationError extends Error {
    constructor(message: string) {
      super(message)
      this.name = 'AuthenticationError'
    }
  },
}))

// Mock handlers for API endpoints
export const handlers = [
  http.get('/api/health', () => {
    return HttpResponse.json({ status: 'healthy' })
  }),
  http.get('/api/schema/entities', () => {
    return HttpResponse.json({
      entities: [
        {
          name: 'bill',
          label: 'Bills',
          fields: [
            { name: 'id', type: 'uuid', label: 'ID' },
            { name: 'amount', type: 'number', label: 'Amount' },
            { name: 'date', type: 'date', label: 'Date' },
            { name: 'status', type: 'string', label: 'Status' },
          ],
          relationships: [
            {
              name: 'vendor',
              label: 'Vendor',
              entity: 'vendor',
              type: 'many_to_one',
              fields: [{ name: 'name', type: 'string', label: 'Vendor Name' }],
            },
          ],
        },
        {
          name: 'vendor',
          label: 'Vendors',
          fields: [
            { name: 'id', type: 'uuid', label: 'ID' },
            { name: 'name', type: 'string', label: 'Name' },
          ],
          relationships: [],
        },
      ],
    })
  }),
  http.get('/api/jobs', () => {
    return HttpResponse.json({
      items: [],
      total: 0,
      page: 1,
      page_size: 20,
      total_pages: 1,
    })
  }),
  http.get('/api/jobs/:jobId', ({ params }) => {
    return HttpResponse.json({
      id: params.jobId,
      client_id: '00000000-0000-0000-0000-000000000000',
      name: 'Test Job',
      job_type: 'export',
      export_config: {
        entity: 'bill',
        fields: [{ field: 'id' }, { field: 'amount', as: 'Total' }],
      },
      enabled: true,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    })
  }),
  http.get('/api/jobs/:jobId/runs', () => {
    return HttpResponse.json([])
  }),
  http.post('/api/jobs', async ({ request }) => {
    const body = await request.json() as Record<string, unknown>
    return HttpResponse.json({
      id: '123e4567-e89b-12d3-a456-426614174000',
      ...body,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    })
  }),
  http.put('/api/jobs/:jobId', async ({ params, request }) => {
    const body = await request.json() as Record<string, unknown>
    return HttpResponse.json({
      id: params.jobId,
      client_id: '00000000-0000-0000-0000-000000000000',
      name: body.name || 'Test Job',
      job_type: 'export',
      enabled: body.enabled ?? true,
      cron_schedule: body.cron_schedule,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    })
  }),
  http.delete('/api/jobs/:jobId', () => {
    return new HttpResponse(null, { status: 204 })
  }),
  http.post('/api/jobs/:jobId/clone', async ({ request }) => {
    const body = await request.json() as Record<string, unknown>
    return HttpResponse.json({
      id: '123e4567-e89b-12d3-a456-426614174001',
      client_id: '00000000-0000-0000-0000-000000000000',
      name: body.name,
      job_type: 'export',
      export_config: body.export_config,
      enabled: body.enabled ?? true,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    })
  }),
  http.post('/api/jobs/:jobId/run', ({ params }) => {
    return HttpResponse.json({
      id: '123e4567-e89b-12d3-a456-426614174002',
      job_id: params.jobId,
      status: 'running',
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    })
  }),
  http.post('/api/exports/preview', () => {
    return HttpResponse.json({
      entity: 'bill',
      count: 1,
      records: [{ id: '1', amount: 100 }],
      limit: 10,
      offset: 0,
    })
  }),
  http.post('/api/exports', () => {
    return HttpResponse.json({
      run_id: '123e4567-e89b-12d3-a456-426614174003',
      entity: 'bill',
      status: 'running',
    })
  }),
]

export const server = setupServer(...handlers)

// Start server before all tests
beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))

// Reset handlers after each test
afterEach(() => {
  cleanup()
  server.resetHandlers()
})

// Close server after all tests
afterAll(() => server.close())
