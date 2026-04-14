export type TaskStatus = 'PENDING' | 'RUNNING' | 'SUCCESS' | 'FAILED';

export interface Task {
  id: number;
  name: string;
  status: TaskStatus;
  device_ip: string;
  device_path: string;
  config: FioConfig;
  fault_type?: string;
  result: TaskResult | null;
  created_at: string;
  updated_at: string;
}

export interface FioConfig {
  rw: 'read' | 'write' | 'rw' | 'randread' | 'randwrite' | 'randrw';
  bs?: string | null;
  size?: string | null;
  numjobs?: number | null;
  iodepth?: number | null;
  runtime?: number | null;
  time_based?: boolean | null;
  ioengine?: string | null;
  direct?: boolean | null;
  sync?: boolean | null;
  fsync?: number | null;
  buffer_pattern?: string | null;
  random_distribution?: string | null;
  randseed?: number | null;
  rwmixread?: number | null;
  rwmixwrite?: number | null;
  thinktime?: number | null;
  latency_target?: number | null;
  rate?: number | null;
  rate_iops?: number | null;
  verify?: string | null;
  verify_fatal?: boolean | null;
  cpus_allowed?: string | null;
  mem?: string | null;
  stats_interval?: number | null;
  log_avg_msec?: number | null;
  loops?: number | null;
  startdelay?: number | null;
  [key: string]: unknown;
}

export interface TaskResult {
  iops: number;
  bandwidth: number;
  latency: { mean: number; min: number; max: number };
  read_iops?: number;
  write_iops?: number;
  read_bw?: number;
  write_bw?: number;
  smart?: SmartInfo;
  error?: string;
}

export interface SmartInfo {
  temperature: number;
  percentage_used: number;
  power_on_hours: number;
  power_cycles: number;
  media_errors: number;
  critical_warning: number;
  data_units_read: number;
  data_units_written: number;
}

export interface FioTrendPoint {
  timestamp: string;
  iops_read: number;
  iops_write: number;
  iops_total: number;
  bw_read: number;
  bw_write: number;
  bw_total: number;
  lat_mean: number;
  lat_p99: number;
  lat_max: number;
}

export interface TaskCreateParams {
  name?: string;
  device_ip: string;
  device_path: string;
  config: Partial<FioConfig>;
  fio_command?: string;
  fault_type?: 'none' | 'power_off' | 'drop_device';
}

export interface TaskListParams {
  status?: TaskStatus | 'all';
  keyword?: string;
  page?: number;
  pageSize?: number;
}

export interface TaskListResponse {
  items: Task[];
  total: number;
}

export interface TaskStatusResponse {
  id: number;
  status: TaskStatus;
  error?: string | null;
  result: TaskResult | null;
  updated_at: string | null;
}

export function buildFioConfig(config: Partial<FioConfig>): Record<string, unknown> {
  const result: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(config)) {
    if (value !== null && value !== undefined && value !== '') {
      result[key] = value;
    }
  }
  return result;
}
