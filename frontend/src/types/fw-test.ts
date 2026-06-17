import type { FioConfig, TaskResult } from './task';
import type { RegressionResult } from './regression';

export type FwTestStatus =
  | 'pending'
  | 'collecting_baseline'
  | 'waiting_upgrade'
  | 'testing_after'
  | 'done'
  | 'failed';

export interface FwUpgradeTest {
  id: number;
  name: string;
  device_id: number;
  device_ip: string;
  device_path: string;
  fw_before: string | null;
  fw_after: string | null;
  fio_config: FioConfig;
  result_before: TaskResult | null;
  task_before_id: number | null;
  result_after: TaskResult | null;
  task_after_id: number | null;
  regression_id: number | null;
  status: FwTestStatus;
  error: string | null;
  created_at: string;
  updated_at: string;
}

export interface FwTestCreateParams {
  name: string;
  device_id: number;
  device_path: string;
  fio_config: Partial<FioConfig>;
}

export interface FwTestListParams {
  status?: FwTestStatus;
  page?: number;
  pageSize?: number;
}

export interface FwTestListResponse {
  items: FwUpgradeTest[];
  total: number;
}

export interface FwTestReport {
  task: FwUpgradeTest;
  regression: RegressionResult | null;
  generated_at: string;
}
