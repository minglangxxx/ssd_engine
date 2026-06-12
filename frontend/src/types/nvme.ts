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
