import { useQuery } from '@tanstack/react-query'
import { fetchCities, fetchNeighborhoods } from '../api/client'

/** Canonical list of supported cities (static — long cache). */
export function useCities() {
  return useQuery({
    queryKey: ['cities'],
    queryFn: fetchCities,
    staleTime: Infinity,
  })
}

/** Neighborhoods seen in listings for a city. Disabled until a city is chosen. */
export function useNeighborhoods(city: string | undefined) {
  return useQuery({
    queryKey: ['neighborhoods', city],
    queryFn: () => fetchNeighborhoods(city as string),
    enabled: !!city && city.trim().length > 0,
    staleTime: 5 * 60 * 1000,
  })
}
