import { useState } from 'react'
import { X, ExternalLink, ChevronLeft, ChevronRight } from 'lucide-react'
import type { Listing } from '../types/listing'
import { SOURCE_COLORS, SOURCE_LABELS } from '../types/listing'

interface ListingDetailProps {
  listing: Listing
  onClose: () => void
}

export function ListingDetail({ listing, onClose }: ListingDetailProps) {
  const [imgIndex, setImgIndex] = useState(0)
  const color = SOURCE_COLORS[listing.source]
  const hasImages = listing.images.length > 0

  return (
    <div
      style={{
        width: 340,
        flexShrink: 0,
        display: 'flex',
        flexDirection: 'column',
        background: '#fff',
        borderLeft: '1px solid #e5e7eb',
        borderRight: '1px solid #e5e7eb',
        overflow: 'hidden',
      }}
    >
      {/* Image gallery */}
      {hasImages && (
        <div style={{ position: 'relative', height: 180, background: '#f3f4f6', flexShrink: 0 }}>
          <img
            src={listing.images[imgIndex]}
            alt={listing.title}
            style={{ width: '100%', height: '100%', objectFit: 'cover' }}
            onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }}
          />
          {listing.images.length > 1 && (
            <>
              <button
                onClick={() => setImgIndex((i) => (i - 1 + listing.images.length) % listing.images.length)}
                style={arrowBtn}
              >
                <ChevronRight size={16} />
              </button>
              <button
                onClick={() => setImgIndex((i) => (i + 1) % listing.images.length)}
                style={{ ...arrowBtn, left: 8, right: 'auto' }}
              >
                <ChevronLeft size={16} />
              </button>
              <div style={{ position: 'absolute', bottom: 6, left: '50%', transform: 'translateX(-50%)', fontSize: 11, color: '#fff', background: 'rgba(0,0,0,0.45)', padding: '2px 8px', borderRadius: 10 }}>
                {imgIndex + 1} / {listing.images.length}
              </div>
            </>
          )}
        </div>
      )}

      {/* Header: source badge + close */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 14px', borderBottom: '1px solid #f3f4f6', flexShrink: 0 }}>
        <span style={{ fontSize: 11, fontWeight: 600, color: '#fff', background: color, borderRadius: 10, padding: '2px 10px' }}>
          {SOURCE_LABELS[listing.source]}
        </span>
        <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#9ca3af', display: 'flex', alignItems: 'center' }}>
          <X size={18} />
        </button>
      </div>

      {/* Scrollable content */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '12px 14px' }}>
        {/* Title */}
        <div style={{ fontWeight: 700, fontSize: 15, lineHeight: 1.4, marginBottom: 10 }}>{listing.title}</div>

        {/* Key stats */}
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 12 }}>
          {listing.price != null && (
            <Stat label="מחיר" value={`₪${listing.price.toLocaleString()}`} bold color={color} />
          )}
          {listing.rooms != null && <Stat label="חדרים" value={String(listing.rooms)} />}
          {listing.sqm != null && <Stat label='מ"ר' value={String(listing.sqm)} />}
          {listing.floor != null && <Stat label="קומה" value={String(listing.floor)} />}
        </div>

        {/* Location */}
        {(listing.city || listing.neighborhood || listing.address) && (
          <div style={{ fontSize: 13, color: '#374151', marginBottom: 10, lineHeight: 1.5 }}>
            {[listing.address, listing.neighborhood, listing.city].filter(Boolean).join(' · ')}
          </div>
        )}

        {/* Description */}
        {listing.description && (
          <div style={{ fontSize: 13, color: '#6b7280', lineHeight: 1.6, whiteSpace: 'pre-wrap', marginBottom: 12 }}>
            {listing.description.slice(0, 600)}
            {listing.description.length > 600 && '…'}
          </div>
        )}

        {/* Source link */}
        {listing.original_url && (
          <a
            href={listing.original_url}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 5,
              fontSize: 13,
              fontWeight: 600,
              color: color,
              textDecoration: 'none',
            }}
          >
            לצפייה במקור <ExternalLink size={13} />
          </a>
        )}
      </div>
    </div>
  )
}

function Stat({ label, value, bold, color }: { label: string; value: string; bold?: boolean; color?: string }) {
  return (
    <div style={{ background: '#f9fafb', borderRadius: 8, padding: '6px 10px', minWidth: 56, textAlign: 'center' }}>
      <div style={{ fontSize: 13, fontWeight: bold ? 700 : 600, color: color ?? '#111' }}>{value}</div>
      <div style={{ fontSize: 11, color: '#9ca3af' }}>{label}</div>
    </div>
  )
}

const arrowBtn: React.CSSProperties = {
  position: 'absolute',
  right: 8,
  top: '50%',
  transform: 'translateY(-50%)',
  background: 'rgba(0,0,0,0.45)',
  border: 'none',
  borderRadius: '50%',
  width: 28,
  height: 28,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  cursor: 'pointer',
  color: '#fff',
}
