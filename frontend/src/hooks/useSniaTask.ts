import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { sniaApi } from '@/api/snia';
import type { SniaTaskListParams, SniaTaskCreateParams } from '@/types/snia';

const isTerminal = (status: string) => ['done', 'failed', 'aborted'].includes(status);

export const useSniaTaskList = (params?: SniaTaskListParams) =>
  useQuery({
    queryKey: ['snia-tasks', params],
    queryFn: () => sniaApi.list(params),
  });

export const useSniaTaskDetail = (id: number) =>
  useQuery({
    queryKey: ['snia-task', id],
    queryFn: () => sniaApi.get(id),
    enabled: !!id,
    refetchInterval: (data) => (data?.status && !isTerminal(data.status) ? 3000 : false),
  });

export const useCreateSniaTask = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: SniaTaskCreateParams) => sniaApi.create(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['snia-tasks'] });
      qc.invalidateQueries({ queryKey: ['tasks'] });
    },
  });
};

export const useAbortSniaTask = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => sniaApi.abort(id),
    onSuccess: (_data, id) => {
      qc.invalidateQueries({ queryKey: ['snia-task', id] });
      qc.invalidateQueries({ queryKey: ['snia-tasks'] });
    },
  });
};
