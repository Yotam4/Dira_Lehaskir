import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { MapView } from '../components/MapView'
import { FilterPanel } from '../components/FilterPanel'
import { ListingCard } from '../components/ListingCard'
import { ScrapeButton } from '../components/ScrapeButton'
import { useListings } from '../hooks/useListings'
import type { SearchFilters } from '../types/listing'

export function Home() {
  const [filters, setFilters] = useState<SearchFilters>({ page: 1, page_size: 50 })
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const queryClient = useQueryClient()

  const { data, isFetching } = useListings(filters)

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
