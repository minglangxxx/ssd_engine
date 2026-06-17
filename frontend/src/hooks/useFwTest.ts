import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fwTestApi } from '@/api/fw-test';
import type { FwTestListParams, FwTestCreateParams, FwTestStatus } from '@/types/fw-test';

export const useFwTestList = (params?: FwTestListParams) =>
  useQuery({
    queryKey: ['fw-tests', params],
    queryFn: () => fwTestApi.list(params),
  });

export const useFwTestDetail = (id: number) =>
  useQuery({
    queryKey: ['fw-test', id],
    queryFn: () => fwTestApi.get(id),
    enabled: !!id,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (
        status === 'pending' ||
        status === 'collecting_baseline' ||
        status === 'testing_after' ||
        status === 'waiting_upgrade'
      ) {
        return 3000;
      }
      return false;
    },
  });

export const useCreateFwTest = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: FwTestCreateParams) => fwTestApi.create(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['fw-tests'] }),
  });
};

export const useConfirmFwUpgrade = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => fwTestApi.confirmUpgrade(id),
    onSuccess: (_data, id) => {
      qc.invalidateQueries({ queryKey: ['fw-tests'] });
      qc.invalidateQueries({ queryKey: ['fw-test', id] });
    },
  });
};

export const useAbortFwTest = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => fwTestApi.abort(id),
    onSuccess: (_data, id) => {
      qc.invalidateQueries({ queryKey: ['fw-tests'] });
      qc.invalidateQueries({ queryKey: ['fw-test', id] });
    },
  });
};

export const useFwTestReport = (id: number, status?: FwTestStatus) =>
  useQuery({
    queryKey: ['fw-test-report', id],
    queryFn: () => fwTestApi.report(id),
    enabled: !!id && (status === 'done' || status === 'failed'),
  });
