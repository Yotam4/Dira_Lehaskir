import axios from 'axios'
import type { ListingsPage, SearchFilters } from '../types/listing'

const api = axios.create({
  baseURL: '/api',
  timeout: 15_000,
  paramsSerializer: {
    serialize: (params: Record<string, unknown>) => {
      const sp = new URLSearchParams()
      for (const [key, val] of Object.entries(params)) {
        if (val === undefined || val === null) continue
        if (Array.isArray(val)) {
          val.forEach((v) => sp.append(key, String(v)))
        } else {
          sp.set(key, String(val))
        }
      }
      return sp.toString()
    },
  },
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
  filters: Omit<SearchFilters, 'page' | 'page_size' | 'sort_by' | 'order'>
}) {
  const { data } = await api.post('/scrape/trigger', payload)
  return data as { run_id: string; status: string; triggered_at: string }
}

export interface ScrapeRunStatus {
  run_id: string
  status: 'queued' | 'running' | 'completed' | 'failed'
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
