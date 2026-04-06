import request from '@/utils/request';
import type { TaskCreateParams, TaskListParams, TaskListResponse, Task, FioTrendPoint, TaskStatusResponse } from '@/types/task';

export const taskApi = {
  create: (data: TaskCreateParams) =>
    request.post<unknown, Task>('/tasks', data),

  list: (params?: TaskListParams) =>
    request.get<unknown, TaskListResponse>('/tasks', { params }),

  get: (id: number) =>
    request.get<unknown, Task>(`/tasks/${id}`),

  getStatus: (id: number) =>
    request.get<unknown, TaskStatusResponse>(`/tasks/${id}/status`),

  delete: (id: number) =>
    request.delete<unknown, void>(`/tasks/${id}`),

  stop: (id: number) =>
    request.post<unknown, Task>(`/tasks/${id}/stop`),

  retry: (id: number) =>
    request.post<unknown, Task>(`/tasks/${id}/retry`),

  getTrend: (id: number, params?: { start?: string; end?: string }) =>
    request.get<unknown, FioTrendPoint[]>(`/tasks/${id}/trend`, { params }),
};
