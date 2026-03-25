import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiRequest } from '../api/client';
import type { Driver, PaginatedResponse } from '../types/admin';

const DRIVERS_RECONCILE_MS = 60_000;

interface DriverFilters {
  region_id?: string;
  status?: string;
  search?: string;
  page?: number;
  page_size?: number;
}

export function useDriversList(filters: DriverFilters = {}) {
  const params = new URLSearchParams();
  if (filters.region_id) params.set('region_id', filters.region_id);
  if (filters.status) params.set('status', filters.status);
  if (filters.page) params.set('page', String(filters.page));
  if (filters.page_size) params.set('page_size', String(filters.page_size));
  const qs = params.toString();

  return useQuery({
    queryKey: ['drivers', 'list', filters],
    queryFn: () => apiRequest<{ data: Driver[] | PaginatedResponse<Driver> }>(`/admin/drivers${qs ? '?' + qs : ''}`).then(r => {
      const d = r.data;
      if (Array.isArray(d)) return { items: d, pagination: { page: 1, page_size: d.length, total_items: d.length, total_pages: 1 } };
      return d as PaginatedResponse<Driver>;
    }),
    refetchInterval: DRIVERS_RECONCILE_MS,
    refetchOnWindowFocus: true,
  });
}

export function useDriverDetail(driverId: string) {
  return useQuery({
    queryKey: ['drivers', 'detail', driverId],
    queryFn: () => apiRequest<{ data: Driver }>(`/admin/drivers/${driverId}`).then(r => r.data),
    enabled: !!driverId,
  });
}

export function useSuspendDriver() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ driverId, reason }: { driverId: string; reason: string }) =>
      apiRequest(`/admin/drivers/${driverId}/suspend`, { method: 'POST', body: { reason } }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['drivers'] }),
  });
}

export function useReactivateDriver() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ driverId }: { driverId: string }) =>
      apiRequest(`/admin/drivers/${driverId}/reactivate`, { method: 'POST' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['drivers'] }),
  });
}
