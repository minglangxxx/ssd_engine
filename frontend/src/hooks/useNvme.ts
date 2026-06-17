import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { nvmeApi } from '@/api/nvme';
import { smartApi } from '@/api';

export const useNvmeList = (deviceId: number) =>
  useQuery({
    queryKey: ['nvme-list', deviceId],
    queryFn: () => nvmeApi.getList(deviceId),
    enabled: !!deviceId,
  });

export type NvmeDetailType = 'id-ctrl' | 'id-ns' | 'smart-log' | 'error-log' | 'get-feature' | 'fw-log' | null;

export const useNvmeDetail = (deviceId: number, diskName: string, type: NvmeDetailType, fid?: string) => {
  const queryFnMap: Record<string, () => Promise<unknown>> = {
    'id-ctrl': () => nvmeApi.getIdCtrl(deviceId, diskName),
    'id-ns': () => nvmeApi.getIdNs(deviceId, diskName),
    'smart-log': () => smartApi.getLatest(deviceId),
    'error-log': () => nvmeApi.getErrorLog(deviceId, diskName),
    'get-feature': () => nvmeApi.getFeature(deviceId, diskName, fid || '0x06'),
    'fw-log': () => nvmeApi.getFwLog(deviceId, diskName),
  };
  const queryKey = type === 'smart-log'
    ? ['nvme-detail', deviceId, 'smart-log']
    : type === 'get-feature'
      ? ['nvme-detail', deviceId, diskName, type, fid]
      : ['nvme-detail', deviceId, diskName, type];
  return useQuery({
    queryKey,
    queryFn: () => queryFnMap[type!](),
    enabled: !!deviceId && !!diskName && !!type && type in queryFnMap,
  });
};

export const useNvmeValidation = (deviceId: number, diskName: string, testType: string) =>
  useMutation({
    mutationFn: () => nvmeApi.runValidation(deviceId, diskName, testType),
  });

export const useNvmeValidationResult = (testId: number, enabled: boolean) =>
  useQuery({
    queryKey: ['nvme-validation', testId],
    queryFn: () => nvmeApi.getValidationResult(testId),
    enabled: !!testId && enabled,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return (status === 'pending' || status === 'running') ? 3000 : false;
    },
  });

export const useNvmeValidationList = (deviceId: number, params?: object) =>
  useQuery({
    queryKey: ['nvme-validation-list', deviceId, params],
    queryFn: () => nvmeApi.listValidations(deviceId, params as { disk_name?: string; test_type?: string; page?: number; pageSize?: number }),
    enabled: !!deviceId,
  });
