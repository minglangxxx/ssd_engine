import { useQuery } from '@tanstack/react-query';
import { nvmeApi } from '@/api/nvme';
import { smartApi } from '@/api';

export const useNvmeList = (deviceId: number) =>
  useQuery({
    queryKey: ['nvme-list', deviceId],
    queryFn: () => nvmeApi.getList(deviceId),
    enabled: !!deviceId,
  });

export type NvmeDetailType = 'id-ctrl' | 'id-ns' | 'smart-log' | 'error-log' | null;

export const useNvmeDetail = (deviceId: number, diskName: string, type: NvmeDetailType) => {
  const queryFnMap: Record<string, () => Promise<unknown>> = {
    'id-ctrl': () => nvmeApi.getIdCtrl(deviceId, diskName),
    'id-ns': () => nvmeApi.getIdNs(deviceId, diskName),
    'smart-log': () => smartApi.getLatest(deviceId),
    'error-log': () => nvmeApi.getErrorLog(deviceId, diskName),
  };
  const queryKey = type === 'smart-log'
    ? ['nvme-detail', deviceId, 'smart-log']
    : ['nvme-detail', deviceId, diskName, type];
  return useQuery({
    queryKey,
    queryFn: () => queryFnMap[type!](),
    enabled: !!deviceId && !!diskName && !!type && type in queryFnMap,
  });
};
