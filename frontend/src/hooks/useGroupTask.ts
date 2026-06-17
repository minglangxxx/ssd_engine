import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { groupTaskApi } from '@/api/group-task';
import type { GroupTaskListParams, GroupTaskCreateParams } from '@/types/group-task';

export const useGroupTaskList = (params?: GroupTaskListParams) =>
  useQuery({
    queryKey: ['group-tasks', params],
    queryFn: () => groupTaskApi.list(params),
  });

export const useGroupTaskDetail = (id: number) =>
  useQuery({
    queryKey: ['group-task', id],
    queryFn: () => groupTaskApi.get(id),
    enabled: !!id,
    refetchInterval: (data) =>
      data?.status && ['pending', 'running'].includes(data.status) ? 3000 : false,
  });

export const useCreateGroupTask = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: GroupTaskCreateParams) => groupTaskApi.create(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['group-tasks'] });
      qc.invalidateQueries({ queryKey: ['tasks'] });
    },
  });
};

export const useDeleteGroupTask = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => groupTaskApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['group-tasks'] }),
  });
};
