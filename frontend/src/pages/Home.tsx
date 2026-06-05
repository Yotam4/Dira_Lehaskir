import { useState, useEffect, useRef, useMemo } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { MapView } from '../components/MapView'
import { FilterPanel } from '../components/FilterPanel'
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

  // Displayed items — apply client-side favourites filter
  const displayedItems = useMemo(
    () => (favoritesOnly ? accumulatedItems.filter((l) => favorites.has(l.id)) : accumulatedItems),
    [accumulatedItems, favoritesOnly, favorites],
  )

  // Keep a ref to displayedItems so keyboard handler always sees latest value
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

  const handleLoadMore = () => {
    setFilters((prev) => ({ ...prev, page: (prev.page ?? 1) + 1 }))
  }

  const latestScrapedAt = accumulatedItems.length
    ? accumulatedItems.reduce((max, l) => (l.scraped_at > max ? l.scraped_at : max), accumulatedItems[0].scraped_at)
    : null

  const canLoadMore = !isFetching && data != null && accumulatedItems.length < data.total

  const clearAll = () => {
    setFilters({ page: 1, page_size: 20 })
    setAccumulatedItems([])
  }

  // Active-filter chips (each removable)
  const chips: { label: string; clear: () => void }[] = []
  if (filters.city) chips.push({ label: filters.city, clear: () => handleFilterChange({ city: undefined, neighborhood: undefined }) })
  if (filters.neighborhood) chips.push({ label: filters.neighborhood, clear: () => handleFilterChange({ neighborhood: undefined }) })
  if (filters.price_min != null || filters.price_max != null)
    chips.push({ label: `₪${filters.price_min ?? 0}–${filters.price_max ?? '∞'}`, clear: () => handleFilterChange({ price_min: undefined, price_max: undefined }) })
  if (filters.rooms_min != null || filters.rooms_max != null)
    chips.push({ label: `${filters.rooms_min ?? 0}–${filters.rooms_max ?? '∞'} חד׳`, clear: () => handleFilterChange({ rooms_min: undefined, rooms_max: undefined }) })
  if (filters.polygon_geojson) chips.push({ label: 'אזור מצויר', clear: () => handleFilterChange({ polygon_geojson: undefined }) })
  if (filters.lat != null) chips.push({ label: `רדיוס ${filters.radius_m ?? 1000}מ׳`, clear: () => handleFilterChange({ lat: undefined, lng: undefined, radius_m: undefined }) })

  const showSkeleton = isFetching && (filters.page ?? 1) <= 1 && displayedItems.length === 0

  return (
    <div dir="rtl" style={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>
      {/* Sidebar (right in RTL) */}
      <div style={{ width: 300, display: 'flex', flexDirection: 'column', background: '#f9fafb', borderInlineEnd: '1px solid #e5e7eb', overflow: 'hidden' }}>
        {/* Header */}
        <div style={{ padding: '12px 16px', borderBottom: '1px solid #e5e7eb', background: '#fff' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10 }}>
            <div>
              <h1 style={{ fontSize: 18, fontWeight: 700 }}>DiraScan</h1>
              {latestScrapedAt && (
                <div style={{ fontSize: 10, color: '#9ca3af', marginTop: 1 }}>
                  {formatLastScrape(latestScrapedAt)}
                </div>
              )}
            </div>
            <ScrapeButton
              filters={filters}
              onComplete={() => queryClient.invalidateQueries({ queryKey: ['listings'] })}
            />
          </div>
          <FilterPanel
            filters={filters}
            onChange={setFilters}
            favoritesOnly={favoritesOnly}
            onToggleFavoritesOnly={() => setFavoritesOnly((v) => !v)}
          />
        </div>

        {/* Results list */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '8px 12px' }}>
          {/* Sort + result count row */}
          <div style={{ marginBottom: 6 }}>
            <select
              value={`${filters.sort_by ?? 'scraped_at'}:${filters.order ?? 'desc'}`}
              onChange={(e) => handleSortChange(e.target.value)}
              style={{ fontSize: 12, padding: '4px 6px', borderRadius: 6, border: '1px solid #d1d5db', width: '100%', marginBottom: 4 }}
            >
              <option value="scraped_at:desc">חדש ביותר</option>
              <option value="price:asc">מחיר: נמוך לגבוה</option>
              <option value="price:desc">מחיר: גבוה לנמוך</option>
              <option value="rooms:asc">חדרים: מעט לרבה</option>
              <option value="sqm:asc">שטח: קטן לגדול</option>
            </select>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ fontSize: 12, color: isError ? '#ef4444' : '#9ca3af' }}>
                {isError ? 'שגיאה בטעינת הדירות' : `${data?.total ?? 0} תוצאות${isFetching ? ' · מעדכן…' : ''}`}
              </div>
              {chips.length > 0 && (
                <button
                  onClick={clearAll}
                  style={{ fontSize: 11, color: '#1d4ed8', background: 'none', border: 'none', cursor: 'pointer' }}
                >
                  נקה הכל
                </button>
              )}
            </div>
          </div>

          {/* Active-filter chips */}
          {chips.length > 0 && (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginBottom: 8 }}>
              {chips.map((c) => (
                <button
                  key={c.label}
                  onClick={c.clear}
                  style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '2px 8px', borderRadius: 12, border: '1px solid #c7d2fe', background: '#eef2ff', color: '#3730a3', fontSize: 11, cursor: 'pointer' }}
                >
                  {c.label} <span aria-hidden style={{ fontWeight: 700 }}>×</span>
                </button>
              ))}
            </div>
          )}

          {/* Loading skeleton (first page) */}
          {showSkeleton &&
            [0, 1, 2, 3].map((i) => (
              <div
                key={i}
                style={{ height: 78, borderRadius: 8, background: '#eef0f3', marginBottom: 8, animation: 'pulse 1.4s ease-in-out infinite' }}
              />
            ))}

          {!isFetching && displayedItems.length === 0 && (
            <div style={{ padding: '24px 8px', textAlign: 'center', color: '#9ca3af', fontSize: 13 }}>
              <div style={{ marginBottom: 6 }}>לא נמצאו דירות לפי הסינון שנבחר</div>
              <button
                onClick={() => {
                  setFilters({ page: 1, page_size: 20 })
                  setAccumulatedItems([])
                }}
                style={{ fontSize: 12, color: '#1d4ed8', background: 'none', border: 'none', cursor: 'pointer', textDecoration: 'underline' }}
              >
                נקה סינון
              </button>
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

          {/* Load more */}
          {canLoadMore && (
            <button
              onClick={handleLoadMore}
              style={{
                width: '100%',
                padding: '8px',
                marginTop: 4,
                marginBottom: 12,
                borderRadius: 8,
                border: '1px solid #d1d5db',
                background: '#f9fafb',
                color: '#374151',
                cursor: 'pointer',
                fontSize: 13,
                fontWeight: 500,
              }}
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
  )
}
