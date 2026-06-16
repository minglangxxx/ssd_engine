import React from 'react';
import { Row, Col, Card, Statistic, Table, Tag, Button, Empty } from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  SyncOutlined,
  DesktopOutlined,
  UnorderedListOutlined,
  DashboardOutlined,
  CloudOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import ReactECharts from 'echarts-for-react';
import { useDashboardSummary } from '@/hooks/useDashboard';
import { deviceApi } from '@/api/device';
import { useQuery } from '@tanstack/react-query';
import TaskStatusBadge from '@/components/TaskStatusBadge/index';
import { formatShortTime } from '@/utils/format';
import type { ColumnsType } from 'antd/es/table';
import type { RecentTask } from '@/api/dashboard';

const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const { data: summary, isLoading: summaryLoading } = useDashboardSummary();
  const { data: devices } = useQuery({
    queryKey: ['devices'],
    queryFn: () => deviceApi.list(),
  });

  const recentColumns: ColumnsType<RecentTask> = [
    { title: '任务名称', dataIndex: 'name', ellipsis: true },
    {
      title: '状态',
      dataIndex: 'status',
      width: 90,
      render: (s) => <TaskStatusBadge status={s} />,
    },
    {
      title: 'IOPS',
      dataIndex: 'iops',
      width: 100,
      render: (v: number | null) => (v !== null && v !== undefined ? v.toLocaleString() : '--'),
    },
    {
      title: '带宽(MiB/s)',
      dataIndex: 'bw_mib',
      width: 110,
      render: (v: number | null) => (v !== null && v !== undefined ? v : '--'),
    },
    {
      title: '时间',
      dataIndex: 'created_at',
      width: 120,
      render: (t: string) => formatShortTime(t),
    },
    {
      title: '操作',
      width: 70,
      render: (_: unknown, record: RecentTask) => (
        <Button type="link" size="small" onClick={() => navigate(`/tasks/${record.id}`)}>
          查看
        </Button>
      ),
    },
  ];

  const trendOption = {
    tooltip: { trigger: 'axis' as const },
    xAxis: {
      type: 'category' as const,
      data: (summary?.chart_data || []).map((d) => formatShortTime(d.time)),
    },
    yAxis: [
      { type: 'value' as const, name: 'IOPS', position: 'left' as const },
      { type: 'value' as const, name: 'Latency(ms)', position: 'right' as const },
    ],
    series: [
      {
        name: 'IOPS',
        type: 'line',
        smooth: true,
        data: (summary?.chart_data || []).map((d) => d.iops),
        yAxisIndex: 0,
        areaStyle: { opacity: 0.1 },
      },
      {
        name: 'Latency(ms)',
        type: 'line',
        smooth: true,
        data: (summary?.chart_data || []).map((d) => d.lat_ms),
        yAxisIndex: 1,
      },
    ],
    grid: { top: 40, bottom: 30, left: 60, right: 60 },
  };

  const agents = summary?.agents || { total: 0, online: 0 };
  const tasks = summary?.tasks || { total: 0, running: 0, success: 0, failed: 0 };

  return (
    <div>
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={4}>
          <Card size="small" loading={summaryLoading}>
            <Statistic title="任务总数" value={tasks.total} prefix={<UnorderedListOutlined />} />
          </Card>
        </Col>
        <Col span={4}>
          <Card size="small" loading={summaryLoading}>
            <Statistic
              title="运行中"
              value={tasks.running}
              valueStyle={{ color: '#1890ff' }}
              prefix={<SyncOutlined spin={tasks.running > 0} />}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card size="small" loading={summaryLoading}>
            <Statistic
              title="成功"
              value={tasks.success}
              valueStyle={{ color: '#52c41a' }}
              prefix={<CheckCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card size="small" loading={summaryLoading}>
            <Statistic
              title="失败"
              value={tasks.failed}
              valueStyle={{ color: '#ff4d4f' }}
              prefix={<CloseCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card size="small" loading={summaryLoading}>
            <Statistic
              title="平均CPU"
              value={summary?.avg_cpu ?? '--'}
              suffix={summary?.avg_cpu !== null && summary?.avg_cpu !== undefined ? '%' : ''}
              prefix={<DashboardOutlined />}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card size="small" loading={summaryLoading}>
            <Statistic
              title="平均MEM"
              value={summary?.avg_memory ?? '--'}
              suffix={summary?.avg_memory !== null && summary?.avg_memory !== undefined ? '%' : ''}
              prefix={<CloudOutlined />}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={4}>
          <Card size="small" loading={summaryLoading}>
            <Statistic
              title="设备在线"
              value={agents.online}
              valueStyle={{ color: '#13c2c2' }}
              prefix={<DesktopOutlined />}
              suffix={`/ ${agents.total}`}
            />
          </Card>
        </Col>
      </Row>

      <Card title="最近任务" size="small" style={{ marginBottom: 16 }}>
        <Table
          columns={recentColumns}
          dataSource={summary?.recent_tasks || []}
          rowKey="id"
          pagination={false}
          size="small"
          loading={summaryLoading}
        />
      </Card>

      <Row gutter={16}>
        <Col span={12}>
          <Card title="设备节点状态" size="small">
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {(devices || []).map((d) => (
                <div key={d.id} style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span>{d.ip} ({d.name})</span>
                  <Tag color={d.agent_status === 'online' ? 'green' : 'red'}>
                    {d.agent_status === 'online' ? '在线' : '离线'}
                  </Tag>
                </div>
              ))}
              {(!devices || devices.length === 0) && (
                <span style={{ color: '#999' }}>暂无设备</span>
              )}
            </div>
          </Card>
        </Col>
        <Col span={12}>
          <Card title="IOPS / Latency 趋势" size="small">
            {(summary?.chart_data || []).length > 0 ? (
              <ReactECharts option={trendOption} style={{ height: 200 }} />
            ) : (
              <Empty description="暂无已完成的测试任务" />
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Dashboard;
