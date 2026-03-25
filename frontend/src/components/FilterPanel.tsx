import { useEffect, useRef, useState } from 'react'
import type { SearchFilters, ListingSource } from '../types/listing'
import { SOURCE_LABELS } from '../types/listing'

interface FilterPanelProps {
  filters: SearchFilters
  onChange: (filters: SearchFilters) => void
}

const SOURCES: ListingSource[] = ['yad2', 'madlan', 'facebook']

export function FilterPanel({ filters, onChange }: FilterPanelProps) {
  const set = (partial: Partial<SearchFilters>) => onChange({ ...filters, ...partial, page: 1 })

  // Local draft state for text inputs — debounce before firing onChange
  const [cityDraft, setCityDraft] = useState(filters.city ?? '')
  const [neighborhoodDraft, setNeighborhoodDraft] = useState(filters.neighborhood ?? '')
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Sync drafts when filters are reset externally (e.g. "clear filters" button)
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current)
    setCityDraft(filters.city ?? '')
  }, [filters.city])
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current)
    setNeighborhoodDraft(filters.neighborhood ?? '')
  }, [filters.neighborhood])

  // Clear pending debounce on unmount
  useEffect(() => () => { if (debounceRef.current) clearTimeout(debounceRef.current) }, [])

  const debouncedSet = (partial: Partial<SearchFilters>) => {
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => set(partial), 350)
  }

  const priceInvalid =
    filters.price_min != null &&
    filters.price_max != null &&
    filters.price_min > filters.price_max

  return (
    <div style={{ padding: '12px', background: '#fff', borderRadius: 8, minWidth: 240 }}>
      <h3 style={{ marginBottom: 12, fontSize: 14, fontWeight: 600 }}>סינון</h3>

      <label style={labelStyle}>עיר</label>
      <input
        style={inputStyle}
        placeholder="תל אביב, חיפה..."
        value={cityDraft}
        onChange={(e) => {
          const val = e.target.value
          setCityDraft(val)
          debouncedSet({ city: val || undefined })
        }}
      />

      <label style={labelStyle}>שכונה</label>
      <input
        style={inputStyle}
        placeholder="שם שכונה"
        value={neighborhoodDraft}
        onChange={(e) => {
          const val = e.target.value
          setNeighborhoodDraft(val)
          debouncedSet({ neighborhood: val || undefined })
        }}
      />

      <label style={labelStyle}>מחיר (₪)</label>
      <div style={{ display: 'flex', gap: 6, marginBottom: priceInvalid ? 2 : 8 }}>
        <input
          style={{ ...inputStyle, marginBottom: 0 }}
          type="number"
          placeholder="מינימום"
          value={filters.price_min ?? ''}
          onChange={(e) => set({ price_min: e.target.value ? Number(e.target.value) : undefined })}
        />
        <input
          style={{ ...inputStyle, marginBottom: 0 }}
          type="number"
          placeholder="מקסימום"
          value={filters.price_max ?? ''}
          onChange={(e) => set({ price_max: e.target.value ? Number(e.target.value) : undefined })}
        />
      </div>
      {priceInvalid && (
        <div style={{ fontSize: 11, color: '#ef4444', marginBottom: 6 }}>מינ׳ גדול ממקס׳</div>
      )}

      <label style={labelStyle}>חדרים</label>
      <div style={{ display: 'flex', gap: 6, marginBottom: 8 }}>
        <input
          style={{ ...inputStyle, marginBottom: 0 }}
          type="number"
          step="0.5"
          placeholder="מינ׳"
          value={filters.rooms_min ?? ''}
          onChange={(e) => set({ rooms_min: e.target.value ? Number(e.target.value) : undefined })}
        />
        <input
          style={{ ...inputStyle, marginBottom: 0 }}
          type="number"
          step="0.5"
          placeholder="מקס׳"
          value={filters.rooms_max ?? ''}
          onChange={(e) => set({ rooms_max: e.target.value ? Number(e.target.value) : undefined })}
        />
      </div>

      <label style={labelStyle}>מקור</label>
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 8 }}>
        {SOURCES.map((s) => (
          <button
            key={s}
            onClick={() => set({ source: filters.source === s ? undefined : s })}
            style={{
              padding: '4px 10px',
              borderRadius: 12,
              border: '1px solid #ccc',
              background: filters.source === s ? '#3b82f6' : '#f3f4f6',
              color: filters.source === s ? '#fff' : '#374151',
              cursor: 'pointer',
              fontSize: 12,
            }}
          >
            {SOURCE_LABELS[s]}
          </button>
        ))}
      </div>

      {(filters.lat || filters.polygon_geojson) && (
        <div style={{ fontSize: 12, color: '#6b7280', marginTop: 4 }}>
          {filters.polygon_geojson
            ? '🔷 חיפוש לפי פוליגון מצויר'
            : `📍 רדיוס ${filters.radius_m ?? 1000}מ׳ מהנקודה שנבחרה`}
          <button
            style={{ marginRight: 8, fontSize: 11, color: '#ef4444', border: 'none', background: 'none', cursor: 'pointer' }}
            onClick={() => set({ lat: undefined, lng: undefined, radius_m: undefined, polygon_geojson: undefined })}
          >
            נקה
          </button>
        </div>
      )}
    </div>
  )
}

const labelStyle: React.CSSProperties = { display: 'block', fontSize: 12, fontWeight: 500, marginBottom: 4, color: '#374151' }
const inputStyle: React.CSSProperties = { width: '100%', padding: '6px 8px', borderRadius: 6, border: '1px solid #d1d5db', fontSize: 13, marginBottom: 8 }
