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

const FIO_OPTION_MAP: Record<string, string> = {
  mem: 'iomem',
};

function formatFioOption(key: string, value: unknown): string | null {
  if (value === null || value === undefined || value === '') {
    return null;
  }

  if (key === 'filename' || key === 'stats_interval') {
    return null;
  }

  const fioKey = FIO_OPTION_MAP[key] || key;
  if (typeof value === 'boolean') {
    return `--${fioKey}=${value ? 1 : 0}`;
  }

  return `--${fioKey}=${value}`;
}

export function buildFioCommand(config: Partial<FioConfig>, devicePath: string, taskId: number): string {
  const rawStatusInterval = config.stats_interval;
  const statusInterval = rawStatusInterval == null ? 1 : Math.max(1, Math.ceil(Number(rawStatusInterval) / 1000));
  const command = [
    'fio',
    `--name=task_${taskId}`,
    `--filename=${devicePath}`,
    '--output-format=json',
    '--group_reporting=1',
    `--status-interval=${statusInterval}`,
  ];

  for (const [key, value] of Object.entries(config)) {
    const option = formatFioOption(key, value);
    if (option) {
      command.push(option);
    }
  }

  return command.join(' ');
}
