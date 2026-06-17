import request from '@/utils/request';
import type { RegressionResult, RegressionListParams, RegressionListResponse } from '@/types/regression';

export const regressionApi = {
  run: (data: { task_id: number; baseline_id: number }) =>
    request.post<unknown, RegressionResult>('/regressions', data),

  list: (params?: RegressionListParams) =>
    request.get<unknown, RegressionListResponse>('/regressions', { params }),

  get: (id: number) =>
    request.get<unknown, RegressionResult>(`/regressions/${id}`),
};
