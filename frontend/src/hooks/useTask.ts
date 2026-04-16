import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { taskApi } from '@/api/task';
import type { TaskListParams, TaskCreateParams } from '@/types/task';
import type { TimeRange } from '@/types/monitor';
import dayjs from 'dayjs';
import { formatApiDateTime } from '@/utils/format';

export const useTaskList = (params?: TaskListParams) =>
  useQuery({
    queryKey: ['tasks', params],
    queryFn: () => taskApi.list(params),
  });

export const useTaskDetail = (id: number) =>
  useQuery({
    queryKey: ['task', id],
    queryFn: () => taskApi.get(id),
    enabled: !!id,
  });

export const useCreateTask = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: TaskCreateParams) => taskApi.create(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tasks'] }),
  });
};

export const useDeleteTask = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => taskApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tasks'] }),
  });
};

function buildTrendParams(opts?: { timeRange?: TimeRange; customRange?: [dayjs.Dayjs, dayjs.Dayjs] | null }) {
  if (!opts) return undefined;
  const { timeRange, customRange } = opts;
  if (timeRange === 'custom' && customRange) {
    return {
      start: formatApiDateTime(customRange[0]),
      end: formatApiDateTime(customRange[1]),
    };
  }
  if (timeRange && timeRange !== 'all') {
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
  }
  return undefined;
}

export const useFioTrend = (taskId: number, opts?: { timeRange: TimeRange; customRange?: [dayjs.Dayjs, dayjs.Dayjs] | null }) =>
  useQuery({
    queryKey: ['task-trend', taskId, opts?.timeRange, opts?.customRange?.map((d) => d.valueOf())],
    queryFn: () => taskApi.getTrend(taskId, buildTrendParams(opts)),
    enabled: !!taskId,
  });
