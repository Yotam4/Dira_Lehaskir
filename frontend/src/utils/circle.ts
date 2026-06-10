import type { Feature, Polygon } from 'geojson'

/**
 * Approximate a geographic circle (centre + radius in metres) as a closed
 * GeoJSON polygon, for drawing the radius-search overlay on the map. Uses an
 * equirectangular approximation: latitude degrees are constant, longitude
 * degrees are scaled by cos(lat). Accurate enough at city scale; the actual
 * listings query uses PostGIS geography for the real filter.
 */
export function circlePolygon(
  lng: number,
  lat: number,
  radiusM: number,
  points = 64,
): Feature<Polygon> {
  const coords: [number, number][] = []
  const earth = 6378137 // metres
  const dLat = (radiusM / earth) * (180 / Math.PI)
  const dLng = dLat / Math.cos((lat * Math.PI) / 180)
  for (let i = 0; i <= points; i++) {
    const theta = (i / points) * 2 * Math.PI
    coords.push([lng + dLng * Math.cos(theta), lat + dLat * Math.sin(theta)])
  }
  return { type: 'Feature', properties: {}, geometry: { type: 'Polygon', coordinates: [coords] } }
}
