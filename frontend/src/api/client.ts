import axios from 'axios'
import type { ListingsPage, SearchFilters } from '../types/listing'

const api = axios.create({
  baseURL: '/api',
})

export async function fetchListings(filters: SearchFilters): Promise<ListingsPage> {
  const { data } = await api.get<ListingsPage>('/listings', { params: filters })
  return data
}

export async function fetchListing(id: string) {
  const { data } = await api.get(`/listings/${id}`)
  return data
}

export async function triggerScrape(payload: {
  sources: string[]
  filters: Omit<SearchFilters, 'page' | 'page_size'>
}) {
  const { data } = await api.post('/scrape/trigger', payload)
  return data
}
