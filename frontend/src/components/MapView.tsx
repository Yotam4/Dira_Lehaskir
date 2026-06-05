import { useCallback, useEffect, useMemo, useRef, useState, type MutableRefObject } from 'react'
import Map, { NavigationControl, Source, Layer, useControl } from 'react-map-gl'
import type { MapRef, LayerProps, IControl } from 'react-map-gl'
import type { Feature, FeatureCollection, Polygon } from 'geojson'
import MapboxDraw from '@mapbox/mapbox-gl-draw'
import type { Listing, SearchFilters } from '../types/listing'
import { SOURCE_COLORS } from '../types/listing'

const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_TOKEN as string

// Default center: Tel Aviv
const DEFAULT_VIEW = { longitude: 34.7818, latitude: 32.0853, zoom: 12 }

type SpatialMode = 'browse' | 'draw' | 'radius'

// Captures the MapboxDraw instance and reports drawn/edited/deleted geometry.
function DrawControl({
  onReady,
  onChange,
}: {
  onReady: (draw: MapboxDraw) => void
  onChange: (geojson: string | null) => void
}) {
  const drawRef: MutableRefObject<MapboxDraw | null> = useRef(null)

  // mapbox-gl-draw's IControl types don't line up with react-map-gl's MapInstance;
  // cast the instance (a long-standing typings gap, runtime is fine).
  useControl(
    () => {
      const draw = new MapboxDraw({ displayControlsDefault: false })
      drawRef.current = draw
      onReady(draw)
      return draw as unknown as IControl
    },
    ({ map }: { map: any }) => {
      const report = () => {
        const data = drawRef.current?.getAll()
        if (data && data.features.length > 0) {
          // Keep only the most recent polygon — drop any earlier ones.
          const last = data.features[data.features.length - 1]
          if (data.features.length > 1) {
            data.features.slice(0, -1).forEach((f) => f.id && drawRef.current?.delete(String(f.id)))
          }
          onChange(JSON.stringify(last.geometry))
        } else {
          onChange(null)
        }
      }
      map.on('draw.create', report)
      map.on('draw.update', report)
      map.on('draw.delete', () => onChange(null))
    },
    () => {},
    { position: 'top-left' },
  )
  return null
}

// Approximate a circle as a GeoJSON polygon for the radius overlay.
function circlePolygon(lng: number, lat: number, radiusM: number, points = 64): Feature<Polygon> {
  const coords: [number, number][] = []
  const earth = 6378137
  const dLat = (radiusM / earth) * (180 / Math.PI)
  const dLng = dLat / Math.cos((lat * Math.PI) / 180)
  for (let i = 0; i <= points; i++) {
    const theta = (i / points) * 2 * Math.PI
    coords.push([lng + dLng * Math.cos(theta), lat + dLat * Math.sin(theta)])
  }
  return { type: 'Feature', properties: {}, geometry: { type: 'Polygon', coordinates: [coords] } }
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
  const drawRef = useRef<MapboxDraw | null>(null)
  const [mode, setMode] = useState<SpatialMode>('browse')

  const hasPolygon = !!filters.polygon_geojson
  const hasRadius = filters.lat != null && filters.lng != null
  const hasSpatial = hasPolygon || hasRadius

  // Auto-fit map to listing markers whenever the result set changes
  useEffect(() => {
    if (!mapRef.current || listings.length === 0) return
    // Only auto-fit on a fresh result set (page 1). Load-more appends to the
    // same view, so re-fitting there would yank the camera and fight any manual
    // pan/zoom the user just did.
    if ((filters.page ?? 1) > 1) return
    const withCoords = listings.filter((l) => l.lat != null && l.lng != null)
    if (withCoords.length === 0) return
    const lngs = withCoords.map((l) => l.lng as number)
    const lats = withCoords.map((l) => l.lat as number)
    mapRef.current.fitBounds(
      [[Math.min(...lngs), Math.min(...lats)], [Math.max(...lngs), Math.max(...lats)]],
      { padding: 60, maxZoom: 14, duration: 600 },
    )
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [listings])

  const geojson = useMemo<FeatureCollection>(() => ({
    type: 'FeatureCollection',
    features: listings
      .filter((l) => l.lat != null && l.lng != null)
      .map((l) => ({
        type: 'Feature',
        properties: { id: l.id, color: SOURCE_COLORS[l.source], selected: l.id === selectedId },
        geometry: { type: 'Point', coordinates: [l.lng!, l.lat!] },
      })),
  }), [listings, selectedId])

  const clusterLayer: LayerProps = {
    id: 'clusters', type: 'circle', source: 'listings', filter: ['has', 'point_count'],
    paint: {
      'circle-color': ['step', ['get', 'point_count'], '#93c5fd', 10, '#3b82f6', 30, '#1d4ed8'],
      'circle-radius': ['step', ['get', 'point_count'], 16, 10, 22, 30, 28],
      'circle-stroke-width': 2, 'circle-stroke-color': '#fff',
    },
  }
  const clusterCountLayer: LayerProps = {
    id: 'cluster-count', type: 'symbol', source: 'listings', filter: ['has', 'point_count'],
    layout: { 'text-field': '{point_count_abbreviated}', 'text-size': 12 }, paint: { 'text-color': '#fff' },
  }
  const unclusteredLayer: LayerProps = {
    id: 'unclustered-point', type: 'circle', source: 'listings', filter: ['!', ['has', 'point_count']],
    paint: {
      'circle-color': ['get', 'color'],
      'circle-radius': ['case', ['==', ['get', 'id'], selectedId ?? ''], 10, 7],
      'circle-stroke-width': ['case', ['==', ['get', 'id'], selectedId ?? ''], 3, 2],
      'circle-stroke-color': ['case', ['==', ['get', 'id'], selectedId ?? ''], '#111', '#fff'],
    },
  }

  const clearSpatial = useCallback(() => {
    drawRef.current?.deleteAll()
    onFilterChange({ polygon_geojson: undefined, lat: undefined, lng: undefined, radius_m: undefined })
    setMode('browse')
  }, [onFilterChange])

  const startDraw = () => {
    drawRef.current?.deleteAll()
    drawRef.current?.changeMode('draw_polygon')
    setMode('draw')
    // Polygon and radius are mutually exclusive.
    onFilterChange({ lat: undefined, lng: undefined, radius_m: undefined })
  }

  const startRadius = () => {
    drawRef.current?.deleteAll()
    setMode('radius')
    // Seed a default radius so the size selector appears immediately and the
    // user can pick a size before placing the centre. radius_m without lat/lng
    // is ignored by the listings query, so this creates no premature filter.
    onFilterChange({ polygon_geojson: undefined, radius_m: filters.radius_m ?? 1000 })
  }

  const stopMode = () => setMode('browse')

  const handleMapClick = useCallback(
    (e: any) => {
      const features = e.features as
        | Array<{ layer: { id: string }; properties: Record<string, unknown>; geometry: { coordinates: number[] } }>
        | undefined
      if (features && features.length > 0) {
        const feature = features[0]
        if (feature.layer.id === 'clusters') {
          const clusterId = feature.properties?.cluster_id as number
          const mapInstance = mapRef.current?.getMap() as any
          const source = mapInstance?.getSource('listings')
          source?.getClusterExpansionZoom(clusterId)
            .then((zoom: number) => {
              mapRef.current?.easeTo({ center: feature.geometry.coordinates as [number, number], zoom })
            })
            .catch(() => {})
        } else if (feature.layer.id === 'unclustered-point') {
          onSelectListing(feature.properties?.id as string)
        }
      } else if (mode === 'radius') {
        onFilterChange({ lat: e.lngLat.lat, lng: e.lngLat.lng, radius_m: filters.radius_m ?? 1000, polygon_geojson: undefined })
        setMode('browse')
      }
    },
    [mode, filters.radius_m, onFilterChange, onSelectListing],
  )

  const onDraw = useCallback(
    (geojson: string | null) => {
      onFilterChange({ polygon_geojson: geojson ?? undefined, lat: undefined, lng: undefined, radius_m: undefined })
      setMode('browse')
    },
    [onFilterChange],
  )

  const radiusCircle = useMemo<FeatureCollection | null>(() => {
    if (!hasRadius) return null
    return { type: 'FeatureCollection', features: [circlePolygon(filters.lng!, filters.lat!, filters.radius_m ?? 1000)] }
  }, [hasRadius, filters.lng, filters.lat, filters.radius_m])

  return (
    <div style={{ position: 'relative', flex: 1, height: '100%' }}>
      {/* Toolbar overlay */}
      <div style={{ position: 'absolute', top: 10, insetInlineEnd: 10, zIndex: 10, display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 6 }}>
        <div style={{ display: 'flex', gap: 6 }}>
          <button onClick={stopMode} style={toolBtn(mode === 'browse')} title="גלישה רגילה">עיון</button>
          <button onClick={startDraw} style={toolBtn(mode === 'draw')} title="צייר אזור על המפה">צייר אזור</button>
          <button onClick={startRadius} style={toolBtn(mode === 'radius')} title="לחץ על המפה לקביעת מרכז">רדיוס</button>
          {hasSpatial && (
            <button onClick={clearSpatial} style={{ ...toolBtn(false), color: '#dc2626', borderColor: '#fecaca' }} title="נקה סינון מרחבי">נקה ✕</button>
          )}
        </div>
        {mode === 'radius' && filters.radius_m && (
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
        {(mode === 'draw' || mode === 'radius') && (
          <div style={hintStyle}>
            {mode === 'draw'
              ? 'לחץ להוספת נקודות, לחיצה כפולה לסגירת האזור'
              : 'לחץ על המפה לבחירת מרכז הרדיוס'}
          </div>
        )}
        {hasSpatial && mode === 'browse' && (
          <div style={{ ...hintStyle, background: '#1d4ed8', color: '#fff' }}>
            {hasPolygon ? 'מסונן לפי אזור מצויר' : `מסונן לפי רדיוס ${filters.radius_m ?? 1000}מ׳`}
          </div>
        )}
      </div>

      <Map
        ref={mapRef}
        mapboxAccessToken={MAPBOX_TOKEN}
        initialViewState={DEFAULT_VIEW}
        style={{ width: '100%', height: '100%' }}
        mapStyle="mapbox://styles/mapbox/streets-v12"
        onClick={handleMapClick}
        cursor={mode === 'radius' ? 'crosshair' : 'grab'}
        interactiveLayerIds={['clusters', 'unclustered-point']}
      >
        <NavigationControl position="bottom-left" />

        <DrawControl onReady={(d) => { drawRef.current = d }} onChange={onDraw} />

        {/* Radius coverage circle */}
        {radiusCircle && (
          <Source id="radius-circle" type="geojson" data={radiusCircle}>
            <Layer id="radius-fill" type="fill" paint={{ 'fill-color': '#1d4ed8', 'fill-opacity': 0.08 }} />
            <Layer id="radius-outline" type="line" paint={{ 'line-color': '#1d4ed8', 'line-width': 2, 'line-dasharray': [2, 1] }} />
          </Source>
        )}

        {/* Clustered listing markers */}
        <Source id="listings" type="geojson" data={geojson} cluster clusterMaxZoom={14} clusterRadius={50}>
          <Layer {...clusterLayer} />
          <Layer {...clusterCountLayer} />
          <Layer {...unclusteredLayer} />
        </Source>

        {/* Radius center marker */}
        {hasRadius && (
          <Source id="radius-center" type="geojson" data={{
            type: 'FeatureCollection',
            features: [{ type: 'Feature', properties: {}, geometry: { type: 'Point', coordinates: [filters.lng!, filters.lat!] } }],
          }}>
            <Layer id="radius-center-point" type="circle" paint={{ 'circle-color': '#1d4ed8', 'circle-radius': 6, 'circle-stroke-width': 2, 'circle-stroke-color': '#fff' }} />
          </Source>
        )}
      </Map>
    </div>
  )
}

function toolBtn(active: boolean): React.CSSProperties {
  return {
    padding: '6px 12px',
    borderRadius: 6,
    border: '1px solid #d1d5db',
    background: active ? '#1d4ed8' : '#fff',
    color: active ? '#fff' : '#374151',
    cursor: 'pointer',
    fontSize: 12,
    fontWeight: 500,
  }
}

const hintStyle: React.CSSProperties = {
  background: '#fff',
  border: '1px solid #d1d5db',
  borderRadius: 6,
  padding: '4px 8px',
  fontSize: 11,
  color: '#374151',
  maxWidth: 220,
}
