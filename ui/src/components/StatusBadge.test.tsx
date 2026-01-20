import { describe, it, expect } from 'vitest'
import { render, screen } from '@/test/test-utils'
import { StatusBadge } from './StatusBadge'
import type { JobStatus } from '@/types'

describe('StatusBadge', () => {
  const statuses: Array<{ status: JobStatus; label: string }> = [
    { status: 'pending', label: 'Pending' },
    { status: 'running', label: 'Running' },
    { status: 'succeeded', label: 'Succeeded' },
    { status: 'failed', label: 'Failed' },
    { status: 'cancelled', label: 'Cancelled' },
  ]

  statuses.forEach(({ status, label }) => {
    it(`should render "${label}" for status "${status}"`, () => {
      render(<StatusBadge status={status} />)
      expect(screen.getByText(label)).toBeInTheDocument()
    })
  })

  it('should handle unknown status gracefully', () => {
    // @ts-expect-error - testing unknown status
    render(<StatusBadge status="unknown" />)
    expect(screen.getByText('unknown')).toBeInTheDocument()
  })
})
