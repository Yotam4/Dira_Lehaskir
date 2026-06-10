import { useState, useEffect, useRef, useMemo } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { MapView } from '../components/MapView'
import { FilterBar } from '../components/FilterBar'
import { ListingCard } from '../components/ListingCard'
import { ListingDetail } from '../components/ListingDetail'
import { ScrapeButton } from '../components/ScrapeButton'
import { useListings } from '../hooks/useListings'
import { useFavorites } from '../hooks/useFavorites'
import { formatLastScrape } from '../utils/formatAge'
import type { Listing, SearchFilters, ListingSource } from '../types/listing'

function readFiltersFromUrl(): SearchFilters {
  const params = new URLSearchParams(window.location.search)
  const filters: SearchFilters = { page: 1, page_size: 20 }
  const city = params.get('city'); if (city) filters.city = city
  const neighborhood = params.get('neighborhood'); if (neighborhood) filters.neighborhood = neighborhood
  const priceMin = params.get('price_min'); if (priceMin) filters.price_min = Number(priceMin)
  const priceMax = params.get('price_max'); if (priceMax) filters.price_max = Number(priceMax)
  const roomsMin = params.get('rooms_min'); if (roomsMin) filters.rooms_min = Number(roomsMin)
  const roomsMax = params.get('rooms_max'); if (roomsMax) filters.rooms_max = Number(roomsMax)
  const sourcesArr = params.getAll('sources') as ListingSource[]
  if (sourcesArr.length) filters.sources = sourcesArr
  const sortBy = params.get('sort_by') as SearchFilters['sort_by']
  if (sortBy) filters.sort_by = sortBy
  const order = params.get('order') as SearchFilters['order']
  if (order) filters.order = order
  const lat = params.get('lat'); if (lat) filters.lat = Number(lat)
  const lng = params.get('lng'); if (lng) filters.lng = Number(lng)
  const radiusM = params.get('radius_m'); if (radiusM) filters.radius_m = Number(radiusM)
  const poly = params.get('polygon_geojson'); if (poly) filters.polygon_geojson = poly
  return filters
}

export function Home() {
  const [filters, setFilters] = useState<SearchFilters>(readFiltersFromUrl)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [favoritesOnly, setFavoritesOnly] = useState(false)
  const [accumulatedItems, setAccumulatedItems] = useState<Listing[]>([])
  const queryClient = useQueryClient()
  const { favorites, toggle: toggleFavorite } = useFavorites()
  const { data, isFetching, isError } = useListings(filters)

  // Accumulate items for load-more — replace on page 1, append on subsequent pages
  useEffect(() => {
    if (!data) return
    if ((filters.page ?? 1) <= 1) {
      setAccumulatedItems(data.items)
    } else {
      setAccumulatedItems((prev) => [...prev, ...data.items])
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data])

  // Sync filters → URL on every change (spatial params included so they survive reload)
  useEffect(() => {
    const params = new URLSearchParams()
    if (filters.city) params.set('city', filters.city)
    if (filters.neighborhood) params.set('neighborhood', filters.neighborhood)
    if (filters.price_min != null) params.set('price_min', String(filters.price_min))
    if (filters.price_max != null) params.set('price_max', String(filters.price_max))
    if (filters.rooms_min != null) params.set('rooms_min', String(filters.rooms_min))
    if (filters.rooms_max != null) params.set('rooms_max', String(filters.rooms_max))
    filters.sources?.forEach((s) => params.append('sources', s))
    if (filters.sort_by) params.set('sort_by', filters.sort_by)
    if (filters.order) params.set('order', filters.order)
    if (filters.lat != null) params.set('lat', String(filters.lat))
    if (filters.lng != null) params.set('lng', String(filters.lng))
    if (filters.radius_m != null) params.set('radius_m', String(filters.radius_m))
    if (filters.polygon_geojson) params.set('polygon_geojson', filters.polygon_geojson)
    window.history.replaceState(null, '', params.toString() ? `?${params}` : window.location.pathname)
  }, [filters])

  const displayedItems = useMemo(
    () => (favoritesOnly ? accumulatedItems.filter((l) => favorites.has(l.id)) : accumulatedItems),
    [accumulatedItems, favoritesOnly, favorites],
  )

  const displayedItemsRef = useRef<Listing[]>([])
  displayedItemsRef.current = displayedItems

  // Keyboard navigation: j/↓ next, k/↑ prev, Escape close
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement).tagName
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return
      const items = displayedItemsRef.current
      if (e.key === 'j' || e.key === 'ArrowDown') {
        e.preventDefault()
        setSelectedId((id) => {
          if (!items.length) return id
          if (!id) return items[0].id
          const idx = items.findIndex((l) => l.id === id)
          return items[Math.min(idx + 1, items.length - 1)].id
        })
      } else if (e.key === 'k' || e.key === 'ArrowUp') {
        e.preventDefault()
        setSelectedId((id) => {
          if (!items.length) return id
          if (!id) return items[items.length - 1].id
          const idx = items.findIndex((l) => l.id === id)
          return items[Math.max(idx - 1, 0)].id
        })
      } else if (e.key === 'Escape') {
        setSelectedId(null)
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  const selectedListing = displayedItems.find((l) => l.id === selectedId) ?? null

  const handleFilterChange = (partial: Partial<SearchFilters>) => {
    setFilters((prev) => ({ ...prev, ...partial, page: 1 }))
    setAccumulatedItems([])
  }

  const handleSortChange = (value: string) => {
    const [sort_by, order] = value.split(':') as [SearchFilters['sort_by'], SearchFilters['order']]
    handleFilterChange({ sort_by, order })
  }

  const handleLoadMore = () => setFilters((prev) => ({ ...prev, page: (prev.page ?? 1) + 1 }))

  const latestScrapedAt = accumulatedItems.length
    ? accumulatedItems.reduce((max, l) => (l.scraped_at > max ? l.scraped_at : max), accumulatedItems[0].scraped_at)
    : null

  const canLoadMore = !isFetching && data != null && accumulatedItems.length < data.total

  const clearAll = () => {
    setFilters({ page: 1, page_size: 20 })
    setAccumulatedItems([])
  }

  const hasActiveFilters =
    !!(filters.city || filters.neighborhood || filters.price_min != null || filters.price_max != null ||
       filters.rooms_min != null || filters.rooms_max != null || filters.sources?.length ||
       filters.lat != null || filters.polygon_geojson || favoritesOnly)

  const showSkeleton = isFetching && (filters.page ?? 1) <= 1 && displayedItems.length === 0

  return (
    <div dir="rtl" style={{ display: 'flex', flexDirection: 'column', height: '100vh', overflow: 'hidden' }}>
      {/* ── Top filter bar ───────────────────────────────────────────── */}
      <header style={{ position: 'relative', zIndex: 30, background: '#fff', borderBottom: '1px solid #e5e7eb', padding: '10px 16px', display: 'flex', alignItems: 'center', gap: 16, flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
          <h1 style={{ fontSize: 20, fontWeight: 800, color: '#1d4ed8' }}>DiraScan</h1>
          {latestScrapedAt && (
            <span style={{ fontSize: 10, color: '#9ca3af' }}>{formatLastScrape(latestScrapedAt)}</span>
          )}
        </div>

        <div style={{ flex: 1, minWidth: 280 }}>
          <FilterBar
            filters={filters}
            onChange={handleFilterChange}
            favoritesOnly={favoritesOnly}
            onToggleFavoritesOnly={() => setFavoritesOnly((v) => !v)}
          />
        </div>

        {hasActiveFilters && (
          <button onClick={clearAll} style={{ fontSize: 12, color: '#dc2626', background: 'none', border: 'none', cursor: 'pointer' }}>
            נקה הכל
          </button>
        )}
        <ScrapeButton filters={filters} onComplete={() => queryClient.invalidateQueries({ queryKey: ['listings'] })} />
      </header>

      {/* ── Body: results list + map ─────────────────────────────────── */}
      <div style={{ position: 'relative', zIndex: 0, flex: 1, display: 'flex', overflow: 'hidden' }}>
        {/* Results panel */}
        <div style={{ width: 380, display: 'flex', flexDirection: 'column', background: '#f9fafb', borderInlineEnd: '1px solid #e5e7eb', overflow: 'hidden' }}>
          {/* Result count + sort */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8, padding: '8px 12px', borderBottom: '1px solid #e5e7eb', background: '#fff' }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: isError ? '#ef4444' : '#374151' }}>
              {isError ? 'שגיאה בטעינה' : `${data?.total ?? 0} דירות${isFetching ? ' · מעדכן…' : ''}`}
            </div>
            <select
              value={`${filters.sort_by ?? 'scraped_at'}:${filters.order ?? 'desc'}`}
              onChange={(e) => handleSortChange(e.target.value)}
              style={{ fontSize: 12, padding: '5px 6px', borderRadius: 6, border: '1px solid #d1d5db' }}
            >
              <option value="scraped_at:desc">חדש ביותר</option>
              <option value="price:asc">מחיר: נמוך לגבוה</option>
              <option value="price:desc">מחיר: גבוה לנמוך</option>
              <option value="rooms:asc">חדרים: מעט לרבה</option>
              <option value="sqm:asc">שטח: קטן לגדול</option>
            </select>
          </div>

          {/* List */}
          <div style={{ flex: 1, overflowY: 'auto', padding: '8px 12px' }}>
            {showSkeleton &&
              [0, 1, 2, 3].map((i) => (
                <div key={i} style={{ height: 78, borderRadius: 8, background: '#eef0f3', marginBottom: 8, animation: 'pulse 1.4s ease-in-out infinite' }} />
              ))}

            {!isFetching && displayedItems.length === 0 && (
              <div style={{ padding: '24px 8px', textAlign: 'center', color: '#9ca3af', fontSize: 13 }}>
                <div style={{ marginBottom: 6 }}>לא נמצאו דירות לפי הסינון שנבחר</div>
                {hasActiveFilters && (
                  <button onClick={clearAll} style={{ fontSize: 12, color: '#1d4ed8', background: 'none', border: 'none', cursor: 'pointer', textDecoration: 'underline' }}>
                    נקה סינון
                  </button>
                )}
              </div>
            )}

            {displayedItems.map((listing) => (
              <ListingCard
                key={listing.id}
                listing={listing}
                selected={listing.id === selectedId}
                onClick={() => setSelectedId(listing.id === selectedId ? null : listing.id)}
                isFavorite={favorites.has(listing.id)}
                onToggleFavorite={() => toggleFavorite(listing.id)}
              />
            ))}

            {canLoadMore && (
              <button
                onClick={handleLoadMore}
                style={{ width: '100%', padding: 8, marginTop: 4, marginBottom: 12, borderRadius: 8, border: '1px solid #d1d5db', background: '#f9fafb', color: '#374151', cursor: 'pointer', fontSize: 13, fontWeight: 500 }}
              >
                עוד תוצאות ({accumulatedItems.length} / {data?.total})
              </button>
            )}

            {isFetching && (filters.page ?? 1) > 1 && (
              <div style={{ textAlign: 'center', padding: 8, fontSize: 12, color: '#9ca3af' }}>טוען...</div>
            )}
          </div>
        </div>

        {/* Detail panel — shown when a listing is selected */}
        {selectedListing && (
          <ListingDetail
            listing={selectedListing}
            onClose={() => setSelectedId(null)}
            isFavorite={favorites.has(selectedListing.id)}
            onToggleFavorite={() => toggleFavorite(selectedListing.id)}
          />
        )}

        {/* Map */}
        <MapView
          listings={accumulatedItems}
          filters={filters}
          selectedId={selectedId}
          onSelectListing={setSelectedId}
          onFilterChange={handleFilterChange}
        />
      </div>
    </div>
  )
}
