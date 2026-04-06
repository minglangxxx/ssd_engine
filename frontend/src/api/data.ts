import request from '@/utils/request';
import type { DataListParams, DataListResponse, DataOverview } from '@/types/data';

export const dataApi = {
  list: (params?: DataListParams) =>
    request.get<unknown, DataListResponse>('/data', { params }),

  getOverview: () =>
    request.get<unknown, DataOverview>('/data/overview'),

  download: (ids: number[], format: 'json' | 'csv') =>
    request.post('/data/download', { ids, format }, { responseType: 'blob' }),

  archive: (ids: number[]) =>
    request.post<unknown, void>('/data/archive', { ids }),

  delete: (ids: number[]) =>
    request.post<unknown, void>('/data/delete', { ids }),
};
