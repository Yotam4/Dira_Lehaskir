import { Star } from 'lucide-react'
import type { SearchFilters, ListingSource } from '../types/listing'
import { SOURCE_COLORS, SOURCE_LABELS } from '../types/listing'
import { Combobox } from './Combobox'
import { FilterPopover } from './FilterPopover'
import { useCities, useNeighborhoods } from '../hooks/useGeo'

interface FilterBarProps {
  filters: SearchFilters
  onChange: (partial: Partial<SearchFilters>) => void
  favoritesOnly: boolean
  onToggleFavoritesOnly: () => void
}

const SOURCES: ListingSource[] = ['yad2', 'madlan', 'facebook']
const PRICE_PRESETS = [4000, 5000, 6000, 8000, 10000]
const ROOM_RANGES: { label: string; min?: number; max?: number }[] = [
  { label: '1–2', min: 1, max: 2 },
  { label: '2–3', min: 2, max: 3 },
  { label: '3–4', min: 3, max: 4 },
  { label: '4+', min: 4 },
]

const nis = (n: number) => `₪${n.toLocaleString()}`

export function FilterBar({ filters, onChange, favoritesOnly, onToggleFavoritesOnly }: FilterBarProps) {
  const set = (partial: Partial<SearchFilters>) => onChange(partial)

  const { data: cities = [] } = useCities()
  const { data: neighborhoods = [], isFetching: nbhLoading } = useNeighborhoods(filters.city)
  const hasCity = !!filters.city && filters.city.trim().length > 0
  const activeSources = filters.sources ?? []

  const priceSummary =
    filters.price_min != null || filters.price_max != null
      ? `${filters.price_min != null ? nis(filters.price_min) : '₪0'}–${filters.price_max != null ? nis(filters.price_max) : '∞'}`
      : null
  const roomsSummary =
    filters.rooms_min != null || filters.rooms_max != null
      ? `${filters.rooms_min ?? 0}–${filters.rooms_max ?? '∞'} חד׳`
      : null
  const sourcesSummary = activeSources.length ? activeSources.map((s) => SOURCE_LABELS[s]).join(', ') : null

  const toggleSource = (s: ListingSource) => {
    const next = activeSources.includes(s) ? activeSources.filter((x) => x !== s) : [...activeSources, s]
    set({ sources: next.length ? next : undefined })
  }

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
      {/* Location: city → dependent neighborhood */}
      <div style={{ width: 180 }}>
        <Combobox
          aria-label="עיר"
          value={filters.city ?? ''}
          options={cities}
          placeholder="כל הערים"
          emptyText="לא נמצאה עיר"
          onSelect={(val) => set({ city: val || undefined, neighborhood: undefined })}
        />
      </div>
      <div style={{ width: 180 }}>
        <Combobox
          aria-label="שכונה"
          value={filters.neighborhood ?? ''}
          options={neighborhoods}
          disabled={!hasCity}
          placeholder={!hasCity ? 'בחר עיר תחילה' : nbhLoading ? 'טוען…' : 'כל השכונות'}
          emptyText="אין שכונות"
          onSelect={(val) => set({ neighborhood: val || undefined })}
        />
      </div>

      {/* Price */}
      <FilterPopover label="מחיר" summary={priceSummary} onClear={() => set({ price_min: undefined, price_max: undefined })}>
        <RangeFields
          minValue={filters.price_min}
          maxValue={filters.price_max}
          minPlaceholder="מינימום"
          maxPlaceholder="מקסימום"
          onMin={(v) => set({ price_min: v })}
          onMax={(v) => set({ price_max: v })}
        />
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 10 }}>
          {PRICE_PRESETS.map((p) => (
            <button key={p} type="button" onClick={() => set({ price_max: p })} style={chipStyle(filters.price_max === p)}>
              עד {nis(p)}
            </button>
          ))}
        </div>
      </FilterPopover>

      {/* Rooms */}
      <FilterPopover label="חדרים" summary={roomsSummary} onClear={() => set({ rooms_min: undefined, rooms_max: undefined })}>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 10 }}>
          {ROOM_RANGES.map((r) => {
            const on = filters.rooms_min === r.min && filters.rooms_max === r.max
            return (
              <button key={r.label} type="button" onClick={() => set({ rooms_min: r.min, rooms_max: r.max })} style={chipStyle(on)}>
                {r.label}
              </button>
            )
          })}
        </div>
        <RangeFields
          minValue={filters.rooms_min}
          maxValue={filters.rooms_max}
          step="0.5"
          minPlaceholder="מינ׳"
          maxPlaceholder="מקס׳"
          onMin={(v) => set({ rooms_min: v })}
          onMax={(v) => set({ rooms_max: v })}
        />
      </FilterPopover>

      {/* Sources */}
      <FilterPopover label="מקור" summary={sourcesSummary} onClear={() => set({ sources: undefined })}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {SOURCES.map((s) => (
            <label key={s} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, cursor: 'pointer' }}>
              <input type="checkbox" checked={activeSources.includes(s)} onChange={() => toggleSource(s)} />
              <span style={{ width: 10, height: 10, borderRadius: 3, background: SOURCE_COLORS[s], display: 'inline-block' }} />
              {SOURCE_LABELS[s]}
            </label>
          ))}
        </div>
      </FilterPopover>

      {/* Favourites */}
      <button
        type="button"
        onClick={onToggleFavoritesOnly}
        title="מועדפים בלבד"
        style={{
          display: 'inline-flex', alignItems: 'center', gap: 6, padding: '7px 12px', borderRadius: 999,
          border: `1px solid ${favoritesOnly ? '#f59e0b' : '#d1d5db'}`,
          background: favoritesOnly ? '#fef3c7' : '#fff',
          color: favoritesOnly ? '#92400e' : '#374151', cursor: 'pointer', fontSize: 13, fontWeight: 500,
        }}
      >
        <Star size={13} fill={favoritesOnly ? '#f59e0b' : 'none'} color={favoritesOnly ? '#f59e0b' : '#9ca3af'} />
        מועדפים
      </button>
    </div>
  )
}

function RangeFields({
  minValue, maxValue, onMin, onMax, minPlaceholder, maxPlaceholder, step,
}: {
  minValue?: number | null
  maxValue?: number | null
  onMin: (v: number | undefined) => void
  onMax: (v: number | undefined) => void
  minPlaceholder: string
  maxPlaceholder: string
  step?: string
}) {
  const invalid = minValue != null && maxValue != null && minValue > maxValue
  return (
    <>
      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
        <input
          type="number" step={step} placeholder={minPlaceholder} style={inputStyle}
          value={minValue ?? ''} onChange={(e) => onMin(e.target.value ? Number(e.target.value) : undefined)}
        />
        <span style={{ color: '#9ca3af' }}>–</span>
        <input
          type="number" step={step} placeholder={maxPlaceholder} style={inputStyle}
          value={maxValue ?? ''} onChange={(e) => onMax(e.target.value ? Number(e.target.value) : undefined)}
        />
      </div>
      {invalid && <div style={{ fontSize: 11, color: '#ef4444', marginTop: 4 }}>מינ׳ גדול ממקס׳</div>}
    </>
  )
}

function chipStyle(active: boolean): React.CSSProperties {
  return {
    padding: '5px 10px', borderRadius: 999,
    border: `1px solid ${active ? '#1d4ed8' : '#d1d5db'}`,
    background: active ? '#1d4ed8' : '#f9fafb',
    color: active ? '#fff' : '#374151', cursor: 'pointer', fontSize: 12, fontWeight: 500,
  }
}

const inputStyle: React.CSSProperties = {
  width: '100%', padding: '6px 8px', borderRadius: 6, border: '1px solid #d1d5db', fontSize: 13,
}
