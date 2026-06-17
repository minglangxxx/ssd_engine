export type SniaStatus =
  | 'pending'
  | 'preconditioning'
  | 'iops_test'
  | 'steady_state'
  | 'done'
  | 'failed'
  | 'aborted';

export interface SniaConfig {
  precondition: { rw: string; bs: string; iodepth: number; loops: number };
  iops_test: {
    block_sizes: string[];
    patterns: string[];
    iodepth: number;
    runtime: number;
  };
  steady_state: {
    rw: string;
    bs: string;
    iodepth: number;
    rounds: number;
    runtime: number;
    window: number;
    threshold: number;
  };
}

export interface SniaTask {
  id: number;
  name: string;
  device_id: number;
  device_ip: string;
  device_path: string;
  status: SniaStatus;
  current_phase: string | null;
  current_round: number;
  total_rounds: number;
  iops_history: number[];
  is_steady: boolean;
  config: SniaConfig;
  result: Record<string, unknown> | null;
  error: string | null;
  created_at: string;
  updated_at: string;
}

export interface SniaTaskCreateParams {
  name: string;
  device_id: number;
  device_path: string;
  config?: Partial<SniaConfig>;
}

export interface SniaTaskListParams {
  status?: SniaStatus;
  page?: number;
  pageSize?: number;
}

export interface SniaTaskListResponse {
  items: SniaTask[];
  total: number;
}

export interface SniaReport {
  task: SniaTask;
  generated_at: string;
}
