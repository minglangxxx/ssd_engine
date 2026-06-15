import request from '@/utils/request';
import type { DataListParams, DataListResponse, DataOverview } from '@/types/data';

export const dataApi = {
  list: (params?: DataListParams) =>
    request.get<unknown, DataListResponse>('/data', { params }),

  getOverview: () =>
    request.get<unknown, DataOverview>('/data/overview'),

  download: (ids: number[]) =>
    request.post('/data/download', { ids }, { responseType: 'blob' }),

  archive: (ids: number[]) =>
    request.post<unknown, { archived_count: number; archived_ids: number[] }>('/data/archive', { ids }),

  delete: (ids: number[]) =>
    request.post<unknown, void>('/data/delete', { ids }),

  compress: (ids: number[]) =>
    request.post<unknown, void>('/data/compress', { ids }),
};
