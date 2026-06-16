import request from '@/utils/request';
import type { Device, DeviceAddParams, DeviceInfo, DeviceUpdateParams } from '@/types/device';

export const deviceApi = {
  list: () =>
    request.get<unknown, Device[]>('/devices'),

  add: (data: DeviceAddParams) =>
    request.post<unknown, Device>('/devices', data),

  update: (id: number, data: DeviceUpdateParams) =>
    request.put<unknown, Device>(`/devices/${id}`, data),

  delete: (id: number) =>
    request.delete<unknown, void>(`/devices/${id}`),

  getInfo: (id: number) =>
    request.get<unknown, DeviceInfo>(`/devices/${id}/info`),

  testConnection: (params: { ip: string; user?: string; password?: string }) =>
    request.post<unknown, { success: boolean; message: string }>('/devices/test-connection', params),

  getAgentStatus: (id: number) =>
    request.get<unknown, { status: string; version: string }>(`/devices/${id}/agent-status`),
};