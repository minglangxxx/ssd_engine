import request from '@/utils/request';
import type { NvmeListResponse, NvmeDetailResponse, NvmeFeatureResponse, NvmeFwLogResponse, NvmeTestRecord, NvmeTestListResponse } from '@/types/nvme';

export const nvmeApi = {
  getList: (deviceId: number) =>
    request.get<unknown, NvmeListResponse>(`/devices/${deviceId}/nvme/list`),

  getIdCtrl: (deviceId: number, diskName: string) =>
    request.get<unknown, NvmeDetailResponse>(`/devices/${deviceId}/nvme/${diskName}/id-ctrl`),

  getIdNs: (deviceId: number, diskName: string) =>
    request.get<unknown, NvmeDetailResponse>(`/devices/${deviceId}/nvme/${diskName}/id-ns`),

  getErrorLog: (deviceId: number, diskName: string) =>
    request.get<unknown, NvmeDetailResponse>(`/devices/${deviceId}/nvme/${diskName}/error-log`),

  getFeature: (deviceId: number, diskName: string, fid: string = '0x06') =>
    request.get<unknown, NvmeFeatureResponse>(
      `/devices/${deviceId}/nvme/${diskName}/get-feature`,
      { params: { fid } }
    ),

  getFwLog: (deviceId: number, diskName: string) =>
    request.get<unknown, NvmeFwLogResponse>(
      `/devices/${deviceId}/nvme/${diskName}/fw-log`
    ),

  runValidation: (deviceId: number, diskName: string, testType: string) =>
    request.post<unknown, { test_id: number; status: string }>(
      `/devices/${deviceId}/nvme/validate`,
      { disk_name: diskName, test_type: testType }
    ),

  getValidationResult: (testId: number) =>
    request.get<unknown, NvmeTestRecord>(
      `/nvme-tests/${testId}`
    ),

  listValidations: (deviceId: number, params?: {
    disk_name?: string;
    test_type?: string;
    page?: number;
    pageSize?: number;
  }) =>
    request.get<unknown, NvmeTestListResponse>(
      `/devices/${deviceId}/nvme-tests`,
      { params }
    ),
};
