import request from '@/utils/request';
import type { Device, DeviceAddParams, DeviceUpdateParams } from '@/types/device';

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
    request.get<unknown, Device>(`/devices/${id}/info`),

  testConnection: (params: { ip: string; user: string; password: string }) => {
    // 如果密码为空，则设置默认值
    const updatedParams = {
      ...params,
      password: params.password || '123456'
    };
    return request.post<unknown, { success: boolean; message: string }>('/devices/test-connection', updatedParams);
  },

  getAgentStatus: (id: number) =>
    request.get<unknown, { status: string; version: string }>(`/devices/${id}/agent-status`),
};