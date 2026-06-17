import request from '@/utils/request';
import type { Baseline, BaselineCreateParams, BaselineListParams, BaselineListResponse } from '@/types/baseline';

export const baselineApi = {
  create: (data: BaselineCreateParams) =>
    request.post<unknown, Baseline>('/baselines', data),

  list: (params?: BaselineListParams) =>
    request.get<unknown, BaselineListResponse>('/baselines', { params }),

  get: (id: number) =>
    request.get<unknown, Baseline>(`/baselines/${id}`),

  delete: (id: number) =>
    request.delete<unknown, void>(`/baselines/${id}`),
};
