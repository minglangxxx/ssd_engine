import { useQuery } from '@tanstack/react-query';
import { dashboardApi } from '@/api/dashboard';

export const useDashboardSummary = () =>
  useQuery({
    queryKey: ['dashboard', 'summary'],
    queryFn: () => dashboardApi.summary(),
    refetchInterval: 5000,
  });
