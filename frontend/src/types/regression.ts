export type RegressionVerdict = 'PASS' | 'WARNING' | 'FAIL';

export interface RegressionMetric {
  name: string;
  display_name: string;
  baseline: number;
  current: number;
  diff_pct: number;
  verdict: RegressionVerdict;
  unit: string;
}

export interface RegressionResult {
  id: number;
  task_id: number;
  baseline_id: number;
  iops_diff: number | null;
  bw_diff: number | null;
  lat_mean_diff: number | null;
  lat_p99_diff: number | null;
  verdict: RegressionVerdict;
  detail: { metrics: RegressionMetric[] };
  created_at: string;
}

export interface RegressionListParams {
  verdict?: RegressionVerdict;
  page?: number;
  pageSize?: number;
}

export interface RegressionListResponse {
  items: RegressionResult[];
  total: number;
}
