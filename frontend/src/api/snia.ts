import request from '@/utils/request';
import type {
  SniaTask,
  SniaTaskCreateParams,
  SniaTaskListParams,
  SniaTaskListResponse,
  SniaReport,
} from '@/types/snia';

export const sniaApi = {
  create: (data: SniaTaskCreateParams) =>
    request.post<unknown, SniaTask>('/snia-tasks', data),

  list: (params?: SniaTaskListParams) =>
    request.get<unknown, SniaTaskListResponse>('/snia-tasks', { params }),

  get: (id: number) =>
    request.get<unknown, SniaTask>(`/snia-tasks/${id}`),

  abort: (id: number) =>
    request.post<unknown, SniaTask>(`/snia-tasks/${id}/abort`),

  report: (id: number): Promise<SniaReport> =>
    request.get<unknown, SniaReport>(`/snia-tasks/${id}/report`),
};
