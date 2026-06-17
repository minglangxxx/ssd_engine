import type { FioConfig, TaskResult } from './task';

export interface Baseline {
  id: number;
  name: string;
  device_model: string | null;
  firmware: string | null;
  fio_config: FioConfig;
  result: TaskResult;
  source_task_id: number;
  device_ip: string;
  device_path: string;
  created_at: string;
  created_by: string;
}

export interface BaselineCreateParams {
  task_id: number;
  name: string;
  device_model?: string;
  firmware?: string;
}

export interface BaselineListParams {
  keyword?: string;
  device_model?: string;
  page?: number;
  pageSize?: number;
}

export interface BaselineListResponse {
  items: Baseline[];
  total: number;
}
