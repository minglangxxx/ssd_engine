import React, { useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, Descriptions, Steps, Button, Space, Tag, Alert, Row, Col, Statistic } from 'antd';
import { ArrowLeftOutlined, DownloadOutlined } from '@ant-design/icons';
import { useSniaTaskDetail } from '@/hooks/useSniaTask';
import { formatTime, formatNumber } from '@/utils/format';
import type { SniaStatus } from '@/types/snia';

const STATUS_MAP: Record<SniaStatus, { color: string; text: string }> = {
  pending: { color: 'default', text: '等待中' },
  preconditioning: { color: 'processing', text: '预处理' },
  iops_test: { color: 'processing', text: 'IOPS 扫描' },
  steady_state: { color: 'processing', text: '稳态判定' },
  done: { color: 'success', text: '已完成' },
  failed: { color: 'error', text: '失败' },
  aborted: { color: 'warning', text: '已终止' },
};

const STEPS_ITEMS = [
  { title: '预处理', description: '顺序写 128k' },
  { title: 'IOPS 扫描', description: 'bs × pattern 组合' },
  { title: '稳态判定', description: '多轮 FIO + 收敛检测' },
];

function getStepIndex(phase: string | null): number {
  if (!phase) return -1;
  if (phase === 'precondition') return 0;
  if (phase === 'iops_test') return 1;
  if (phase === 'steady_state') return 2;
  return -1;
}

const SniaTaskDetail: React.FC = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const taskId = Number(id);
  const { data: task, isLoading } = useSniaTaskDetail(taskId);

  if (isLoading || !task) {
    return <Card loading={isLoading}>加载中...</Card>;
  }

  const currentStep = getStepIndex(task.current_phase);
  const result = task.result as {
    iops_test_results?: { bs: string; pattern: string; iops: number; bw: number }[];
    steady_state_achieved?: boolean;
    steady_state_round?: number;
    iops_history?: number[];
  } | null;

  const iopsTestResults = result?.iops_test_results || [];
  const iopsHistory = task.iops_history || [];

  const steadyConfig = task.config?.steady_state;
  const window = steadyConfig?.window || 5;
  const threshold = steadyConfig?.threshold || 0.10;

  const steadyWindowEnd = task.is_steady ? task.current_round - 1 : null;
  const steadyWindowStart = steadyWindowEnd != null ? Math.max(0, steadyWindowEnd - window + 1) : null;

  const iopsTestMatrix = useMemo(() => {
    const bss = [...new Set(iopsTestResults.map((r) => r.bs))];
    const patterns = [...new Set(iopsTestResults.map((r) => r.pattern))];
    const map: Record<string, Record<string, { iops: number; bw: number }>> = {};
    for (const r of iopsTestResults) {
      if (!map[r.bs]) map[r.bs] = {};
      map[r.bs][r.pattern] = { iops: r.iops, bw: r.bw };
    }
    return { bss, patterns, map };
  }, [iopsTestResults]);

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/snia-tasks')}>
            返回列表
          </Button>
          <h2 style={{ margin: 0 }}>SNIA 测试详情 - {task.name}</h2>
        </Space>
        <Space>
          <Tag color={STATUS_MAP[task.status]?.color}>
            {STATUS_MAP[task.status]?.text || task.status}
          </Tag>
          {task.status === 'done' && (
            <Button
              icon={<DownloadOutlined />}
              size="small"
              onClick={() => {
                import('@/utils/download').then(({ downloadJson }) => {
                  downloadJson(task, `snia-report-${task.id}.json`);
                });
              }}
            >
              导出报告
            </Button>
          )}
        </Space>
      </div>

      <Card title="阶段进度" size="small" style={{ marginBottom: 16 }}>
        <Steps
          current={currentStep}
          items={STEPS_ITEMS}
          status={task.status === 'failed' ? 'error' : task.status === 'aborted' ? 'error' : undefined}
        />
        {task.current_phase === 'steady_state' && (
          <Alert
            type="info"
            showIcon
            message={`稳态轮次 ${task.current_round}/${task.total_rounds}`}
            style={{ marginTop: 12 }}
          />
        )}
        {task.error && (
          <Alert type="error" showIcon message={task.error} style={{ marginTop: 12 }} />
        )}
        {task.status === 'aborted' && (
          <Alert type="warning" showIcon message="测试已被用户终止" style={{ marginTop: 12 }} />
        )}
      </Card>

      <Card title="基本信息" size="small" style={{ marginBottom: 16 }}>
        <Descriptions column={3} size="small">
          <Descriptions.Item label="任务ID">{task.id}</Descriptions.Item>
          <Descriptions.Item label="设备IP">{task.device_ip}</Descriptions.Item>
          <Descriptions.Item label="设备路径">{task.device_path}</Descriptions.Item>
          <Descriptions.Item label="稳态达成">
            {task.is_steady ? <Tag color="green">是</Tag> : <Tag>否</Tag>}
          </Descriptions.Item>
          <Descriptions.Item label="创建时间">{formatTime(task.created_at)}</Descriptions.Item>
          <Descriptions.Item label="更新时间">{formatTime(task.updated_at)}</Descriptions.Item>
        </Descriptions>
      </Card>

      {iopsTestResults.length > 0 && (
        <Card title="IOPS 测试结果矩阵" size="small" style={{ marginBottom: 16 }}>
          <Row gutter={[8, 8]}>
            <Col span={24}>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ borderCollapse: 'collapse', width: '100%', fontSize: 13 }}>
                  <thead>
                    <tr>
                      <th style={{ padding: 6, border: '1px solid #f0f0f0', textAlign: 'left' }}>块大小</th>
                      {iopsTestMatrix.patterns.map((p) => (
                        <th key={p} style={{ padding: 6, border: '1px solid #f0f0f0' }}>{p}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {iopsTestMatrix.bss.map((bs) => (
                      <tr key={bs}>
                        <td style={{ padding: 6, border: '1px solid #f0f0f0', fontWeight: 600 }}>{bs}</td>
                        {iopsTestMatrix.patterns.map((p) => {
                          const cell = iopsTestMatrix.map[bs]?.[p];
                          return (
                            <td key={p} style={{ padding: 6, border: '1px solid #f0f0f0', textAlign: 'center' }}>
                              {cell ? (
                                <div>
                                  <div>{formatNumber(cell.iops)} IOPS</div>
                                  <div style={{ color: '#999' }}>{cell.bw.toFixed(1)} MB/s</div>
                                </div>
                              ) : '-'}
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Col>
          </Row>
        </Card>
      )}

      {iopsHistory.length > 0 && (
        <Card title="稳态收敛 IOPS 历史" size="small" style={{ marginBottom: 16 }}>
          <Row gutter={16}>
            <Col span={6}>
              <Statistic title="最终 IOPS" value={iopsHistory[iopsHistory.length - 1]} formatter={(v) => formatNumber(v as number)} />
            </Col>
            <Col span={6}>
              <Statistic title="IOPS 均值" value={iopsHistory.reduce((a, b) => a + b, 0) / iopsHistory.length} precision={0} />
            </Col>
            <Col span={6}>
              <Statistic title="达成轮次" value={result?.steady_state_round || '-'} />
            </Col>
            <Col span={6}>
              <Statistic title="窗口/阈值" value={`${window}轮 / ${(threshold * 100).toFixed(0)}%`} />
            </Col>
          </Row>
          <div style={{ marginTop: 16, overflowX: 'auto' }}>
            <div style={{ display: 'flex', alignItems: 'flex-end', height: 200, gap: 4 }}>
              {(() => {
                const maxV = iopsHistory.length > 0 ? Math.max(...iopsHistory) : 0;
                return iopsHistory.map((v, i) => {
                  const h = maxV > 0 ? (v / maxV) * 180 : 0;
                  const inWindow = steadyWindowStart != null && i >= steadyWindowStart && i <= (steadyWindowEnd || 0);
                  return (
                    <div key={i} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: 32 }}>
                      <div
                        style={{
                          width: 24,
                          height: h,
                          backgroundColor: inWindow ? '#52c41a' : '#1890ff',
                          borderRadius: 2,
                          transition: 'height 0.3s',
                        }}
                      />
                      <span style={{ fontSize: 10, color: '#999', marginTop: 2 }}>{i + 1}</span>
                    </div>
                  );
                });
              })()}
            </div>
          </div>
        </Card>
      )}
    </div>
  );
};

export default SniaTaskDetail;
