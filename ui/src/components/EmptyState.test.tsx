import { describe, it, expect } from 'vitest'
import { render, screen } from '@/test/test-utils'
import { EmptyState } from './EmptyState'

describe('EmptyState', () => {
  it('should render title', () => {
    render(<EmptyState title="No items found" />)
    expect(screen.getByText('No items found')).toBeInTheDocument()
  })

  it('should render description when provided', () => {
    render(
      <EmptyState
        title="No items"
        description="Create your first item to get started"
      />
    )
    expect(screen.getByText('Create your first item to get started')).toBeInTheDocument()
  })

  it('should not render description when not provided', () => {
    render(<EmptyState title="No items" />)
    expect(screen.queryByText(/Create your first/)).not.toBeInTheDocument()
  })

  it('should render icon when provided', () => {
    render(
      <EmptyState
        title="No items"
        icon={<span data-testid="test-icon">Icon</span>}
      />
    )
    expect(screen.getByTestId('test-icon')).toBeInTheDocument()
  })

  it('should render action when provided', () => {
    render(
      <EmptyState
        title="No items"
        action={<button>Create Item</button>}
      />
    )
    expect(screen.getByRole('button', { name: 'Create Item' })).toBeInTheDocument()
  })

  it('should apply custom className', () => {
    const { container } = render(
      <EmptyState title="No items" className="custom-class" />
    )
    expect(container.firstChild).toHaveClass('custom-class')
  })
})
