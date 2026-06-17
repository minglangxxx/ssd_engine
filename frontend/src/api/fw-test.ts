import request from '@/utils/request';
import type { FwUpgradeTest, FwTestCreateParams, FwTestListParams, FwTestListResponse, FwTestReport } from '@/types/fw-test';

export const fwTestApi = {
  create: (data: FwTestCreateParams) =>
    request.post<unknown, FwUpgradeTest>('/fw-tests', data),

  list: (params?: FwTestListParams) =>
    request.get<unknown, FwTestListResponse>('/fw-tests', { params }),

  get: (id: number) =>
    request.get<unknown, FwUpgradeTest>(`/fw-tests/${id}`),

  confirmUpgrade: (id: number) =>
    request.post<unknown, FwUpgradeTest>(`/fw-tests/${id}/confirm-upgrade`),

  abort: (id: number) =>
    request.post<unknown, FwUpgradeTest>(`/fw-tests/${id}/abort`),

  report: (id: number) =>
    request.get<unknown, FwTestReport>(`/fw-tests/${id}/report`),
};
