import { describe, it, expect } from 'vitest'
import { circlePolygon } from './circle'

describe('circlePolygon', () => {
  it('returns a closed ring with points+1 vertices', () => {
    const f = circlePolygon(34.78, 32.08, 1000, 64)
    const ring = f.geometry.coordinates[0]
    expect(ring).toHaveLength(65)
    expect(ring[0]).toEqual(ring[ring.length - 1]) // closed
  })

  it('is centred on the given point', () => {
    const lng = 34.78
    const lat = 32.08
    const ring = circlePolygon(lng, lat, 1000).geometry.coordinates[0]
    const lngs = ring.map(([x]) => x)
    const lats = ring.map(([, y]) => y)
    // Midpoint of the extremes is the centre (symmetric ring).
    expect((Math.max(...lngs) + Math.min(...lngs)) / 2).toBeCloseTo(lng, 6)
    expect((Math.max(...lats) + Math.min(...lats)) / 2).toBeCloseTo(lat, 6)
  })

  it('scales longitude by 1/cos(lat) so the drawn circle looks round', () => {
    const lat = 32.08
    const ring = circlePolygon(34.78, lat, 1000).geometry.coordinates[0]
    const lngs = ring.map(([x]) => x)
    const lats = ring.map(([, y]) => y)
    const dLng = (Math.max(...lngs) - Math.min(...lngs)) / 2
    const dLat = (Math.max(...lats) - Math.min(...lats)) / 2
    // East-west degree span must be larger than north-south by ~1/cos(lat).
    expect(dLng / dLat).toBeCloseTo(1 / Math.cos((lat * Math.PI) / 180), 2)
  })

  it('grows the radius roughly linearly with metres', () => {
    const small = circlePolygon(34.78, 32.08, 500).geometry.coordinates[0]
    const big = circlePolygon(34.78, 32.08, 2000).geometry.coordinates[0]
    const span = (ring: number[][]) => Math.max(...ring.map(([, y]) => y)) - Math.min(...ring.map(([, y]) => y))
    expect(span(big) / span(small)).toBeCloseTo(4, 1)
  })
})
