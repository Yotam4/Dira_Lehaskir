import { Star } from 'lucide-react'
import type { SearchFilters, ListingSource } from '../types/listing'
import { SOURCE_COLORS, SOURCE_LABELS } from '../types/listing'
import { Combobox } from './Combobox'
import { useCities, useNeighborhoods } from '../hooks/useGeo'

interface FilterPanelProps {
  filters: SearchFilters
  onChange: (filters: SearchFilters) => void
  favoritesOnly: boolean
  onToggleFavoritesOnly: () => void
}

const SOURCES: ListingSource[] = ['yad2', 'madlan', 'facebook']

const PRESETS: { label: string; partial: Partial<SearchFilters> }[] = [
  { label: '2-3 חד׳', partial: { rooms_min: 2, rooms_max: 3 } },
  { label: 'עד ₪6,000', partial: { price_max: 6000 } },
  { label: 'עד ₪8,000', partial: { price_max: 8000 } },
]

export function FilterPanel({ filters, onChange, favoritesOnly, onToggleFavoritesOnly }: FilterPanelProps) {
  const set = (partial: Partial<SearchFilters>) => onChange({ ...filters, ...partial, page: 1 })

  const { data: cities = [] } = useCities()
  const { data: neighborhoods = [], isFetching: nbhLoading } = useNeighborhoods(filters.city)

  const priceInvalid =
    filters.price_min != null &&
    filters.price_max != null &&
    filters.price_min > filters.price_max

  const activeSources = filters.sources ?? []
  const toggleSource = (s: ListingSource) => {
    const next = activeSources.includes(s)
      ? activeSources.filter((x) => x !== s)
      : [...activeSources, s]
    set({ sources: next.length ? next : undefined })
  }

  const hasCity = !!filters.city && filters.city.trim().length > 0

  return (
    <div style={{ padding: '12px', background: '#fff', borderRadius: 8, minWidth: 240 }}>
      <h3 style={{ marginBottom: 8, fontSize: 14, fontWeight: 600 }}>סינון</h3>

      {/* Quick-filter presets */}
      <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginBottom: 10 }}>
        {PRESETS.map((p) => (
          <button
            key={p.label}
            onClick={() => set(p.partial)}
            style={{
              padding: '3px 8px',
              borderRadius: 10,
              border: '1px solid #d1d5db',
              background: '#f9fafb',
              color: '#374151',
              cursor: 'pointer',
              fontSize: 11,
              fontWeight: 500,
            }}
          >
            {p.label}
          </button>
        ))}
      </div>

      <label style={labelStyle}>עיר</label>
      <Combobox
        aria-label="עיר"
        value={filters.city ?? ''}
        options={cities}
        placeholder="בחר עיר..."
        emptyText="לא נמצאה עיר"
        onSelect={(val) => set({ city: val || undefined, neighborhood: undefined })}
      />

      <label style={labelStyle}>שכונה</label>
      <Combobox
        aria-label="שכונה"
        value={filters.neighborhood ?? ''}
        options={neighborhoods}
        disabled={!hasCity}
        placeholder={
          !hasCity ? 'בחר עיר תחילה' : nbhLoading ? 'טוען שכונות...' : 'בחר שכונה...'
        }
        emptyText="אין שכונות ידועות לעיר זו"
        onSelect={(val) => set({ neighborhood: val || undefined })}
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
            onClick={() => toggleSource(s)}
            style={{
              padding: '4px 10px',
              borderRadius: 12,
              border: `1px solid ${activeSources.includes(s) ? SOURCE_COLORS[s] : '#ccc'}`,
              background: activeSources.includes(s) ? SOURCE_COLORS[s] : '#f3f4f6',
              color: activeSources.includes(s) ? '#fff' : '#374151',
              cursor: 'pointer',
              fontSize: 12,
            }}
          >
            {SOURCE_LABELS[s]}
          </button>
        ))}
      </div>

      {/* Favourites toggle */}
      <button
        onClick={onToggleFavoritesOnly}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          padding: '5px 10px',
          borderRadius: 8,
          border: `1px solid ${favoritesOnly ? '#f59e0b' : '#d1d5db'}`,
          background: favoritesOnly ? '#fef3c7' : '#f9fafb',
          color: favoritesOnly ? '#92400e' : '#374151',
          cursor: 'pointer',
          fontSize: 12,
          marginBottom: 8,
          width: '100%',
        }}
      >
        <Star size={12} fill={favoritesOnly ? '#f59e0b' : 'none'} color={favoritesOnly ? '#f59e0b' : '#9ca3af'} />
        מועדפים בלבד
      </button>

      {(filters.lat || filters.polygon_geojson) && (
        <div style={{ fontSize: 12, color: '#6b7280', marginTop: 4 }}>
          {filters.polygon_geojson
            ? 'חיפוש לפי אזור מצויר'
            : `רדיוס ${filters.radius_m ?? 1000}מ׳ מהנקודה שנבחרה`}
          <button
            style={{ marginInlineStart: 8, fontSize: 11, color: '#ef4444', border: 'none', background: 'none', cursor: 'pointer' }}
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
