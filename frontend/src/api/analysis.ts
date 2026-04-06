import request from '@/utils/request';
import type { AiAnalysisRequest, AiAnalysisResult } from '@/types/analysis';

export const analysisApi = {
  analyze: (taskId: number, params: AiAnalysisRequest) =>
    request.post<unknown, AiAnalysisResult>(`/tasks/${taskId}/ai-analysis`, params),

  getResult: (taskId: number) =>
    request.get<unknown, AiAnalysisResult>(`/tasks/${taskId}/ai-analysis`),

  getHistory: (taskId: number) =>
    request.get<unknown, AiAnalysisResult[]>(`/tasks/${taskId}/ai-analysis/history`),
};
