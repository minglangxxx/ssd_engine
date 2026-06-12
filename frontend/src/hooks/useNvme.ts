import { useQuery } from '@tanstack/react-query';
import { nvmeApi } from '@/api/nvme';

export const useNvmeList = (deviceId: number) =>
  useQuery({
    queryKey: ['nvme-list', deviceId],
    queryFn: () => nvmeApi.getList(deviceId),
    enabled: !!deviceId,
  });

export const useNvmeDetail = (deviceId: number, diskName: string, type: 'id-ctrl' | 'id-ns' | 'error-log' | null) => {
  const queryFnMap: Record<string, () => Promise<import('@/types/nvme').NvmeDetailResponse>> = {
    'id-ctrl': () => nvmeApi.getIdCtrl(deviceId, diskName),
    'id-ns': () => nvmeApi.getIdNs(deviceId, diskName),
    'error-log': () => nvmeApi.getErrorLog(deviceId, diskName),
  };
  return useQuery({
    queryKey: ['nvme-detail', deviceId, diskName, type],
    queryFn: () => queryFnMap[type!](),
    enabled: !!deviceId && !!diskName && !!type && type in queryFnMap,
  });
};
