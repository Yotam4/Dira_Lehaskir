import { useEffect, useRef, useState } from 'react'
import { RefreshCw, CheckCircle, XCircle } from 'lucide-react'
import { triggerScrape, fetchScrapeRun } from '../api/client'
import type { SearchFilters } from '../types/listing'

interface ScrapeButtonProps {
  filters: SearchFilters
  onComplete?: () => void
}

type Phase = 'idle' | 'triggering' | 'polling' | 'done' | 'error'

export function ScrapeButton({ filters, onComplete }: ScrapeButtonProps) {
  const [phase, setPhase] = useState<Phase>('idle')
  const [message, setMessage] = useState<string | null>(null)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // Clean up interval on unmount
  useEffect(() => () => { if (intervalRef.current) clearInterval(intervalRef.current) }, [])

  const stopPolling = () => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
    }
  }

  const startPolling = (runId: string) => {
    intervalRef.current = setInterval(async () => {
      try {
        const run = await fetchScrapeRun(runId)
        if (run.status === 'completed') {
          stopPolling()
          setPhase('done')
          setMessage(`הושלם ✓  ${run.listings_new ?? 0} חדשות · ${run.listings_found ?? 0} סה"כ`)
          onComplete?.()
        } else if (run.status === 'failed') {
          stopPolling()
          setPhase('error')
          setMessage(run.error_message ? `שגיאה: ${run.error_message}` : 'הסריקה נכשלה')
        }
        // status === 'running' → keep polling
      } catch {
        // network hiccup — keep polling
      }
    }, 3000)
  }

  const handleClick = async () => {
    if (phase === 'polling') return
    stopPolling()
    setPhase('triggering')
    setMessage(null)

    try {
      const result = await triggerScrape({
        sources: ['yad2', 'madlan', 'facebook'],
        filters: {
          city: filters.city ?? '',
          neighborhood: filters.neighborhood ?? '',
          lat: filters.lat,
          lng: filters.lng,
          radius_m: filters.radius_m,
          polygon_geojson: filters.polygon_geojson,
          price_min: filters.price_min,
          price_max: filters.price_max,
          rooms_min: filters.rooms_min,
          rooms_max: filters.rooms_max,
        },
      })
      setPhase('polling')
      setMessage('סורק…')
      startPolling(result.run_id)
    } catch {
      setPhase('error')
      setMessage('שגיאה בהפעלת הסריקה')
    }
  }

  const busy = phase === 'triggering' || phase === 'polling'
  const btnBg = phase === 'error' ? '#dc2626' : phase === 'done' ? '#16a34a' : busy ? '#9ca3af' : '#1d4ed8'

  return (
    <div>
      <button
        onClick={handleClick}
        disabled={busy}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          padding: '8px 16px',
          borderRadius: 8,
          border: 'none',
          background: btnBg,
          color: '#fff',
          fontWeight: 600,
          cursor: busy ? 'not-allowed' : 'pointer',
          fontSize: 14,
        }}
      >
        {phase === 'done' ? (
          <CheckCircle size={16} />
        ) : phase === 'error' ? (
          <XCircle size={16} />
        ) : (
          <RefreshCw size={16} style={{ animation: busy ? 'spin 1s linear infinite' : 'none' }} />
        )}
        {busy ? 'סורק…' : 'סרוק עכשיו'}
      </button>
      {message && (
        <div style={{ marginTop: 6, fontSize: 12, color: phase === 'error' ? '#dc2626' : '#6b7280' }}>
          {message}
        </div>
      )}
    </div>
  )
}
