import React, { useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Card, Descriptions, Steps, Button, Space, Tag, Alert, Row, Col, Statistic, Table, Spin, Popconfirm,
} from 'antd';
import { ArrowLeftOutlined, CheckCircleOutlined, DownloadOutlined } from '@ant-design/icons';
import { useFwTestDetail, useConfirmFwUpgrade, useAbortFwTest, useFwTestReport } from '@/hooks/useFwTest';
import { useRegressionDetail } from '@/hooks/useRegression';
import { formatTime, formatNumber } from '@/utils/format';
import type { FwUpgradeTest, FwTestStatus } from '@/types/fw-test';
import type { RegressionMetric, RegressionVerdict } from '@/types/regression';

const STATUS_MAP: Record<FwTestStatus, { color: string; text: string }> = {
  pending: { color: 'default', text: '等待中' },
  collecting_baseline: { color: 'processing', text: '采集基线' },
  waiting_upgrade: { color: 'warning', text: '等待升级' },
  testing_after: { color: 'processing', text: '升级后测试' },
  done: { color: 'success', text: '已完成' },
  failed: { color: 'error', text: '失败' },
};

const verdictColor: Record<RegressionVerdict, string> = {
  PASS: 'green',
  WARNING: 'orange',
  FAIL: 'red',
};

function getCurrentStep(status: FwTestStatus, fwTest: FwUpgradeTest): number {
  if (status === 'pending' || status === 'collecting_baseline') return 0;
  if (status === 'waiting_upgrade') return 1;
  if (status === 'testing_after' || status === 'done') return 2;
  if (status === 'failed') {
    if (!fwTest.result_before) return 0;
    if (!fwTest.fw_after) return 1;
    return 2;
  }
  return 0;
}

function getStepsStatus(status: FwTestStatus): 'process' | 'wait' | 'error' | 'finish' {
  if (status === 'failed') return 'error';
  if (status === 'done') return 'finish';
  return 'process';
}

const FwTestDetail: React.FC = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const fwTestId = Number(id);

  const { data: fwTest, isLoading } = useFwTestDetail(fwTestId);
  const { mutate: confirmUpgrade, isPending: confirming } = useConfirmFwUpgrade();
  const { mutate: abortTest } = useAbortFwTest();
  const { data: report } = useFwTestReport(fwTestId, fwTest?.status);

  const regressionId = fwTest?.regression_id ?? report?.regression?.id ?? undefined;
  const { data: regression } = useRegressionDetail(regressionId!);

  if (isLoading || !fwTest) {
    return <Card loading><Spin /></Card>;
  }

  const currentStep = getCurrentStep(fwTest.status, fwTest);
  const stepsStatus = getStepsStatus(fwTest.status);
  const metrics = regression?.detail?.metrics || [];

  const comparisonColumns = [
    {
      title: '指标',
      dataIndex: 'display_name',
      width: 120,
    },
    {
      title: '升级前(基线)',
      dataIndex: 'baseline',
      width: 130,
      render: (v: number, r: RegressionMetric) => `${formatNumber(v)} ${r.unit}`,
    },
    {
      title: '升级后',
      dataIndex: 'current',
      width: 130,
      render: (v: number, r: RegressionMetric) => `${formatNumber(v)} ${r.unit}`,
    },
    {
      title: '差异',
      dataIndex: 'diff_pct',
      width: 120,
      render: (v: number, r: RegressionMetric) => {
        const isLatency = r.name.startsWith('lat');
        const isDegradation = isLatency ? v > 0 : v < 0;
        const isImprovement = isLatency ? v < 0 : v > 0;
        const color = isDegradation ? '#f5222d' : isImprovement ? '#52c41a' : '#000';
        return (
          <Space>
            <span style={{ color }}>
              {v > 0 ? '+' : ''}{v}%
            </span>
            <Tag color={verdictColor[r.verdict]}>{r.verdict}</Tag>
          </Space>
        );
      },
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/fw-tests')}>
            返回列表
          </Button>
          <h2 style={{ margin: 0 }}>固件升级测试 - {fwTest.name}</h2>
        </Space>
        <Space>
          <Tag color={STATUS_MAP[fwTest.status]?.color}>
            {STATUS_MAP[fwTest.status]?.text || fwTest.status}
          </Tag>
          {fwTest.status === 'done' && (
            <Button
              icon={<DownloadOutlined />}
              size="small"
              onClick={() => {
                import('@/utils/download').then(({ downloadJson }) => {
                  downloadJson(report || fwTest, `fw-report-${fwTest.id}.json`);
                });
              }}
            >
              导出报告
            </Button>
          )}
        </Space>
      </div>

      {/* Three-step wizard */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Steps
          current={currentStep}
          status={stepsStatus}
          items={[
            {
              title: '采集基线',
              description: fwTest.status === 'collecting_baseline'
                ? '正在运行基线 FIO...'
                : fwTest.result_before
                  ? '基线采集完成'
                  : '等待启动',
            },
            {
              title: '固件升级',
              description: fwTest.status === 'waiting_upgrade'
                ? '请在目标设备上完成固件升级'
                : fwTest.fw_after
                  ? '升级已完成'
                  : '等待基线完成',
            },
            {
              title: '查看报告',
              description: fwTest.status === 'testing_after'
                ? '正在运行升级后 FIO...'
                : fwTest.status === 'done'
                  ? '报告已生成'
                  : '等待升级确认',
            },
          ]}
        />
        {fwTest.error && (
          <Alert type="error" showIcon message={fwTest.error} style={{ marginTop: 12 }} />
        )}
      </Card>

      {/* Basic info */}
      <Card title="基本信息" size="small" style={{ marginBottom: 16 }}>
        <Descriptions column={3} size="small">
          <Descriptions.Item label="任务ID">{fwTest.id}</Descriptions.Item>
          <Descriptions.Item label="设备IP">{fwTest.device_ip}</Descriptions.Item>
          <Descriptions.Item label="设备路径">{fwTest.device_path}</Descriptions.Item>
          <Descriptions.Item label="升级前FW">{fwTest.fw_before || '-'}</Descriptions.Item>
          <Descriptions.Item label="升级后FW">{fwTest.fw_after || '-'}</Descriptions.Item>
          <Descriptions.Item label="创建时间">{formatTime(fwTest.created_at)}</Descriptions.Item>
        </Descriptions>
      </Card>

      {/* Step 1: Baseline results */}
      {fwTest.result_before && (
        <Card title="升级前基线结果" size="small" style={{ marginBottom: 16 }}>
          <Row gutter={16}>
            <Col span={6}>
              <Statistic title="IOPS" value={fwTest.result_before.iops} formatter={(v) => formatNumber(v as number)} />
            </Col>
            <Col span={6}>
              <Statistic title="带宽(MB/s)" value={fwTest.result_before.bandwidth} precision={1} />
            </Col>
            <Col span={6}>
              <Statistic title="平均延迟(us)" value={fwTest.result_before.latency.mean} precision={1} />
            </Col>
            <Col span={6}>
              <Statistic title="P99延迟(us)" value={fwTest.result_before.latency.p99 || '-'} />
            </Col>
          </Row>
        </Card>
      )}

      {/* Step 2: Confirm upgrade */}
      {fwTest.status === 'waiting_upgrade' && (
        <Card title="确认固件升级" size="small" style={{ marginBottom: 16 }}>
          <Alert
            type="warning"
            showIcon
            message="请在目标设备上完成固件升级"
            description={`当前固件版本: ${fwTest.fw_before || '未知'}。升级完成后请点击下方按钮确认。`}
            style={{ marginBottom: 12 }}
          />
          <Button
            type="primary"
            icon={<CheckCircleOutlined />}
            loading={confirming}
            onClick={() => confirmUpgrade(fwTestId)}
          >
            确认升级已完成
          </Button>
        </Card>
      )}

      {/* Step 3: Comparison report */}
      {fwTest.status === 'done' && metrics.length > 0 && (
        <Card title="升级前后对比报告" size="small" style={{ marginBottom: 16 }}>
          <Table
            columns={comparisonColumns}
            dataSource={metrics}
            rowKey="name"
            pagination={false}
            size="small"
          />
          {regression && (
            <div style={{ marginTop: 12 }}>
              <Space>
                <span>总体判定:</span>
                <Tag
                  color={verdictColor[regression.verdict]}
                  style={{ fontSize: 14, padding: '4px 12px' }}
                >
                  {regression.verdict}
                </Tag>
                <Button type="link" size="small" onClick={() => navigate(`/regressions/${regression.id}`)}>
                  查看回归详情
                </Button>
              </Space>
            </div>
          )}
        </Card>
      )}

      {/* Step 3: After-test results */}
      {fwTest.result_after && (
        <Card title="升级后测试结果" size="small" style={{ marginBottom: 16 }}>
          <Row gutter={16}>
            <Col span={6}>
              <Statistic title="IOPS" value={fwTest.result_after.iops} formatter={(v) => formatNumber(v as number)} />
            </Col>
            <Col span={6}>
              <Statistic title="带宽(MB/s)" value={fwTest.result_after.bandwidth} precision={1} />
            </Col>
            <Col span={6}>
              <Statistic title="平均延迟(us)" value={fwTest.result_after.latency.mean} precision={1} />
            </Col>
            <Col span={6}>
              <Statistic title="P99延迟(us)" value={fwTest.result_after.latency.p99 || '-'} />
            </Col>
          </Row>
        </Card>
      )}

      {/* Abort button for non-terminal states */}
      {fwTest.status !== 'done' && fwTest.status !== 'failed' && (
        <div style={{ textAlign: 'right', marginTop: 8 }}>
          <Popconfirm title="确认终止此测试？" onConfirm={() => abortTest(fwTestId)}>
            <Button danger>终止测试</Button>
          </Popconfirm>
        </div>
      )}
    </div>
  );
};

export default FwTestDetail;
