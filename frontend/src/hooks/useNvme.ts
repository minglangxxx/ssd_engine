import { useQuery } from '@tanstack/react-query';
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
