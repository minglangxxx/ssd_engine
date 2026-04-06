export type TimeRange = '1m' | '5m' | '15m' | '1h' | '6h' | '24h' | 'all' | 'custom';

export interface HostMetricPoint {
  timestamp: string;
  cpu_usage_percent: number;
  cpu_user_percent: number;
  cpu_system_percent: number;
  cpu_iowait_percent: number;
  cpu_steal_percent: number;
  load_avg_1m: number;
  load_avg_5m: number;
  load_avg_15m: number;
  mem_total_bytes: number;
  mem_used_bytes: number;
  mem_available_bytes: number;
  mem_usage_percent: number;
  mem_buffers_bytes: number;
  mem_cached_bytes: number;
  swap_total_bytes: number;
  swap_used_bytes: number;
  net_rx_bytes_per_sec: number;
  net_tx_bytes_per_sec: number;
  net_rx_packets_per_sec: number;
  net_tx_packets_per_sec: number;
  net_rx_errors: number;
  net_tx_errors: number;
  tcp_connections: number;
  context_switches_per_sec: number;
  interrupts_per_sec: number;
  process_count: number;
}

export interface DiskMetricPoint {
  timestamp: string;
  disk_name: string;
  disk_iops_read: number;
  disk_iops_write: number;
  disk_bw_read_bytes_per_sec: number;
  disk_bw_write_bytes_per_sec: number;
  disk_latency_read_ms: number;
  disk_latency_write_ms: number;
  disk_queue_depth: number;
  disk_await_ms: number;
  disk_svctm_ms: number;
  disk_util_percent: number;
  disk_rrqm_per_sec: number;
  disk_wrqm_per_sec: number;
}

export interface HostSummary {
  cpu_usage_percent: number;
  mem_usage_percent: number;
  iowait_percent: number;
  load_avg_1m: number;
  load_avg_5m: number;
  load_avg_15m: number;
  uptime_seconds: number;
  kernel_version: string;
  process_count: number;
}

export interface DiskSummary {
  disk_name: string;
  iops_read: number;
  iops_write: number;
  bw_read: number;
  bw_write: number;
  util_percent: number;
  temperature: number;
}
