import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { MapView } from '../components/MapView'
import { FilterPanel } from '../components/FilterPanel'
import { ListingCard } from '../components/ListingCard'
import { ListingDetail } from '../components/ListingDetail'
import { ScrapeButton } from '../components/ScrapeButton'
import { useListings } from '../hooks/useListings'
import type { SearchFilters } from '../types/listing'

export function Home() {
  const [filters, setFilters] = useState<SearchFilters>({ page: 1, page_size: 50 })
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const queryClient = useQueryClient()

  const { data, isFetching } = useListings(filters)
  const selectedListing = data?.items.find((l) => l.id === selectedId) ?? null

  const handleFilterChange = (partial: Partial<SearchFilters>) => {
    setFilters((prev) => ({ ...prev, ...partial }))
  }

  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>
      {/* Left sidebar */}
      <div style={{ width: 300, display: 'flex', flexDirection: 'column', background: '#f9fafb', borderLeft: '1px solid #e5e7eb', overflow: 'hidden' }}>
        {/* Header */}
        <div style={{ padding: '12px 16px', borderBottom: '1px solid #e5e7eb', background: '#fff' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
            <h1 style={{ fontSize: 18, fontWeight: 700 }}>DiraScan</h1>
            <ScrapeButton
              filters={filters}
              onComplete={() => queryClient.invalidateQueries({ queryKey: ['listings'] })}
            />
          </div>
          <FilterPanel filters={filters} onChange={setFilters} />
        </div>

        {/* Results list */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '8px 12px' }}>
          <div style={{ fontSize: 12, color: '#9ca3af', marginBottom: 8 }}>
            {isFetching ? 'טוען...' : `${data?.total ?? 0} תוצאות`}
          </div>
          {!isFetching && data?.items.length === 0 && (
            <div style={{ padding: '24px 8px', textAlign: 'center', color: '#9ca3af', fontSize: 13 }}>
              <div style={{ marginBottom: 6 }}>לא נמצאו דירות לפי הסינון שנבחר</div>
              <button
                onClick={() => setFilters({ page: 1, page_size: 50 })}
                style={{ fontSize: 12, color: '#1d4ed8', background: 'none', border: 'none', cursor: 'pointer', textDecoration: 'underline' }}
              >
                נקה סינון
              </button>
            </div>
          )}
          {data?.items.map((listing) => (
            <ListingCard
              key={listing.id}
              listing={listing}
              selected={listing.id === selectedId}
              onClick={() => setSelectedId(listing.id === selectedId ? null : listing.id)}
            />
          ))}
        </div>
      </div>

      {/* Detail panel — shown when a listing is selected */}
      {selectedListing && (
        <ListingDetail listing={selectedListing} onClose={() => setSelectedId(null)} />
      )}

      {/* Map */}
      <MapView
        listings={data?.items ?? []}
        filters={filters}
        selectedId={selectedId}
        onSelectListing={setSelectedId}
        onFilterChange={handleFilterChange}
      />
    </div>
  )
}
