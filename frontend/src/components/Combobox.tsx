import { useEffect, useRef, useState } from 'react'

interface ComboboxProps {
  value: string
  onSelect: (value: string) => void
  options: string[]
  placeholder?: string
  disabled?: boolean
  /** Allow committing arbitrary typed text (not just an option). */
  allowFreeText?: boolean
  emptyText?: string
  'aria-label'?: string
}

/**
 * Lightweight accessible combobox: a text input with a filtered dropdown of
 * suggestions. Selecting a suggestion (or, with allowFreeText, pressing Enter)
 * commits the value. Used for the city/neighborhood pickers.
 */
export function Combobox({
  value,
  onSelect,
  options,
  placeholder,
  disabled,
  allowFreeText = false,
  emptyText = 'אין תוצאות',
  'aria-label': ariaLabel,
}: ComboboxProps) {
  const [query, setQuery] = useState(value)
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(0)
  const wrapRef = useRef<HTMLDivElement>(null)

  // Keep the input text in sync when the value is changed externally (e.g. cleared).
  useEffect(() => setQuery(value), [value])

  // Close on outside click.
  useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', onDoc)
    return () => document.removeEventListener('mousedown', onDoc)
  }, [])

  const q = query.trim().toLowerCase()
  const filtered = q ? options.filter((o) => o.toLowerCase().includes(q)) : options

  const commit = (val: string) => {
    onSelect(val)
    setQuery(val)
    setOpen(false)
  }

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (!open && (e.key === 'ArrowDown' || e.key === 'ArrowUp')) {
      setOpen(true)
      return
    }
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setActive((a) => Math.min(a + 1, filtered.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setActive((a) => Math.max(a - 1, 0))
    } else if (e.key === 'Enter') {
      e.preventDefault()
      if (filtered[active]) commit(filtered[active])
      else if (allowFreeText) commit(query)
    } else if (e.key === 'Escape') {
      setOpen(false)
    }
  }

  return (
    <div ref={wrapRef} style={{ position: 'relative', marginBottom: 8 }}>
      <input
        aria-label={ariaLabel}
        role="combobox"
        aria-expanded={open}
        autoComplete="off"
        disabled={disabled}
        style={{ ...inputStyle, background: disabled ? '#f3f4f6' : '#fff' }}
        placeholder={placeholder}
        value={query}
        onChange={(e) => {
          setQuery(e.target.value)
          setOpen(true)
          setActive(0)
          if (allowFreeText) onSelect(e.target.value)
        }}
        onFocus={() => setOpen(true)}
        onKeyDown={onKeyDown}
      />
      {query && !disabled && (
        <button
          type="button"
          aria-label="נקה"
          onClick={() => commit('')}
          style={clearBtnStyle}
        >
          ×
        </button>
      )}
      {open && !disabled && (
        <ul role="listbox" style={listStyle}>
          {filtered.length === 0 ? (
            <li style={{ ...optionStyle, color: '#9ca3af', cursor: 'default' }}>{emptyText}</li>
          ) : (
            filtered.map((opt, i) => (
              <li
                key={opt}
                role="option"
                aria-selected={i === active}
                onMouseDown={(e) => {
                  e.preventDefault()
                  commit(opt)
                }}
                onMouseEnter={() => setActive(i)}
                style={{ ...optionStyle, background: i === active ? '#eff6ff' : '#fff' }}
              >
                {opt}
              </li>
            ))
          )}
        </ul>
      )}
    </div>
  )
}

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '6px 8px',
  borderRadius: 6,
  border: '1px solid #d1d5db',
  fontSize: 13,
}

const clearBtnStyle: React.CSSProperties = {
  position: 'absolute',
  insetInlineStart: 6,
  top: '50%',
  transform: 'translateY(-50%)',
  border: 'none',
  background: 'none',
  color: '#9ca3af',
  cursor: 'pointer',
  fontSize: 16,
  lineHeight: 1,
  padding: 0,
}

const listStyle: React.CSSProperties = {
  position: 'absolute',
  zIndex: 20,
  insetInlineStart: 0,
  insetInlineEnd: 0,
  top: '100%',
  marginTop: 2,
  maxHeight: 220,
  overflowY: 'auto',
  background: '#fff',
  border: '1px solid #d1d5db',
  borderRadius: 6,
  boxShadow: '0 4px 12px rgba(0,0,0,0.08)',
  listStyle: 'none',
  padding: 4,
  margin: 0,
}

const optionStyle: React.CSSProperties = {
  padding: '6px 8px',
  borderRadius: 4,
  fontSize: 13,
  cursor: 'pointer',
}
