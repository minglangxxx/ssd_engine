import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { baselineApi } from '@/api/baseline';
import type { BaselineListParams, BaselineCreateParams } from '@/types/baseline';

export const useBaselineList = (params?: BaselineListParams) =>
  useQuery({
    queryKey: ['baselines', params],
    queryFn: () => baselineApi.list(params),
  });

export const useBaselineDetail = (id: number) =>
  useQuery({
    queryKey: ['baseline', id],
    queryFn: () => baselineApi.get(id),
    enabled: !!id,
  });

export const useCreateBaseline = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: BaselineCreateParams) => baselineApi.create(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['baselines'] });
      qc.invalidateQueries({ queryKey: ['tasks'] });
    },
  });
};

export const useDeleteBaseline = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => baselineApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['baselines'] }),
  });
};
