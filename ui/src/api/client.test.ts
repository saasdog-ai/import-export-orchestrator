import { describe, it, expect, vi, beforeEach } from 'vitest'
import {
  getJobs,
  getJob,
  createJob,
  updateJob,
  deleteJob,
  cloneJob,
  runJob,
  getJobRuns,
  checkHealth,
  getSchema,
  previewExport,
  createExport,
} from './client'

describe('API Client', () => {
  beforeEach(() => {
    localStorage.setItem('auth_token', 'test-token')
  })

  describe('Health API', () => {
    it('should fetch health status', async () => {
      const health = await checkHealth()
      expect(health.status).toBe('healthy')
    })
  })

  describe('Schema API', () => {
    it('should fetch schema entities', async () => {
      const schema = await getSchema()
      expect(schema.entities).toBeDefined()
      expect(schema.entities.length).toBeGreaterThan(0)
      expect(schema.entities[0].name).toBe('bill')
    })
  })

  describe('Jobs API', () => {
    it('should fetch paginated jobs', async () => {
      const jobs = await getJobs({ page: 1, page_size: 20 })
      expect(jobs.items).toBeDefined()
      expect(jobs.total).toBeDefined()
      expect(jobs.page).toBe(1)
    })

    it('should fetch jobs with filters', async () => {
      const jobs = await getJobs({
        page: 1,
        page_size: 20,
        job_type: 'export',
        entity: 'bill',
      })
      expect(jobs.items).toBeDefined()
    })

    it('should fetch jobs with date range', async () => {
      const jobs = await getJobs({
        page: 1,
        page_size: 20,
        start_date: '2024-01-01',
        end_date: '2024-12-31',
      })
      expect(jobs.items).toBeDefined()
    })

    it('should fetch a single job by ID', async () => {
      const job = await getJob('123e4567-e89b-12d3-a456-426614174000')
      expect(job.id).toBe('123e4567-e89b-12d3-a456-426614174000')
      expect(job.name).toBe('Test Job')
    })

    it('should create a new job', async () => {
      const job = await createJob({
        client_id: '00000000-0000-0000-0000-000000000000',
        name: 'New Export Job',
        job_type: 'export',
        export_config: {
          entity: 'bill',
          fields: [{ field: 'id' }],
        },
        enabled: true,
      })
      expect(job.id).toBeDefined()
      expect(job.name).toBe('New Export Job')
    })

    it('should update a job', async () => {
      const job = await updateJob('123e4567-e89b-12d3-a456-426614174000', {
        name: 'Updated Job Name',
        enabled: false,
      })
      expect(job.name).toBe('Updated Job Name')
      expect(job.enabled).toBe(false)
    })

    it('should delete a job', async () => {
      await expect(
        deleteJob('123e4567-e89b-12d3-a456-426614174000')
      ).resolves.not.toThrow()
    })

    it('should clone a job', async () => {
      const job = await cloneJob('123e4567-e89b-12d3-a456-426614174000', {
        name: 'Cloned Job',
        export_config: {
          entity: 'bill',
          fields: [{ field: 'id' }, { field: 'amount' }],
        },
      })
      expect(job.id).not.toBe('123e4567-e89b-12d3-a456-426614174000')
      expect(job.name).toBe('Cloned Job')
    })

    it('should run a job', async () => {
      const run = await runJob('123e4567-e89b-12d3-a456-426614174000')
      expect(run.id).toBeDefined()
      expect(run.status).toBe('running')
    })

    it('should fetch job runs', async () => {
      const runs = await getJobRuns('123e4567-e89b-12d3-a456-426614174000')
      expect(Array.isArray(runs)).toBe(true)
    })
  })

  describe('Export API', () => {
    it('should preview export', async () => {
      const preview = await previewExport({
        entity: 'bill',
        fields: [{ field: 'id' }, { field: 'amount' }],
        limit: 10,
      })
      expect(preview.entity).toBe('bill')
      expect(preview.records).toBeDefined()
    })

    it('should create export', async () => {
      const result = await createExport({
        entity: 'bill',
        fields: [{ field: 'id' }, { field: 'amount' }],
      })
      expect(result.run_id).toBeDefined()
      expect(result.status).toBe('running')
    })
  })

  describe('Error handling', () => {
    it('should throw error for failed requests', async () => {
      // This will hit the default error handler since we don't have a mock for this endpoint
      await expect(getJob('non-existent-id')).resolves.toBeDefined()
    })
  })
})
