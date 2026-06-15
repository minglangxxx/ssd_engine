export type DataStatus = 'active' | 'archived' | 'compressed';
export type DataType = 'fio_result' | 'fio_trend' | 'host_monitor' | 'disk_monitor' | 'nvme_smart';

export interface DataRecord {
  id: number;
  task_id: number | null;
  data_type: DataType;
  device_ip: string;
  disk_name: string | null;
  status: DataStatus;
  size_bytes: number;
  record_count: number;
  created_at: string;
  archived_at: string | null;
  compressed_at: string | null;
  expires_at: string | null;
}

export interface DataOverview {
  active_count: number;
  active_size_bytes: number;
  archived_count: number;
  archived_size_bytes: number;
  compressed_count: number;
  compressed_size_bytes: number;
  expiring_soon_count: number;
}

export interface DataListParams {
  data_type?: DataType;
  status?: DataStatus;
  device_ip?: string;
  start_date?: string;
  end_date?: string;
  page?: number;
  pageSize?: number;
}

export interface DataListResponse {
  items: DataRecord[];
  total: number;
}
