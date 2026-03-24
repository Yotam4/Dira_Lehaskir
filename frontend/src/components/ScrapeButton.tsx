import { useState } from 'react'
import { RefreshCw } from 'lucide-react'
import { triggerScrape } from '../api/client'
import type { SearchFilters } from '../types/listing'

interface ScrapeButtonProps {
  filters: SearchFilters
  onComplete?: () => void
}

export function ScrapeButton({ filters, onComplete }: ScrapeButtonProps) {
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState<string | null>(null)

  const handleClick = async () => {
    setLoading(true)
    setMessage(null)
    try {
      const result = await triggerScrape({
        sources: ['yad2', 'madlan', 'facebook'],
        filters: {
          city: filters.city,
          neighborhood: filters.neighborhood,
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
      setMessage(`סריקה החלה (${result.run_id.slice(0, 8)}...)`)
      onComplete?.()
    } catch (e) {
      setMessage('שגיאה בהפעלת הסריקה')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <button
        onClick={handleClick}
        disabled={loading}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          padding: '8px 16px',
          borderRadius: 8,
          border: 'none',
          background: loading ? '#9ca3af' : '#1d4ed8',
          color: '#fff',
          fontWeight: 600,
          cursor: loading ? 'not-allowed' : 'pointer',
          fontSize: 14,
        }}
      >
        <RefreshCw size={16} style={{ animation: loading ? 'spin 1s linear infinite' : 'none' }} />
        {loading ? 'סורק...' : 'סרוק עכשיו'}
      </button>
      {message && (
        <div style={{ marginTop: 6, fontSize: 12, color: '#6b7280' }}>{message}</div>
      )}
    </div>
  )
}
