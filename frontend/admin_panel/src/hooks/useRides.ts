import { useQuery } from '@tanstack/react-query';
import { apiRequest } from '../api/client';
import type { ActiveRide } from '../types/admin';

interface RideFilters {
  region_id?: string;
  status?: string;
  search?: string;
}

export function useActiveRides(filters: RideFilters = {}) {
  const params = new URLSearchParams();
  if (filters.region_id) params.set('region_id', filters.region_id);
  if (filters.status) params.set('status', filters.status);
  if (filters.search) params.set('search', filters.search);
  const qs = params.toString();

  return useQuery({
    queryKey: ['rides', 'active', filters],
    queryFn: () => apiRequest<{ data: ActiveRide[] }>(`/admin/rides/active${qs ? '?' + qs : ''}`).then(r => r.data ?? []),
    refetchInterval: 5_000,
    refetchOnWindowFocus: true,
  });
}
