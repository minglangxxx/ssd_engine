export interface NvmeDeviceInfo {
  disk_name: string;
  controller: string;
  model: string;
  serial_number: string;
  firmware_version: string;
  capacity_bytes: number;
  capacity_formatted: string;
  pci_vendor_id: number;
  nvme_version: string;
  state: string;
}

export interface NvmeListResponse {
  device_id: number;
  device_ip: string;
  disks: NvmeDeviceInfo[];
}

export interface NvmeDetailResponse {
  device_id: number;
  disk_name: string;
  data: Record<string, unknown>;
}

export interface NvmeFeatureResponse {
  device_id: number;
  disk_name: string;
  fid: string;
  data: Record<string, unknown>;
}

export interface NvmeFwLogResponse {
  device_id: number;
  disk_name: string;
  data: {
    afi: { active: number };
    frs: string[];
  };
}

export interface NvmeTestRecord {
  id: number;
  device_id: number;
  disk_name: string;
  test_type: 'identify' | 'namespace' | 'smart' | 'error_log' | 'feature' | 'fw_slot';
  status: 'pending' | 'running' | 'done' | 'failed';
  result: NvmeCheckItem[] | null;
  verdict: 'PASS' | 'PARTIAL' | 'FAIL' | null;
  error: string | null;
  created_at: string;
  updated_at: string;
}

export interface NvmeCheckItem {
  field: string;
  value: unknown;
  check: string;
  pass: boolean;
  reason: string;
  level: 'fail' | 'warn';
}

export interface NvmeTestListResponse {
  items: NvmeTestRecord[];
  total: number;
}
