import React, { useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, Descriptions, Table, Button, Space, Tag } from 'antd';
import { ArrowLeftOutlined } from '@ant-design/icons';
import ReactEChartsCore from 'echarts-for-react/lib/core';
import * as echarts from 'echarts/core';
import { LineChart } from 'echarts/charts';
import { GridComponent, TooltipComponent, LegendComponent, MarkLineComponent } from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';
import { useRegressionDetail } from '@/hooks/useRegression';
import { useBaselineDetail } from '@/hooks/useBaseline';
import { formatTime } from '@/utils/format';
import type { RegressionMetric, RegressionVerdict } from '@/types/regression';

echarts.use([LineChart, GridComponent, TooltipComponent, LegendComponent, MarkLineComponent, CanvasRenderer]);

const THRESHOLD_TABLE: Record<string, { warning: number; fail: number }> = {
  iops: { warning: -5, fail: -10 },
  bw: { warning: -5, fail: -10 },
  lat_mean: { warning: 10, fail: 20 },
  lat_p99: { warning: 15, fail: 30 },
};

const verdictColor: Record<RegressionVerdict, string> = {
  PASS: 'green',
  WARNING: 'orange',
  FAIL: 'red',
};

const verdictBgColor: Record<RegressionVerdict, string> = {
  PASS: '#f6ffed',
  WARNING: '#fff7e6',
  FAIL: '#fff2f0',
};

const RegressionDetail: React.FC = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const regressionId = Number(id);
  const { data: regression, isLoading } = useRegressionDetail(regressionId);
  const { data: baseline } = useBaselineDetail(regression?.baseline_id ?? 0);

  const metrics = regression?.detail?.metrics || [];

  const trendChartOption = useMemo(() => {
    if (!metrics.length) return {};
    const diffData = metrics.map((m: RegressionMetric) => ({
      name: m.display_name,
      metricName: m.name,
      value: m.diff_pct,
      isLatency: m.name.startsWith('lat'),
    }));

    return {
      tooltip: { trigger: 'axis' as const },
      legend: {},
      xAxis: { type: 'category' as const, data: diffData.map((d) => d.name) },
      yAxis: { type: 'value' as const, name: '差异%' },
      series: [
        {
          name: '差异%',
          type: 'line' as const,
          data: diffData.map((d) => d.value),
          itemStyle: { color: '#1890ff' },
          markLine: {
            silent: true,
            symbol: 'none' as const,
            data: [
              { yAxis: 0, lineStyle: { color: '#52c41a', type: 'solid' as const }, label: { formatter: '基线(0%)' } },
              ...diffData.flatMap((d) => {
                const t = THRESHOLD_TABLE[d.metricName];
                if (!t) return [];
                return [
                  { yAxis: t.warning, lineStyle: { color: '#fa8c16', type: 'dashed' as const }, label: { formatter: `WARNING(${t.warning}%)`, position: 'insideEndTop' as const } },
                  { yAxis: t.fail, lineStyle: { color: '#f5222d', type: 'dashed' as const }, label: { formatter: `FAIL(${t.fail}%)`, position: 'insideEndTop' as const } },
                ];
              }),
            ],
          },
        },
      ],
    };
  }, [metrics]);

  const baselineName = baseline?.name || `#${regression?.baseline_id ?? ''}`;

  if (isLoading || !regression) {
    return <Card loading={isLoading}>加载中...</Card>;
  }

  const columns = [
    {
      title: '指标',
      dataIndex: 'display_name',
      width: 120,
    },
    {
      title: '基线值',
      dataIndex: 'baseline',
      width: 120,
      render: (v: number, r: RegressionMetric) => `${v} ${r.unit}`,
    },
    {
      title: '当前值',
      dataIndex: 'current',
      width: 120,
      render: (v: number, r: RegressionMetric) => `${v} ${r.unit}`,
    },
    {
      title: '差异',
      dataIndex: 'diff_pct',
      width: 120,
      render: (v: number, r: RegressionMetric) => (
        <Space>
          <span>{v > 0 ? '+' : ''}{v}%</span>
          <Tag color={verdictColor[r.verdict]}>{r.verdict}</Tag>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/regressions')}>
            返回列表
          </Button>
          <h2 style={{ margin: 0 }}>回归结果 #{regression.id}</h2>
        </Space>
        <Tag
          color={verdictColor[regression.verdict]}
          style={{ fontSize: 14, padding: '4px 12px' }}
        >
          {regression.verdict}
        </Tag>
      </div>

      <Card
        title="回归信息"
        size="small"
        style={{
          marginBottom: 16,
          background: verdictBgColor[regression.verdict],
        }}
      >
        <Descriptions column={4} size="small">
          <Descriptions.Item label="任务ID">
            <Button type="link" size="small" onClick={() => navigate(`/tasks/${regression.task_id}`)}>
              #{regression.task_id}
            </Button>
          </Descriptions.Item>
          <Descriptions.Item label="基线">
            <Button type="link" size="small" onClick={() => navigate(`/baselines/${regression.baseline_id}`)}>
              {baselineName}
            </Button>
          </Descriptions.Item>
          <Descriptions.Item label="判定结果">
            <Tag color={verdictColor[regression.verdict]}>{regression.verdict}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="创建时间">{formatTime(regression.created_at)}</Descriptions.Item>
        </Descriptions>
      </Card>

      <Card title="三列对比表" size="small" style={{ marginBottom: 16 }}>
        <Table
          columns={columns}
          dataSource={metrics}
          rowKey="name"
          pagination={false}
          size="small"
        />
      </Card>

      {metrics.length > 0 && (
        <Card title="差异趋势" size="small" style={{ marginBottom: 16 }}>
          <ReactEChartsCore echarts={echarts} option={trendChartOption} style={{ height: 300 }} />
        </Card>
      )}
    </div>
  );
};

export default RegressionDetail;
