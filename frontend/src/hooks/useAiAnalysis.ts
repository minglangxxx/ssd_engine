import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { analysisApi } from '@/api/analysis';
import type { AiAnalysisRequest } from '@/types/analysis';

export const useAiAnalysis = (taskId: number) =>
  useQuery({
    queryKey: ['ai-analysis', taskId],
    queryFn: () => analysisApi.getResult(taskId),
    enabled: !!taskId,
  });

export const useTriggerAnalysis = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ taskId, params }: { taskId: number; params: AiAnalysisRequest }) =>
      analysisApi.analyze(taskId, params),
    onSuccess: (_data, variables) => {
      qc.invalidateQueries({ queryKey: ['ai-analysis', variables.taskId] });
    },
  });
};

export const useAnalysisHistory = (taskId: number) =>
  useQuery({
    queryKey: ['ai-analysis-history', taskId],
    queryFn: () => analysisApi.getHistory(taskId),
    enabled: !!taskId,
  });
