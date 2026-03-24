import type { Listing } from '../types/listing'

export const mockListing: Listing = {
  id: 'abc-123',
  source: 'yad2',
  original_url: 'https://yad2.co.il/item/abc123',
  title: 'דירת 3 חדרים בתל אביב',
  description: 'דירה מרווחת עם מרפסת נוף לים',
  price: 5500,
  rooms: 3,
  sqm: 75,
  floor: 2,
  address: 'רחוב דיזנגוף 1',
  city: 'תל אביב',
  neighborhood: 'לב העיר',
  lat: 32.08,
  lng: 34.78,
  amenities: {},
  images: [],
  scraped_at: '2026-03-24T10:00:00Z',
  created_at: '2026-03-24T10:00:00Z',
}

export const mockListingWithImages: Listing = {
  ...mockListing,
  id: 'abc-456',
  images: [
    'https://example.com/img1.jpg',
    'https://example.com/img2.jpg',
  ],
}
