import { useQuery } from '@tanstack/react-query';
import { monitorApi } from '@/api/monitor';
import type { TimeRange } from '@/types/monitor';
import dayjs from 'dayjs';

function buildTimeParams(timeRange: TimeRange) {
  if (timeRange === 'all') return undefined;
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
      start: dayjs().subtract(entry[0], entry[1]).toISOString(),
      end: dayjs().toISOString(),
    };
  }
  return undefined;
}

export const useHostMonitor = (host: string, timeRange: TimeRange) =>
  useQuery({
    queryKey: ['host-monitor', host, timeRange],
    queryFn: () => monitorApi.getHostMetrics(host, buildTimeParams(timeRange)),
    enabled: !!host,
  });

export const useDiskMonitor = (host: string, disks: string[], timeRange: TimeRange) =>
  useQuery({
    queryKey: ['disk-monitor', host, disks, timeRange],
    queryFn: () =>
      Promise.all(
        disks.map((d) =>
          monitorApi.getDiskMetrics(host, d, buildTimeParams(timeRange))
        )
      ),
    enabled: !!host && disks.length > 0,
  });

export const useDiskList = (host: string) =>
  useQuery({
    queryKey: ['disk-list', host],
    queryFn: () => monitorApi.getDiskList(host),
    enabled: !!host,
  });

export const useHostSummary = (host: string) =>
  useQuery({
    queryKey: ['host-summary', host],
    queryFn: () => monitorApi.getHostSummary(host),
    enabled: !!host,
  });
