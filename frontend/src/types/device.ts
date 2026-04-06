export interface Device {
  id: number;
  ip: string;
  name: string;
  agent_status: 'online' | 'offline';
  agent_version: string;
  agent_port: number;
  last_heartbeat: string;
  disks: string[];
  created_at: string;
  updated_at: string;
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
