import { useQuery } from '@tanstack/react-query'
import { fetchListings } from '../api/client'
import type { SearchFilters } from '../types/listing'

export function useListings(filters: SearchFilters) {
  return useQuery({
    queryKey: ['listings', filters],
    queryFn: () => fetchListings(filters),
    placeholderData: (prev) => prev,
  })
}
