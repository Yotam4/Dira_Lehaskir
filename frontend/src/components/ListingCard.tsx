import { ExternalLink } from 'lucide-react'
import type { Listing } from '../types/listing'
import { SOURCE_COLORS, SOURCE_LABELS } from '../types/listing'

interface ListingCardProps {
  listing: Listing
  selected?: boolean
  onClick?: () => void
}

export function ListingCard({ listing, selected, onClick }: ListingCardProps) {
  const color = SOURCE_COLORS[listing.source]

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

      <div style={{ marginTop: 6, fontWeight: 600, fontSize: 14 }}>{listing.title}</div>

      <div style={{ marginTop: 4, fontSize: 13, color: '#374151', display: 'flex', gap: 12 }}>
        {listing.price && <span>₪{listing.price.toLocaleString()}</span>}
        {listing.rooms && <span>{listing.rooms} חד׳</span>}
        {listing.sqm && <span>{listing.sqm} מ״ר</span>}
      </div>

      {(listing.neighborhood || listing.city) && (
        <div style={{ marginTop: 2, fontSize: 12, color: '#9ca3af' }}>
          {[listing.neighborhood, listing.city].filter(Boolean).join(', ')}
        </div>
      )}
    </div>
  )
}
