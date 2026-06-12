import request from '@/utils/request';
import type { NvmeListResponse, NvmeDetailResponse } from '@/types/nvme';

export const nvmeApi = {
  getList: (deviceId: number) =>
    request.get<unknown, NvmeListResponse>(`/devices/${deviceId}/nvme/list`),

  getIdCtrl: (deviceId: number, diskName: string) =>
    request.get<unknown, NvmeDetailResponse>(`/devices/${deviceId}/nvme/${diskName}/id-ctrl`),

  getIdNs: (deviceId: number, diskName: string) =>
    request.get<unknown, NvmeDetailResponse>(`/devices/${deviceId}/nvme/${diskName}/id-ns`),

  getErrorLog: (deviceId: number, diskName: string) =>
    request.get<unknown, NvmeDetailResponse>(`/devices/${deviceId}/nvme/${diskName}/error-log`),
};
