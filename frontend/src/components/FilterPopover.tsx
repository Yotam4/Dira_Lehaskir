import { useEffect, useRef, useState, type ReactNode } from 'react'

interface FilterPopoverProps {
  /** Label shown when no value is selected. */
  label: string
  /** Active-value summary; when set, the pill renders in the active style. */
  summary?: string | null
  children: ReactNode
  onClear?: () => void
  width?: number
}

/**
 * A Madlan-style filter "pill": a button that opens a dropdown panel below it.
 * Closes on outside click. Shows a summary + clear (×) when a value is active.
 */
export function FilterPopover({ label, summary, children, onClear, width = 280 }: FilterPopoverProps) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', onDoc)
    return () => document.removeEventListener('mousedown', onDoc)
  }, [])

  const active = !!summary

  return (
    <div ref={ref} style={{ position: 'relative' }}>
      <button onClick={() => setOpen((o) => !o)} style={pillStyle(active || open)} type="button">
        <span style={{ whiteSpace: 'nowrap' }}>{active ? summary : label}</span>
        {active && onClear ? (
          <span
            role="button"
            aria-label={`נקה ${label}`}
            onClick={(e) => { e.stopPropagation(); onClear() }}
            style={{ fontWeight: 700, fontSize: 14, lineHeight: 1, marginInlineStart: 2 }}
          >
            ×
          </span>
        ) : (
          <span style={{ fontSize: 9, opacity: 0.55 }}>▾</span>
        )}
      </button>
      {open && (
        <div style={{ ...panelStyle, width }}>
          {children}
        </div>
      )}
    </div>
  )
}

function pillStyle(active: boolean): React.CSSProperties {
  return {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 6,
    padding: '7px 12px',
    borderRadius: 999,
    border: `1px solid ${active ? '#1d4ed8' : '#d1d5db'}`,
    background: active ? '#eff6ff' : '#fff',
    color: active ? '#1d4ed8' : '#374151',
    cursor: 'pointer',
    fontSize: 13,
    fontWeight: 500,
  }
}

const panelStyle: React.CSSProperties = {
  position: 'absolute',
  top: '100%',
  insetInlineStart: 0,
  marginTop: 6,
  zIndex: 40,
  background: '#fff',
  border: '1px solid #e5e7eb',
  borderRadius: 12,
  boxShadow: '0 10px 30px rgba(0,0,0,0.12)',
  padding: 14,
}
