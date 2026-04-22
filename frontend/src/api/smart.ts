import request from '@/utils/request';
import type {
  SmartLatestResponse,
  SmartHistoryResponse,
  HealthScoreResponse,
  SmartAlertsResponse,
} from '@/types/smart';

export const smartApi = {
  getLatest: (deviceId: number) =>
    request.get<unknown, SmartLatestResponse>(`/devices/${deviceId}/smart/latest`),

  getHistory: (deviceId: number, diskName: string, params?: { start?: string; end?: string }) =>
    request.get<unknown, SmartHistoryResponse>(`/devices/${deviceId}/smart/history`, {
      params: { disk_name: diskName, ...params },
    }),

  getHealthScore: (deviceId: number) =>
    request.get<unknown, HealthScoreResponse>(`/devices/${deviceId}/smart/health-score`),

  getAlerts: (deviceId: number) =>
    request.get<unknown, SmartAlertsResponse>(`/devices/${deviceId}/smart/alerts`),
};