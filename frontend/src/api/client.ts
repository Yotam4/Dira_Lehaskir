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
  return data as { run_id: string; status: string; triggered_at: string }
}

export interface ScrapeRunStatus {
  run_id: string
  status: 'running' | 'completed' | 'failed'
  triggered_at: string
  completed_at: string | null
  listings_found: number | null
  listings_new: number | null
  error_message: string | null
}

export async function fetchScrapeRun(runId: string): Promise<ScrapeRunStatus> {
  const { data } = await api.get<ScrapeRunStatus>(`/scrape/runs/${runId}`)
  return data
}
