import { useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';

import { buildAuthenticatedApiUrl } from '../api/client';

export function useDashboardPresenceStream(enabled = true) {
  const queryClient = useQueryClient();

  useEffect(() => {
    if (!enabled || typeof window === 'undefined') {
      return;
    }

    const eventSource = new EventSource(buildAuthenticatedApiUrl('/admin/dashboard/stream'));

    const refreshDashboard = () => {
      void queryClient.invalidateQueries({ queryKey: ['dashboard', 'summary'] });
      void queryClient.invalidateQueries({ queryKey: ['drivers', 'list'] });
    };

    eventSource.addEventListener('presence', refreshDashboard);
    eventSource.addEventListener('summary', refreshDashboard);
    eventSource.onerror = () => {
      // EventSource reconnects automatically; periodic query reconciliation remains as backup.
    };

    return () => {
      eventSource.removeEventListener('presence', refreshDashboard);
      eventSource.removeEventListener('summary', refreshDashboard);
      eventSource.close();
    };
  }, [enabled, queryClient]);
}
