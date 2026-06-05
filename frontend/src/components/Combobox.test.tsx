import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { Combobox } from './Combobox'

const CITIES = ['תל אביב', 'חיפה', 'חולון']

describe('Combobox', () => {
  it('shows all options on focus', () => {
    render(<Combobox value="" options={CITIES} onSelect={() => {}} placeholder="עיר" />)
    fireEvent.focus(screen.getByPlaceholderText('עיר'))
    expect(screen.getByText('תל אביב')).toBeInTheDocument()
    expect(screen.getByText('חיפה')).toBeInTheDocument()
  })

  it('filters options as the user types', () => {
    render(<Combobox value="" options={CITIES} onSelect={() => {}} placeholder="עיר" />)
    const input = screen.getByPlaceholderText('עיר')
    fireEvent.focus(input)
    fireEvent.change(input, { target: { value: 'חי' } })
    expect(screen.getByText('חיפה')).toBeInTheDocument()
    expect(screen.queryByText('תל אביב')).not.toBeInTheDocument()
  })

  it('calls onSelect when an option is clicked', () => {
    const onSelect = vi.fn()
    render(<Combobox value="" options={CITIES} onSelect={onSelect} placeholder="עיר" />)
    fireEvent.focus(screen.getByPlaceholderText('עיר'))
    fireEvent.mouseDown(screen.getByText('חולון'))
    expect(onSelect).toHaveBeenCalledWith('חולון')
  })

  it('clear button resets the value', () => {
    const onSelect = vi.fn()
    render(<Combobox value="תל אביב" options={CITIES} onSelect={onSelect} placeholder="עיר" />)
    fireEvent.click(screen.getByLabelText('נקה'))
    expect(onSelect).toHaveBeenCalledWith('')
  })

  it('shows empty text when no options match', () => {
    render(<Combobox value="" options={CITIES} onSelect={() => {}} placeholder="עיר" emptyText="אין" />)
    const input = screen.getByPlaceholderText('עיר')
    fireEvent.focus(input)
    fireEvent.change(input, { target: { value: 'zzz' } })
    expect(screen.getByText('אין')).toBeInTheDocument()
  })

  it('is disabled when disabled prop is set', () => {
    render(<Combobox value="" options={CITIES} onSelect={() => {}} placeholder="עיר" disabled />)
    expect(screen.getByPlaceholderText('עיר')).toBeDisabled()
  })

  it('commits an in-range option when the list shrinks after the active index was set', () => {
    const onSelect = vi.fn()
    const { rerender } = render(
      <Combobox value="" options={CITIES} onSelect={onSelect} placeholder="עיר" />,
    )
    const input = screen.getByPlaceholderText('עיר')
    fireEvent.focus(input)
    fireEvent.keyDown(input, { key: 'ArrowDown' }) // active -> 1
    fireEvent.keyDown(input, { key: 'ArrowDown' }) // active -> 2 (last of 3)

    // Options shrink to a single item without a keystroke resetting `active`.
    rerender(<Combobox value="" options={['חיפה']} onSelect={onSelect} placeholder="עיר" />)
    fireEvent.keyDown(input, { key: 'Enter' })

    // Must commit the valid in-range option, never undefined.
    expect(onSelect).toHaveBeenCalledWith('חיפה')
  })
})
