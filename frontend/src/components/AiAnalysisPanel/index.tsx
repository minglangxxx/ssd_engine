import React, { useState } from 'react';
import { Card, Button, Checkbox, Space, Spin, Divider, Tag, message, InputNumber, Typography } from 'antd';
import { RobotOutlined, DownloadOutlined, ReloadOutlined } from '@ant-design/icons';
import ReactMarkdown from 'react-markdown';
import { useAiAnalysis, useTriggerAnalysis } from '@/hooks/useAiAnalysis';
import { usePolling } from '@/hooks/usePolling';
import type { TaskStatus } from '@/types/task';

const ratingConfig: Record<string, { color: string; text: string }> = {
  excellent: { color: 'green', text: '优秀' },
  good: { color: 'blue', text: '良好' },
  normal: { color: 'orange', text: '一般' },
  poor: { color: 'red', text: '较差' },
};

interface AiAnalysisSectionProps {
  taskId: number;
  status: TaskStatus;
}

const AiAnalysisSection: React.FC<AiAnalysisSectionProps> = ({ taskId, status }) => {
  const [scope, setScope] = useState({
    include_fio: true,
    include_host_monitor: true,
    include_disk_monitor: true,
    window_before_seconds: 30,
    window_after_seconds: 30,
  });

  const { data: analysisResult, refetch } = useAiAnalysis(taskId);
  const { mutate: triggerAnalysis, isPending: analyzing } = useTriggerAnalysis();

  usePolling({
    fn: () => refetch(),
    enabled: analysisResult?.status === 'analyzing',
    interval: 3000,
  });

  const handleAnalyze = () => {
    triggerAnalysis(
      { taskId, params: scope },
      {
        onSuccess: () => {
          message.success('分析已提交');
          refetch();
        },
      }
    );
  };

  const handleExport = () => {
    if (!analysisResult?.report) return;
    const blob = new Blob([analysisResult.report], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `ai-analysis-task-${taskId}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const scopeOptions = [
    { label: 'FIO结果', value: 'include_fio' },
    { label: '主机监控', value: 'include_host_monitor' },
    { label: '磁盘监控', value: 'include_disk_monitor' },
  ];

  return (
    <Card title="AI 智能分析" size="small" style={{ marginBottom: 16 }}>
      <Space wrap>
        <Button
          type="primary"
          icon={<RobotOutlined />}
          loading={analyzing}
          onClick={handleAnalyze}
          disabled={status === 'RUNNING'}
        >
          开始AI分析
        </Button>
        <Checkbox.Group
          value={Object.entries(scope)
            .filter(([key, value]) => key.startsWith('include_') && value)
            .map(([k]) => k)}
          onChange={(vals) => {
            setScope((prev) => ({
              ...prev,
              include_fio: vals.includes('include_fio'),
              include_host_monitor: vals.includes('include_host_monitor'),
              include_disk_monitor: vals.includes('include_disk_monitor'),
            }));
          }}
          options={scopeOptions}
        />
      </Space>

      <Space wrap style={{ marginTop: 12 }}>
        <Typography.Text type="secondary">分析窗口</Typography.Text>
        <Space size={4}>
          <Typography.Text>前置</Typography.Text>
          <InputNumber
            min={0}
            max={3600}
            value={scope.window_before_seconds}
            onChange={(value) => {
              setScope((prev) => ({
                ...prev,
                window_before_seconds: typeof value === 'number' ? value : 0,
              }));
            }}
          />
          <Typography.Text type="secondary">秒</Typography.Text>
        </Space>
        <Space size={4}>
          <Typography.Text>后置</Typography.Text>
          <InputNumber
            min={0}
            max={3600}
            value={scope.window_after_seconds}
            onChange={(value) => {
              setScope((prev) => ({
                ...prev,
                window_after_seconds: typeof value === 'number' ? value : 0,
              }));
            }}
          />
          <Typography.Text type="secondary">秒</Typography.Text>
        </Space>
      </Space>

      {analysisResult?.status === 'analyzing' && (
        <div style={{ textAlign: 'center', padding: 40 }}>
          <Spin tip="AI正在分析中..." />
        </div>
      )}

      {analysisResult?.status === 'completed' && (
        <>
          <Divider />
          <Space style={{ marginBottom: 12 }}>
            <span>性能评级:</span>
            <Tag color={ratingConfig[analysisResult.summary.performance_rating]?.color}>
              {ratingConfig[analysisResult.summary.performance_rating]?.text}
            </Tag>
            <span>发现问题: {analysisResult.summary.issues_found}</span>
            <span>优化建议: {analysisResult.summary.suggestions_count}</span>
          </Space>
          <div style={{ padding: 16, background: '#fafafa', borderRadius: 6 }}>
            <ReactMarkdown>{analysisResult.report}</ReactMarkdown>
          </div>
          <Space style={{ marginTop: 16 }}>
            <Button icon={<DownloadOutlined />} onClick={handleExport}>
              导出分析报告
            </Button>
            <Button icon={<ReloadOutlined />} onClick={handleAnalyze}>
              重新分析
            </Button>
          </Space>
        </>
      )}

      {analysisResult?.status === 'failed' && (
        <div style={{ padding: 16, color: '#ff4d4f' }}>
          分析失败: {analysisResult.error || '未知错误'}
        </div>
      )}

      {analysisResult?.status === 'idle' && (
        <div style={{ padding: 16, color: '#8c8c8c' }}>
          当前任务还没有分析结果。任务完成后点击“开始AI分析”，系统会结合 FIO 指标以及所选前后时间窗内的主机、磁盘监控数据生成报告。
        </div>
      )}
    </Card>
  );
};

export default AiAnalysisSection;
