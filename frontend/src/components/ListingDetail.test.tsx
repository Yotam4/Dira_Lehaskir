import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { ListingDetail } from './ListingDetail'
import { mockListing, mockListingWithImages } from '../test/fixtures'

describe('ListingDetail', () => {
  it('renders title', () => {
    render(<ListingDetail listing={mockListing} onClose={vi.fn()} />)
    expect(screen.getByText('דירת 3 חדרים בתל אביב')).toBeInTheDocument()
  })

  it('renders price stat', () => {
    render(<ListingDetail listing={mockListing} onClose={vi.fn()} />)
    expect(screen.getByText('₪5,500')).toBeInTheDocument()
  })

  it('renders rooms stat', () => {
    render(<ListingDetail listing={mockListing} onClose={vi.fn()} />)
    expect(screen.getByText('3')).toBeInTheDocument()
  })

  it('renders description excerpt', () => {
    render(<ListingDetail listing={mockListing} onClose={vi.fn()} />)
    expect(screen.getByText(/דירה מרווחת/)).toBeInTheDocument()
  })

  it('renders source link', () => {
    render(<ListingDetail listing={mockListing} onClose={vi.fn()} />)
    const link = screen.getByRole('link', { name: /לצפייה במקור/ })
    expect(link).toHaveAttribute('href', mockListing.original_url)
  })

  it('calls onClose when close button clicked', () => {
    const onClose = vi.fn()
    render(<ListingDetail listing={mockListing} onClose={onClose} />)
    // The close button wraps an X icon — find by its accessible role
    const closeBtn = screen.getByRole('button')
    fireEvent.click(closeBtn)
    expect(onClose).toHaveBeenCalledOnce()
  })

  it('does not render image when images array is empty', () => {
    render(<ListingDetail listing={mockListing} onClose={vi.fn()} />)
    expect(screen.queryByRole('img')).not.toBeInTheDocument()
  })

  it('renders first image when images are present', () => {
    render(<ListingDetail listing={mockListingWithImages} onClose={vi.fn()} />)
    const img = screen.getByRole('img')
    expect(img).toHaveAttribute('src', 'https://example.com/img1.jpg')
  })

  it('shows image counter when multiple images exist', () => {
    render(<ListingDetail listing={mockListingWithImages} onClose={vi.fn()} />)
    expect(screen.getByText('1 / 2')).toBeInTheDocument()
  })

  it('does not show image counter for single image', () => {
    const singleImg = { ...mockListing, images: ['https://example.com/img1.jpg'] }
    render(<ListingDetail listing={singleImg} onClose={vi.fn()} />)
    expect(screen.queryByText(/\/ 1/)).not.toBeInTheDocument()
  })

  it('renders city and neighborhood', () => {
    render(<ListingDetail listing={mockListing} onClose={vi.fn()} />)
    // Location line: "address · neighborhood · city" — לב העיר is unique to this div
    const locationEl = screen.getByText(/לב העיר/)
    expect(locationEl.textContent).toContain('תל אביב')
  })
})
