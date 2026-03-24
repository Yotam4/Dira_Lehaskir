import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { ListingCard } from './ListingCard'
import { mockListing } from '../test/fixtures'

describe('ListingCard', () => {
  it('renders title', () => {
    render(<ListingCard listing={mockListing} />)
    expect(screen.getByText('דירת 3 חדרים בתל אביב')).toBeInTheDocument()
  })

  it('renders price formatted with ₪', () => {
    render(<ListingCard listing={mockListing} />)
    expect(screen.getByText('₪5,500')).toBeInTheDocument()
  })

  it('renders rooms', () => {
    render(<ListingCard listing={mockListing} />)
    // Use regex anchored to start so it matches "3 חד׳" but not the title "דירת 3 חדרים..."
    expect(screen.getByText(/^\d+\.?\d* חד/)).toBeInTheDocument()
  })

  it('renders sqm', () => {
    render(<ListingCard listing={mockListing} />)
    expect(screen.getByText(/75/)).toBeInTheDocument()
  })

  it('renders neighborhood and city', () => {
    render(<ListingCard listing={mockListing} />)
    // Location div renders "neighborhood, city" — exact match avoids hitting the title
    expect(screen.getByText('לב העיר, תל אביב')).toBeInTheDocument()
  })

  it('renders source badge for yad2', () => {
    render(<ListingCard listing={mockListing} />)
    expect(screen.getByText('יד 2')).toBeInTheDocument()
  })

  it('renders external link when original_url is set', () => {
    render(<ListingCard listing={mockListing} />)
    const link = screen.getByRole('link', { name: /מקור/ })
    expect(link).toHaveAttribute('href', mockListing.original_url)
    expect(link).toHaveAttribute('target', '_blank')
  })

  it('does not render external link when no original_url', () => {
    render(<ListingCard listing={{ ...mockListing, original_url: null }} />)
    expect(screen.queryByRole('link')).not.toBeInTheDocument()
  })

  it('calls onClick when clicked', () => {
    const onClick = vi.fn()
    render(<ListingCard listing={mockListing} onClick={onClick} />)
    fireEvent.click(screen.getByText('דירת 3 חדרים בתל אביב'))
    expect(onClick).toHaveBeenCalledOnce()
  })

  it('does not crash when listing has no price, rooms, or sqm', () => {
    const sparse = { ...mockListing, price: null, rooms: null, sqm: null }
    render(<ListingCard listing={sparse} />)
    expect(screen.getByText('דירת 3 חדרים בתל אביב')).toBeInTheDocument()
  })
})
