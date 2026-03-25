import { useQuery } from '@tanstack/react-query';
import { apiRequest } from '../api/client';
import type { DashboardSummary } from '../types/admin';

const DASHBOARD_RECONCILE_MS = 60_000;

export function useDashboardSummary() {
  return useQuery({
    queryKey: ['dashboard', 'summary'],
    queryFn: () => apiRequest<{ data: DashboardSummary }>('/admin/dashboard/summary').then(r => r.data),
    refetchInterval: DASHBOARD_RECONCILE_MS,
    refetchOnWindowFocus: true,
  });
}
