/** 单条 SMART 采样数据（与后端 NvmeSmartData.to_dict() 对应） */
export interface SmartData {
  disk_name: string;
  event_time: string;
  temperature: number;
  percentage_used: number;
  power_on_hours: number;
  power_cycles: number;
  media_errors: number;
  critical_warning: number;
  data_units_read: number;
  data_units_written: number;
  available_spare?: number | null;
}

/** 单个磁盘的 SMART 快照（含评分和告警） */
export interface SmartDiskSnapshot extends SmartData {
  health_score: number;
  health_level: 'good' | 'warning' | 'critical' | 'failed';
  health_details: {
    temperature_score: number;
    wear_score: number;
    media_errors_score: number;
    critical_warning_score: number;
    spare_score: number;
  };
  alerts: SmartAlert[];
}

/** GET /devices/:id/smart/latest 响应 */
export interface SmartLatestResponse {
  device_id: number;
  device_ip: string;
  disks: SmartDiskSnapshot[];
}

/** GET /devices/:id/smart/history 响应 */
export interface SmartHistoryResponse {
  device_id: number;
  disk_name: string;
  points: SmartData[];
}

/** GET /devices/:id/smart/health-score 响应 */
export interface HealthScoreResponse {
  device_id: number;
  disks: HealthScoreDetail[];
}

/** 单盘健康评分详情 */
export interface HealthScoreDetail {
  disk_name: string;
  score: number;
  level: 'good' | 'warning' | 'critical' | 'failed';
  details: {
    temperature_score: number;
    wear_score: number;
    media_errors_score: number;
    critical_warning_score: number;
    spare_score: number;
  };
}

/** 单条告警 */
export interface SmartAlert {
  disk_name: string;
  severity: 'warning' | 'critical';
  field: string;
  message: string;
  value: number;
  threshold: number;
  detected_at: string;
}

/** GET /devices/:id/smart/alerts 响应 */
export interface SmartAlertsResponse {
  device_id: number;
  alerts: SmartAlert[];
}