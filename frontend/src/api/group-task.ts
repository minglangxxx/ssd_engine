import request from '@/utils/request';
import type {
  GroupTask,
  GroupTaskCreateParams,
  GroupTaskListParams,
  GroupTaskListResponse,
} from '@/types/group-task';

export const groupTaskApi = {
  create: (data: GroupTaskCreateParams) =>
    request.post<unknown, GroupTask>('/group-tasks', data),

  list: (params?: GroupTaskListParams) =>
    request.get<unknown, GroupTaskListResponse>('/group-tasks', { params }),

  get: (id: number) =>
    request.get<unknown, GroupTask>(`/group-tasks/${id}`),

  delete: (id: number) =>
    request.delete<unknown, void>(`/group-tasks/${id}`),
};
