import type { FioConfig, TaskResult, TaskStatus } from './task';

export type GroupTaskStatus = 'pending' | 'running' | 'done' | 'failed' | 'partial';

export interface GroupTaskSummary {
  iops_max: number | null;
  iops_min: number | null;
  iops_avg: number | null;
  bw_max: number | null;
  bw_min: number | null;
  bw_avg: number | null;
  lat_mean_max: number | null;
  lat_mean_min: number | null;
  lat_mean_avg: number | null;
  lat_p99_max: number | null;
  lat_p99_min: number | null;
  lat_p99_avg: number | null;
}

export interface GroupTaskSubTask {
  id: number;
  name: string;
  status: TaskStatus;
  device_ip: string;
  device_path: string;
  config: Partial<FioConfig>;
  result: TaskResult | null;
  created_at: string;
}

export interface GroupTask {
  id: number;
  name: string;
  fio_config: Partial<FioConfig>;
  status: GroupTaskStatus;
  summary: GroupTaskSummary | null;
  total_count: number;
  done_count: number;
  sub_tasks?: GroupTaskSubTask[];
  created_at: string;
  updated_at: string;
}

export interface GroupTaskCreateParams {
  name: string;
  device_ids: number[];
  fio_config: Partial<FioConfig>;
  device_path?: string;
}

export interface GroupTaskListParams {
  status?: GroupTaskStatus;
  page?: number;
  pageSize?: number;
}

export interface GroupTaskListResponse {
  items: GroupTask[];
  total: number;
}
