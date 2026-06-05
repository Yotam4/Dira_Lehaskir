import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { ScrapeButton } from './ScrapeButton'

vi.mock('../hooks/useGeo', () => ({
  useCities: () => ({ data: ['תל אביב', 'חיפה'] }),
}))

vi.mock('../api/client', () => ({
  triggerScrape: vi.fn(),
  fetchScrapeRun: vi.fn(),
}))

import { triggerScrape, fetchScrapeRun } from '../api/client'

describe('ScrapeButton', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.useRealTimers()
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

  it('polls until completed, shows the result, and calls onComplete', async () => {
    vi.useFakeTimers()
    ;(triggerScrape as any).mockResolvedValue({ run_id: 'r1', status: 'queued', triggered_at: 'now' })
    ;(fetchScrapeRun as any)
      .mockResolvedValueOnce({ status: 'running' })
      .mockResolvedValueOnce({ status: 'completed', listings_new: 3, listings_found: 9 })
    const onComplete = vi.fn()

    render(<ScrapeButton filters={{ city: 'תל אביב' }} onComplete={onComplete} />)
    fireEvent.click(screen.getByText('סרוק עכשיו'))
    fireEvent.click(screen.getByText('סרוק'))

    await vi.advanceTimersByTimeAsync(0) // let triggerScrape resolve + start polling
    await vi.advanceTimersByTimeAsync(3000) // poll 1 -> running
    await vi.advanceTimersByTimeAsync(3000) // poll 2 -> completed

    expect(onComplete).toHaveBeenCalledTimes(1)
    expect(screen.getByText(/הושלם/)).toBeInTheDocument()
  })

  it('surfaces a failed run with its error_message', async () => {
    vi.useFakeTimers()
    ;(triggerScrape as any).mockResolvedValue({ run_id: 'r1', status: 'queued', triggered_at: 'now' })
    ;(fetchScrapeRun as any).mockResolvedValueOnce({ status: 'failed', error_message: 'הסריקה קרסה' })

    render(<ScrapeButton filters={{ city: 'תל אביב' }} />)
    fireEvent.click(screen.getByText('סרוק עכשיו'))
    fireEvent.click(screen.getByText('סרוק'))

    await vi.advanceTimersByTimeAsync(0)
    await vi.advanceTimersByTimeAsync(3000)

    expect(screen.getByText(/הסריקה קרסה/)).toBeInTheDocument()
  })
})
