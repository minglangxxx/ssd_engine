import { useQuery } from '@tanstack/react-query';
import { smartApi } from '@/api';
import type { TimeRange } from '@/types/monitor';
import dayjs from 'dayjs';
import { formatApiDateTime } from '@/utils/format';

function getTimeParams(timeRange: TimeRange) {
  if (timeRange === 'all') return {};
  if (timeRange === 'custom') return {};
  const unitMap: Record<string, [number, dayjs.ManipulateType]> = {
    '1m': [1, 'minute'],
    '5m': [5, 'minute'],
    '15m': [15, 'minute'],
    '1h': [1, 'hour'],
    '6h': [6, 'hour'],
    '24h': [24, 'hour'],
  };
  const entry = unitMap[timeRange];
  if (entry) {
    return {
      start: formatApiDateTime(dayjs().subtract(entry[0], entry[1])),
      end: formatApiDateTime(dayjs()),
    };
  }
  return {};
}

export const useSmartLatest = (deviceId: number) =>
  useQuery({
    queryKey: ['smart-latest', deviceId],
    queryFn: () => smartApi.getLatest(deviceId),
    enabled: !!deviceId,
  });

export const useSmartHistory = (deviceId: number, diskName: string, timeRange: TimeRange) =>
  useQuery({
    queryKey: ['smart-history', deviceId, diskName, timeRange],
    queryFn: () => smartApi.getHistory(deviceId, diskName, getTimeParams(timeRange)),
    enabled: !!deviceId && !!diskName,
  });

export const useHealthScore = (deviceId: number) =>
  useQuery({
    queryKey: ['smart-health', deviceId],
    queryFn: () => smartApi.getHealthScore(deviceId),
    enabled: !!deviceId,
  });

export const useSmartAlerts = (deviceId: number) =>
  useQuery({
    queryKey: ['smart-alerts', deviceId],
    queryFn: () => smartApi.getAlerts(deviceId),
    enabled: !!deviceId,
  });