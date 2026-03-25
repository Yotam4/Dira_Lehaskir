export type ListingSource = 'yad2' | 'madlan' | 'facebook'

export interface Listing {
  id: string
  source: ListingSource
  original_url: string | null
  title: string
  description: string | null
  phone: string | null
  price: number | null       // ILS
  rooms: number | null       // can be 3.5
  sqm: number | null
  floor: number | null
  address: string | null
  city: string
  neighborhood: string | null
  lat: number | null
  lng: number | null
  amenities: Record<string, unknown>
  images: string[]
  scraped_at: string
  created_at: string
  updated_at: string
}

export interface ListingsPage {
  items: Listing[]
  total: number
  page: number
  page_size: number
}

/** Search filters sent to GET /listings */
export interface SearchFilters {
  // City / neighbourhood
  city?: string
  neighborhood?: string

  // Point + radius
  lat?: number
  lng?: number
  radius_m?: number

  // Drawn polygon (GeoJSON Polygon geometry JSON string)
  polygon_geojson?: string

  // Attribute filters — multi-source (repeatable param)
  sources?: ListingSource[]
  price_min?: number
  price_max?: number
  rooms_min?: number
  rooms_max?: number

  // Sort
  sort_by?: 'price' | 'rooms' | 'sqm' | 'scraped_at'
  order?: 'asc' | 'desc'

  // Pagination
  page?: number
  page_size?: number
}

export const SOURCE_COLORS: Record<ListingSource, string> = {
  yad2: '#3b82f6',      // blue
  madlan: '#22c55e',    // green
  facebook: '#a855f7',  // purple
}

export const SOURCE_LABELS: Record<ListingSource, string> = {
  yad2: 'יד 2',
  madlan: 'מדלן',
  facebook: 'פייסבוק',
}
