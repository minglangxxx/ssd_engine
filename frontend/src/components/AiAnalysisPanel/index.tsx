import React, { useState } from 'react';
import { Alert, Button, Card, Checkbox, Col, Divider, Empty, InputNumber, List, Row, Space, Spin, Statistic, Tag, Typography, message } from 'antd';
import { BulbOutlined, ClockCircleOutlined, DownloadOutlined, FileTextOutlined, RadarChartOutlined, ReloadOutlined, RobotOutlined, WarningOutlined } from '@ant-design/icons';
import { useAiAnalysis, useTriggerAnalysis } from '@/hooks/useAiAnalysis';
import { usePolling } from '@/hooks/usePolling';
import type { TaskStatus } from '@/types/task';
import { formatTime } from '@/utils/format';

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

interface ReportSection {
  title: string;
  paragraphs: string[];
  bullets: string[];
  ordered: string[];
}

function parseReport(report?: string | null): ReportSection[] {
  if (!report?.trim()) return [];

  const sections: ReportSection[] = [];
  let current: ReportSection = { title: '分析概览', paragraphs: [], bullets: [], ordered: [] };

  const pushCurrent = () => {
    if (current.paragraphs.length || current.bullets.length || current.ordered.length) {
      sections.push(current);
    }
  };

  for (const rawLine of report.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line) continue;

    if (line.startsWith('## ')) {
      pushCurrent();
      current = { title: line.replace(/^##\s+/, ''), paragraphs: [], bullets: [], ordered: [] };
      continue;
    }

    if (line.startsWith('### ')) {
      current.paragraphs.push(line.replace(/^###\s+/, ''));
      continue;
    }

    if (/^[-*]\s+/.test(line)) {
      current.bullets.push(line.replace(/^[-*]\s+/, ''));
      continue;
    }

    if (/^\d+\.\s+/.test(line)) {
      current.ordered.push(line.replace(/^\d+\.\s+/, ''));
      continue;
    }

    current.paragraphs.push(line);
  }

  pushCurrent();
  return sections;
}

function getSectionAccent(title: string) {
  if (title.includes('问题') || title.includes('风险')) {
    return {
      color: '#cf1322',
      background: 'linear-gradient(135deg, rgba(255, 245, 245, 0.95), rgba(255, 232, 230, 0.92))',
      icon: <WarningOutlined />,
    };
  }
  if (title.includes('建议') || title.includes('优化')) {
    return {
      color: '#096dd9',
      background: 'linear-gradient(135deg, rgba(240, 249, 255, 0.95), rgba(230, 244, 255, 0.92))',
      icon: <BulbOutlined />,
    };
  }
  return {
    color: '#389e0d',
    background: 'linear-gradient(135deg, rgba(246, 255, 237, 0.95), rgba(237, 247, 237, 0.92))',
    icon: <FileTextOutlined />,
  };
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

  const reportSections = parseReport(analysisResult?.report);

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
        <Alert
          type="info"
          showIcon
          icon={<RobotOutlined />}
          message="AI 正在分析中"
          description="分析任务已经提交，页面会自动轮询最新结果。你可以先查看趋势图和基础指标。"
          action={<Spin size="small" />}
          style={{ marginTop: 16 }}
        />
      )}

      {analysisResult?.status === 'completed' && analysisResult.summary && (
        <>
          <Divider />
          <div
            style={{
              padding: 20,
              borderRadius: 12,
              marginBottom: 16,
              background: 'linear-gradient(135deg, #f6ffed 0%, #f0f5ff 52%, #fff7e6 100%)',
              border: '1px solid #d6e4ff',
            }}
          >
            <Row gutter={[16, 16]} align="middle">
              <Col xs={24} lg={8}>
                <Space direction="vertical" size={8}>
                  <Space align="center">
                    <RadarChartOutlined style={{ fontSize: 18, color: '#1677ff' }} />
                    <Typography.Title level={5} style={{ margin: 0 }}>
                      AI 分析结论
                    </Typography.Title>
                  </Space>
                  <Space wrap>
                    <Typography.Text type="secondary">性能评级</Typography.Text>
                    <Tag color={ratingConfig[analysisResult.summary.performance_rating]?.color}>
                      {ratingConfig[analysisResult.summary.performance_rating]?.text}
                    </Tag>
                  </Space>
                  <Space wrap size="middle">
                    <Space size={4}>
                      <ClockCircleOutlined style={{ color: '#8c8c8c' }} />
                      <Typography.Text type="secondary">
                        提交时间 {analysisResult.created_at ? formatTime(analysisResult.created_at) : '-'}
                      </Typography.Text>
                    </Space>
                    <Space size={4}>
                      <ClockCircleOutlined style={{ color: '#8c8c8c' }} />
                      <Typography.Text type="secondary">
                        完成时间 {analysisResult.completed_at ? formatTime(analysisResult.completed_at) : '-'}
                      </Typography.Text>
                    </Space>
                  </Space>
                </Space>
              </Col>
              <Col xs={24} md={8} lg={5}>
                <Statistic title="发现问题" value={analysisResult.summary.issues_found} valueStyle={{ color: '#cf1322' }} />
              </Col>
              <Col xs={24} md={8} lg={5}>
                <Statistic title="优化建议" value={analysisResult.summary.suggestions_count} valueStyle={{ color: '#0958d9' }} />
              </Col>
              <Col xs={24} md={8} lg={6}>
                <Alert
                  type="success"
                  showIcon
                  message="已生成结构化报告"
                  description="报告内容已按主题拆分，便于直接浏览和导出。"
                />
              </Col>
            </Row>
          </div>

          {reportSections.length > 0 ? (
            <Row gutter={[16, 16]}>
              {reportSections.map((section) => {
                const accent = getSectionAccent(section.title);
                return (
                  <Col xs={24} xl={12} key={section.title}>
                    <Card
                      size="small"
                      title={
                        <Space size={8} style={{ color: accent.color }}>
                          {accent.icon}
                          <span>{section.title}</span>
                        </Space>
                      }
                      style={{
                        height: '100%',
                        borderRadius: 12,
                        background: accent.background,
                        borderColor: 'rgba(5, 5, 5, 0.06)',
                      }}
                      styles={{ body: { paddingTop: 12 } }}
                    >
                      <Space direction="vertical" size={12} style={{ width: '100%' }}>
                        {section.paragraphs.map((paragraph) => (
                          <Typography.Paragraph key={paragraph} style={{ marginBottom: 0, whiteSpace: 'pre-wrap' }}>
                            {paragraph}
                          </Typography.Paragraph>
                        ))}

                        {section.bullets.length > 0 && (
                          <List
                            size="small"
                            dataSource={section.bullets}
                            renderItem={(item) => (
                              <List.Item style={{ paddingLeft: 0, paddingRight: 0 }}>
                                <Space align="start">
                                  <Tag color="red">问题</Tag>
                                  <Typography.Text>{item}</Typography.Text>
                                </Space>
                              </List.Item>
                            )}
                          />
                        )}

                        {section.ordered.length > 0 && (
                          <List
                            size="small"
                            dataSource={section.ordered}
                            renderItem={(item, index) => (
                              <List.Item style={{ paddingLeft: 0, paddingRight: 0 }}>
                                <Space align="start">
                                  <Tag color="blue">{index + 1}</Tag>
                                  <Typography.Text>{item}</Typography.Text>
                                </Space>
                              </List.Item>
                            )}
                          />
                        )}
                      </Space>
                    </Card>
                  </Col>
                );
              })}
            </Row>
          ) : (
            <Empty description="报告内容为空" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          )}

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
        <Alert
          type="error"
          showIcon
          message="分析失败"
          description={analysisResult.error || '未知错误'}
          style={{ marginTop: 16 }}
        />
      )}

      {analysisResult?.status === 'idle' && (
        <Alert
          type="warning"
          showIcon
          message="当前任务还没有分析结果"
          description="任务完成后点击“开始AI分析”，系统会结合 FIO 指标以及所选前后时间窗内的主机、磁盘监控数据生成结构化报告。"
          style={{ marginTop: 16 }}
        />
      )}
    </Card>
  );
};

export default AiAnalysisSection;
