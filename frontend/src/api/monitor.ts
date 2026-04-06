import request from '@/utils/request';
import type { HostMetricPoint, DiskMetricPoint, HostSummary } from '@/types/monitor';

export const monitorApi = {
  getHostMetrics: (host: string, params?: { start?: string; end?: string }) =>
    request.get<unknown, HostMetricPoint[]>(`/monitor/hosts/${host}/metrics`, { params }),

  getDiskMetrics: (host: string, disk: string, params?: { start?: string; end?: string }) =>
    request.get<unknown, DiskMetricPoint[]>(`/monitor/hosts/${host}/disks/${disk}/metrics`, { params }),

  getDiskList: (host: string) =>
    request.get<unknown, string[]>(`/monitor/hosts/${host}/disks`),

  getHostSummary: (host: string) =>
    request.get<unknown, HostSummary>(`/monitor/hosts/${host}/summary`),
};
