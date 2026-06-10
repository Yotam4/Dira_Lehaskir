import { useEffect, useRef, useState } from 'react'
import { RefreshCw, CheckCircle, XCircle } from 'lucide-react'
import { triggerScrape, fetchScrapeRun } from '../api/client'
import type { SearchFilters, ListingSource } from '../types/listing'
import { SOURCE_LABELS } from '../types/listing'
import { Combobox } from './Combobox'
import { useCities } from '../hooks/useGeo'

interface ScrapeButtonProps {
  filters: SearchFilters
  onComplete?: () => void
}

type Phase = 'idle' | 'triggering' | 'polling' | 'done' | 'error'

// Facebook needs credentials + the optional scraper extra, so it's off by default.
const SCRAPEABLE: { id: ListingSource; disabled?: boolean; note?: string }[] = [
  { id: 'yad2' },
  { id: 'madlan' },
  { id: 'facebook', disabled: true, note: 'דורש הגדרת חשבון' },
]

export function ScrapeButton({ filters, onComplete }: ScrapeButtonProps) {
  const [open, setOpen] = useState(false)
  const [phase, setPhase] = useState<Phase>('idle')
  const [message, setMessage] = useState<string | null>(null)
  const [city, setCity] = useState(filters.city ?? '')
  const [sources, setSources] = useState<ListingSource[]>(['yad2', 'madlan'])
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const { data: cities = [] } = useCities()

  useEffect(() => () => { if (intervalRef.current) clearInterval(intervalRef.current) }, [])
  useEffect(() => { setCity(filters.city ?? '') }, [filters.city])

  const stopPolling = () => {
    if (intervalRef.current) { clearInterval(intervalRef.current); intervalRef.current = null }
  }

  const startPolling = (runId: string) => {
    const MAX_POLLS = 100 // 100 × 3 s = 5 min max
    let polls = 0
    intervalRef.current = setInterval(async () => {
      polls++
      if (polls > MAX_POLLS) {
        stopPolling(); setPhase('error'); setMessage('הסריקה נתקעה — נסה שוב'); return
      }
      try {
        const run = await fetchScrapeRun(runId)
        if (run.status === 'completed') {
          stopPolling(); setPhase('done')
          setMessage(`הושלם ✓  ${run.listings_new ?? 0} חדשות · ${run.listings_found ?? 0} סה"כ`)
          onComplete?.()
        } else if (run.status === 'failed') {
          stopPolling(); setPhase('error')
          setMessage(run.error_message ? `שגיאה: ${run.error_message}` : 'הסריקה נכשלה')
        }
        // 'queued' / 'running' → keep polling
      } catch {
        // network hiccup — keep polling (will time out via MAX_POLLS)
      }
    }, 3000)
  }

  const toggleSource = (s: ListingSource) =>
    setSources((prev) => (prev.includes(s) ? prev.filter((x) => x !== s) : [...prev, s]))

  const submit = async () => {
    if (phase === 'polling' || sources.length === 0) return
    stopPolling()
    setPhase('triggering')
    setMessage(null)
    try {
      const result = await triggerScrape({
        sources,
        filters: {
          city: city ?? '',
          neighborhood: filters.neighborhood ?? '',
          price_min: filters.price_min,
          price_max: filters.price_max,
          rooms_min: filters.rooms_min,
          rooms_max: filters.rooms_max,
        },
      })
      setOpen(false)
      setPhase('polling')
      setMessage('סורק…')
      startPolling(result.run_id)
    } catch (err: any) {
      setPhase('error')
      const detail = err?.response?.data?.detail
      setMessage(detail ? `שגיאה: ${typeof detail === 'string' ? detail : JSON.stringify(detail)}` : 'שגיאה בהפעלת הסריקה')
    }
  }

  const busy = phase === 'triggering' || phase === 'polling'
  const btnBg = phase === 'error' ? '#dc2626' : phase === 'done' ? '#16a34a' : busy ? '#9ca3af' : '#1d4ed8'

  return (
    <div style={{ position: 'relative' }}>
      <button
        onClick={() => (busy ? null : setOpen((v) => !v))}
        disabled={busy}
        style={{
          display: 'flex', alignItems: 'center', gap: 6, padding: '8px 16px', borderRadius: 8,
          border: 'none', background: btnBg, color: '#fff', fontWeight: 600,
          cursor: busy ? 'not-allowed' : 'pointer', fontSize: 14,
        }}
      >
        {phase === 'done' ? <CheckCircle size={16} /> : phase === 'error' ? <XCircle size={16} />
          : <RefreshCw size={16} style={{ animation: busy ? 'spin 1s linear infinite' : 'none' }} />}
        {busy ? 'סורק…' : 'סרוק עכשיו'}
      </button>

      {message && (
        <div style={{ marginTop: 6, fontSize: 12, color: phase === 'error' ? '#dc2626' : '#6b7280' }}>
          {message}
        </div>
      )}

      {open && !busy && (
        <div style={dialogStyle}>
          <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>סריקת דירות חדשות</div>

          <label style={lblStyle}>עיר</label>
          <Combobox
            aria-label="עיר לסריקה"
            value={city}
            options={cities}
            allowFreeText
            placeholder="בחר עיר לסריקה..."
            onSelect={setCity}
          />

          <label style={lblStyle}>מקורות</label>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4, marginBottom: 10 }}>
            {SCRAPEABLE.map(({ id, disabled, note }) => (
              <label key={id} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, color: disabled ? '#9ca3af' : '#374151' }}>
                <input
                  type="checkbox"
                  disabled={disabled}
                  checked={sources.includes(id)}
                  onChange={() => toggleSource(id)}
                />
                {SOURCE_LABELS[id]}
                {note && <span style={{ fontSize: 11, color: '#9ca3af' }}>({note})</span>}
              </label>
            ))}
          </div>

          <div style={{ display: 'flex', gap: 6, justifyContent: 'flex-start' }}>
            <button
              onClick={submit}
              disabled={sources.length === 0}
              style={{ padding: '6px 14px', borderRadius: 6, border: 'none', background: sources.length ? '#1d4ed8' : '#9ca3af', color: '#fff', fontWeight: 600, fontSize: 13, cursor: sources.length ? 'pointer' : 'not-allowed' }}
            >
              סרוק
            </button>
            <button
              onClick={() => setOpen(false)}
              style={{ padding: '6px 14px', borderRadius: 6, border: '1px solid #d1d5db', background: '#fff', color: '#374151', fontSize: 13, cursor: 'pointer' }}
            >
              ביטול
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

const dialogStyle: React.CSSProperties = {
  position: 'absolute',
  top: '100%',
  insetInlineEnd: 0,
  marginTop: 6,
  zIndex: 30,
  width: 260,
  background: '#fff',
  border: '1px solid #e5e7eb',
  borderRadius: 10,
  boxShadow: '0 8px 24px rgba(0,0,0,0.12)',
  padding: 12,
}
const lblStyle: React.CSSProperties = { display: 'block', fontSize: 12, fontWeight: 500, marginBottom: 4, color: '#374151' }
