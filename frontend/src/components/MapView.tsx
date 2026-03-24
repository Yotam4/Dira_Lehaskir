import { useCallback, useRef, useState, type MutableRefObject } from 'react'
import Map, { Marker, NavigationControl, useControl } from 'react-map-gl'
import type { MapRef } from 'react-map-gl'
import MapboxDraw from '@mapbox/mapbox-gl-draw'
import type { Listing, SearchFilters } from '../types/listing'
import { SOURCE_COLORS } from '../types/listing'

const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_TOKEN as string

// Default center: Tel Aviv
const DEFAULT_VIEW = { longitude: 34.7818, latitude: 32.0853, zoom: 12 }

// Draws the MapboxDraw control and reports drawn features upward.
// The draw instance is captured via a ref so event handlers can call getAll().
function DrawControl({ onDraw }: { onDraw: (geojson: string | null) => void }) {
  const drawRef: MutableRefObject<MapboxDraw | null> = useRef(null)

  useControl<MapboxDraw>(
    () => {
      const draw = new MapboxDraw({
        displayControlsDefault: false,
        controls: { polygon: true, trash: true },
      })
      drawRef.current = draw
      return draw
    },
    ({ map }) => {
      const onUpdate = () => {
        const data = drawRef.current?.getAll()
        if (data && data.features.length > 0) {
          onDraw(JSON.stringify(data.features[0].geometry))
        } else {
          onDraw(null)
        }
      }
      map.on('draw.create', onUpdate)
      map.on('draw.update', onUpdate)
      map.on('draw.delete', () => onDraw(null))
    },
    () => {},
    { position: 'top-left' }
  )
  return null
}

interface MapViewProps {
  listings: Listing[]
  filters: SearchFilters
  selectedId: string | null
  onSelectListing: (id: string) => void
  onFilterChange: (partial: Partial<SearchFilters>) => void
}

export function MapView({
  listings,
  filters,
  selectedId,
  onSelectListing,
  onFilterChange,
}: MapViewProps) {
  const mapRef = useRef<MapRef>(null)
  const [radiusMode, setRadiusMode] = useState(false)

  const handleMapClick = useCallback(
    (e: mapboxgl.MapMouseEvent) => {
      if (radiusMode) {
        onFilterChange({
          lat: e.lngLat.lat,
          lng: e.lngLat.lng,
          radius_m: 1000,
          polygon_geojson: undefined,
        })
        setRadiusMode(false)
      }
    },
    [radiusMode, onFilterChange]
  )

  return (
    <div style={{ position: 'relative', flex: 1, height: '100%' }}>
      {/* Toolbar overlay */}
      <div style={{ position: 'absolute', top: 10, right: 10, zIndex: 10, display: 'flex', gap: 6 }}>
        <button
          onClick={() => setRadiusMode((v) => !v)}
          style={{
            padding: '6px 12px',
            borderRadius: 6,
            border: '1px solid #d1d5db',
            background: radiusMode ? '#1d4ed8' : '#fff',
            color: radiusMode ? '#fff' : '#374151',
            cursor: 'pointer',
            fontSize: 12,
            fontWeight: 500,
          }}
        >
          📍 חיפוש רדיוס
        </button>
        {filters.radius_m && (
          <select
            value={filters.radius_m}
            onChange={(e) => onFilterChange({ radius_m: Number(e.target.value) })}
            style={{ padding: '6px', borderRadius: 6, border: '1px solid #d1d5db', fontSize: 12 }}
          >
            <option value={500}>500 מ׳</option>
            <option value={1000}>1 ק״מ</option>
            <option value={2000}>2 ק״מ</option>
            <option value={5000}>5 ק״מ</option>
          </select>
        )}
      </div>

      <Map
        ref={mapRef}
        mapboxAccessToken={MAPBOX_TOKEN}
        initialViewState={DEFAULT_VIEW}
        style={{ width: '100%', height: '100%' }}
        mapStyle="mapbox://styles/mapbox/streets-v12"
        onClick={handleMapClick}
        cursor={radiusMode ? 'crosshair' : 'grab'}
      >
        <NavigationControl position="bottom-left" />

        {/* Draw polygon control */}
        <DrawControl
          onDraw={(geojson) =>
            onFilterChange({ polygon_geojson: geojson ?? undefined, lat: undefined, lng: undefined, radius_m: undefined })
          }
        />

        {/* Listing markers */}
        {listings.map((listing) =>
          listing.lat != null && listing.lng != null ? (
            <Marker
              key={listing.id}
              longitude={listing.lng}
              latitude={listing.lat}
              onClick={(e) => {
                e.originalEvent.stopPropagation()
                onSelectListing(listing.id)
              }}
            >
              <div
                style={{
                  width: 14,
                  height: 14,
                  borderRadius: '50%',
                  background: SOURCE_COLORS[listing.source],
                  border: selectedId === listing.id ? '3px solid #111' : '2px solid #fff',
                  cursor: 'pointer',
                  boxShadow: '0 1px 4px rgba(0,0,0,0.3)',
                  transform: selectedId === listing.id ? 'scale(1.5)' : 'scale(1)',
                  transition: 'transform 0.15s',
                }}
              />
            </Marker>
          ) : null
        )}

        {/* Radius indicator marker */}
        {filters.lat != null && filters.lng != null && (
          <Marker longitude={filters.lng} latitude={filters.lat}>
            <div style={{ width: 18, height: 18, borderRadius: '50%', background: '#1d4ed8', border: '3px solid #fff', boxShadow: '0 1px 6px rgba(0,0,0,0.4)' }} />
          </Marker>
        )}
      </Map>
    </div>
  )
}
