export interface DeviceDisk {
  name: string;
  device: string;
  mountpoint?: string;
  fstype?: string;
}

export interface Device {
  id: number;
  ip: string;
  name: string;
  agent_status: 'online' | 'offline';
  agent_version: string;
  agent_port: number;
  last_heartbeat: string;
  hostname?: string | null;
  os_version?: string | null;
  kernel_version?: string | null;
  cpu_usage?: number | null;
  memory_usage?: number | null;
  disks?: DeviceDisk[] | string[];
  created_at: string;
  updated_at: string;
}

export interface DeviceInfo extends Omit<Device, 'disks'> {
  disks: DeviceDisk[];
}

export interface DeviceAddParams {
  ip: string;
  name: string;
  agent_port?: number;
}

export interface DeviceUpdateParams {
  name?: string;
  agent_port?: number;
}
