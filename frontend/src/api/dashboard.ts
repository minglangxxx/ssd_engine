import request from '@/utils/request';

export interface DashboardSummary {
  agents: { total: number; online: number };
  avg_cpu: number | null;
  avg_memory: number | null;
  tasks: { total: number; running: number; success: number; failed: number };
  recent_tasks: RecentTask[];
  chart_data: ChartDataPoint[];
}

export interface RecentTask {
  id: number;
  name: string;
  status: string;
  iops: number | null;
  bw_mib: number | null;
  lat_mean_us: number | null;
  lat_max_us: number | null;
  created_at: string;
}

export interface ChartDataPoint {
  time: string;
  iops: number | null;
  lat_ms: number | null;
}

export const dashboardApi = {
  summary: () => request.get<unknown, DashboardSummary>('/dashboard/summary'),
};
