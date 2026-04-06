export interface AiAnalysisRequest {
  include_fio: boolean;
  include_host_monitor: boolean;
  include_disk_monitor: boolean;
}

export interface AiAnalysisResult {
  id: number;
  task_id: number;
  status: 'pending' | 'analyzing' | 'completed' | 'failed';
  created_at: string;
  completed_at: string | null;
  report: string;
  summary: {
    performance_rating: 'excellent' | 'good' | 'normal' | 'poor';
    issues_found: number;
    suggestions_count: number;
  };
  error?: string;
}
