export interface AiAnalysisRequest {
  include_fio: boolean;
  include_host_monitor: boolean;
  include_disk_monitor: boolean;
  window_before_seconds: number;
  window_after_seconds: number;
}

export interface AiAnalysisResult {
  id: number | null;
  task_id: number;
  status: 'idle' | 'pending' | 'analyzing' | 'completed' | 'failed';
  created_at: string | null;
  completed_at: string | null;
  report: string;
  summary: {
    performance_rating: 'excellent' | 'good' | 'normal' | 'poor';
    issues_found: number;
    suggestions_count: number;
  };
  error?: string | null;
}
