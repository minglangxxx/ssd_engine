import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { regressionApi } from '@/api/regression';
import type { RegressionListParams } from '@/types/regression';

export const useRegressionList = (params?: RegressionListParams) =>
  useQuery({
    queryKey: ['regressions', params],
    queryFn: () => regressionApi.list(params),
  });

export const useRegressionDetail = (id: number) =>
  useQuery({
    queryKey: ['regression', id],
    queryFn: () => regressionApi.get(id),
    enabled: !!id,
  });

export const useRunRegression = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { task_id: number; baseline_id: number }) => regressionApi.run(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['regressions'] }),
  });
};
