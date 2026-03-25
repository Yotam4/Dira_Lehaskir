import { ExternalLink, Star } from 'lucide-react'
import type { Listing } from '../types/listing'
import { SOURCE_COLORS, SOURCE_LABELS } from '../types/listing'
import { formatAge } from '../utils/formatAge'

interface ListingCardProps {
  listing: Listing
  selected?: boolean
  onClick?: () => void
  isFavorite?: boolean
  onToggleFavorite?: () => void
}

export function ListingCard({ listing, selected, onClick, isFavorite, onToggleFavorite }: ListingCardProps) {
  const color = SOURCE_COLORS[listing.source]
  const pricePerSqm = listing.price && listing.sqm ? Math.round(listing.price / listing.sqm) : null

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onClick}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onClick?.() } }}
      style={{
        padding: '10px 12px',
        borderRadius: 8,
        border: `1px solid ${selected ? color : '#e5e7eb'}`,
        background: selected ? `${color}10` : '#fff',
        cursor: 'pointer',
        marginBottom: 8,
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <span
          style={{
            fontSize: 11,
            fontWeight: 600,
            color: '#fff',
            background: color,
            borderRadius: 10,
            padding: '2px 8px',
          }}
        >
          {SOURCE_LABELS[listing.source]}
        </span>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          {onToggleFavorite && (
            <button
              onClick={(e) => { e.stopPropagation(); onToggleFavorite() }}
              style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0, color: isFavorite ? '#f59e0b' : '#d1d5db', display: 'flex' }}
              title={isFavorite ? 'הסר ממועדפים' : 'הוסף למועדפים'}
            >
              <Star size={14} fill={isFavorite ? '#f59e0b' : 'none'} />
            </button>
          )}
          {listing.original_url && (
            <a
              href={listing.original_url}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
              style={{ color: '#6b7280', display: 'flex', alignItems: 'center', gap: 3, fontSize: 12 }}
            >
              מקור <ExternalLink size={12} />
            </a>
          )}
        </div>
      </div>

      <div style={{ marginTop: 6, fontWeight: 600, fontSize: 14 }}>{listing.title}</div>

      <div style={{ marginTop: 4, fontSize: 13, color: '#374151', display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'baseline' }}>
        {listing.price != null && <span>₪{listing.price.toLocaleString()}</span>}
        {pricePerSqm != null && <span style={{ fontSize: 11, color: '#9ca3af' }}>₪{pricePerSqm}/מ"ר</span>}
        {listing.rooms != null && <span>{listing.rooms} חד׳</span>}
        {listing.sqm != null && <span>{listing.sqm} מ״ר</span>}
      </div>

      {(listing.neighborhood || listing.city) && (
        <div style={{ marginTop: 2, fontSize: 12, color: '#9ca3af' }}>
          {[listing.neighborhood, listing.city].filter(Boolean).join(', ')}
        </div>
      )}

      <div style={{ marginTop: 2, fontSize: 11, color: '#d1d5db' }}>{formatAge(listing.scraped_at)}</div>
    </div>
  )
}
