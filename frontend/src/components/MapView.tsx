import { useCallback, useEffect, useMemo, useRef, useState, type MutableRefObject } from 'react'
import Map, { NavigationControl, Source, Layer, useControl } from 'react-map-gl'
import type { MapRef, LayerProps } from 'react-map-gl'
import type { FeatureCollection } from 'geojson'
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

  // Auto-fit map to listing markers whenever the result set changes
  useEffect(() => {
    if (!mapRef.current || listings.length === 0) return
    const withCoords = listings.filter((l) => l.lat != null && l.lng != null)
    if (withCoords.length === 0) return
    const lngs = withCoords.map((l) => l.lng as number)
    const lats = withCoords.map((l) => l.lat as number)
    mapRef.current.fitBounds(
      [[Math.min(...lngs), Math.min(...lats)], [Math.max(...lngs), Math.max(...lats)]],
      { padding: 60, maxZoom: 14, duration: 600 },
    )
  }, [listings])

  // Build GeoJSON from listings (memoised to avoid unnecessary rebuilds)
  const geojson = useMemo<FeatureCollection>(() => ({
    type: 'FeatureCollection',
    features: listings
      .filter((l) => l.lat != null && l.lng != null)
      .map((l) => ({
        type: 'Feature',
        properties: {
          id: l.id,
          color: SOURCE_COLORS[l.source],
          selected: l.id === selectedId,
        },
        geometry: { type: 'Point', coordinates: [l.lng!, l.lat!] },
      })),
  }), [listings, selectedId])

  // Layer definitions
  const clusterLayer: LayerProps = {
    id: 'clusters',
    type: 'circle',
    source: 'listings',
    filter: ['has', 'point_count'],
    paint: {
      'circle-color': ['step', ['get', 'point_count'], '#93c5fd', 10, '#3b82f6', 30, '#1d4ed8'],
      'circle-radius': ['step', ['get', 'point_count'], 16, 10, 22, 30, 28],
      'circle-stroke-width': 2,
      'circle-stroke-color': '#fff',
    },
  }

  const clusterCountLayer: LayerProps = {
    id: 'cluster-count',
    type: 'symbol',
    source: 'listings',
    filter: ['has', 'point_count'],
    layout: {
      'text-field': '{point_count_abbreviated}',
      'text-size': 12,
    },
    paint: { 'text-color': '#fff' },
  }

  const unclusteredLayer: LayerProps = {
    id: 'unclustered-point',
    type: 'circle',
    source: 'listings',
    filter: ['!', ['has', 'point_count']],
    paint: {
      'circle-color': ['get', 'color'],
      'circle-radius': ['case', ['==', ['get', 'id'], selectedId ?? ''], 10, 7],
      'circle-stroke-width': ['case', ['==', ['get', 'id'], selectedId ?? ''], 3, 2],
      'circle-stroke-color': ['case', ['==', ['get', 'id'], selectedId ?? ''], '#111', '#fff'],
    },
  }

  const handleMapClick = useCallback(
    (e: any) => {
      const features = e.features as Array<{ layer: { id: string }; properties: Record<string, unknown>; geometry: { coordinates: number[] } }> | undefined
      if (features && features.length > 0) {
        const feature = features[0]
        if (feature.layer.id === 'clusters') {
          const clusterId = feature.properties?.cluster_id as number
          const mapInstance = mapRef.current?.getMap() as any
          const source = mapInstance?.getSource('listings')
          source?.getClusterExpansionZoom(clusterId).then((zoom: number) => {
            mapRef.current?.easeTo({ center: feature.geometry.coordinates as [number, number], zoom })
          })
        } else if (feature.layer.id === 'unclustered-point') {
          onSelectListing(feature.properties?.id as string)
        }
      } else if (radiusMode) {
        onFilterChange({
          lat: e.lngLat.lat,
          lng: e.lngLat.lng,
          radius_m: 1000,
          polygon_geojson: undefined,
        })
        setRadiusMode(false)
      }
    },
    [radiusMode, onFilterChange, onSelectListing]
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
          חיפוש רדיוס
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
        interactiveLayerIds={['clusters', 'unclustered-point']}
      >
        <NavigationControl position="bottom-left" />

        {/* Draw polygon control */}
        <DrawControl
          onDraw={(geojson) =>
            onFilterChange({ polygon_geojson: geojson ?? undefined, lat: undefined, lng: undefined, radius_m: undefined })
          }
        />

        {/* Clustered listing markers */}
        <Source
          id="listings"
          type="geojson"
          data={geojson}
          cluster={true}
          clusterMaxZoom={14}
          clusterRadius={50}
        >
          <Layer {...clusterLayer} />
          <Layer {...clusterCountLayer} />
          <Layer {...unclusteredLayer} />
        </Source>

        {/* Radius indicator marker */}
        {filters.lat != null && filters.lng != null && (
          <Source
            id="radius-center"
            type="geojson"
            data={{
              type: 'FeatureCollection',
              features: [{ type: 'Feature', properties: {}, geometry: { type: 'Point', coordinates: [filters.lng, filters.lat] } }],
            }}
          >
            <Layer
              id="radius-center-point"
              type="circle"
              paint={{ 'circle-color': '#1d4ed8', 'circle-radius': 9, 'circle-stroke-width': 3, 'circle-stroke-color': '#fff' }}
            />
          </Source>
        )}
      </Map>
    </div>
  )
}
