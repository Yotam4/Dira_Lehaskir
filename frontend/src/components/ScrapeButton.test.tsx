import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ScrapeButton } from './ScrapeButton'

vi.mock('../hooks/useGeo', () => ({
  useCities: () => ({ data: ['תל אביב', 'חיפה'] }),
}))

vi.mock('../api/client', () => ({
  triggerScrape: vi.fn(),
  fetchScrapeRun: vi.fn(),
}))

import { triggerScrape } from '../api/client'

describe('ScrapeButton', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('sends the selected sources and city (not a hardcoded list)', async () => {
    ;(triggerScrape as any).mockResolvedValue({ run_id: 'r1', status: 'queued', triggered_at: 'now' })

    render(<ScrapeButton filters={{ city: 'תל אביב' }} />)
    fireEvent.click(screen.getByText('סרוק עכשיו')) // open dialog
    fireEvent.click(screen.getByText('סרוק')) // submit

    await waitFor(() => expect(triggerScrape).toHaveBeenCalledTimes(1))
    const arg = (triggerScrape as any).mock.calls[0][0]
    expect(arg.sources).toEqual(['yad2', 'madlan']) // facebook is disabled by default
    expect(arg.filters.city).toBe('תל אביב')
  })

  it('surfaces the real server error detail', async () => {
    ;(triggerScrape as any).mockRejectedValue({ response: { data: { detail: 'Unknown sources: [bad]' } } })

    render(<ScrapeButton filters={{ city: 'תל אביב' }} />)
    fireEvent.click(screen.getByText('סרוק עכשיו'))
    fireEvent.click(screen.getByText('סרוק'))

    await waitFor(() => expect(screen.getByText(/Unknown sources/)).toBeInTheDocument())
  })

  it('does not submit when all sources are unchecked', async () => {
    render(<ScrapeButton filters={{ city: 'תל אביב' }} />)
    fireEvent.click(screen.getByText('סרוק עכשיו'))
    // uncheck the two enabled sources
    fireEvent.click(screen.getByLabelText(/יד 2/))
    fireEvent.click(screen.getByLabelText(/מדלן/))
    fireEvent.click(screen.getByText('סרוק'))
    expect(triggerScrape).not.toHaveBeenCalled()
  })
})
