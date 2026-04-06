import React from 'react';
import { Row, Col, Card, Statistic, Table, Tag, Button, Space } from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  SyncOutlined,
  DesktopOutlined,
  UnorderedListOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import ReactECharts from 'echarts-for-react';
import { taskApi } from '@/api/task';
import { deviceApi } from '@/api/device';
import TaskStatusBadge from '@/components/TaskStatusBadge/index';
import { formatShortTime } from '@/utils/format';
import type { Task } from '@/types/task';
import type { ColumnsType } from 'antd/es/table';

const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const { data: taskData } = useQuery({
    queryKey: ['tasks', { page: 1, pageSize: 10 }],
    queryFn: () => taskApi.list({ page: 1, pageSize: 10 }),
  });
  const { data: devices } = useQuery({
    queryKey: ['devices'],
    queryFn: () => deviceApi.list(),
  });

  const tasks = taskData?.items || [];
  const total = taskData?.total || 0;
  const running = tasks.filter((t: Task) => t.status === 'RUNNING').length;
  const success = tasks.filter((t: Task) => t.status === 'SUCCESS').length;
  const failed = tasks.filter((t: Task) => t.status === 'FAILED').length;
  const devOnline = (devices || []).filter((d) => d.agent_status === 'online').length;

  const recentColumns: ColumnsType<Task> = [
    { title: '任务名称', dataIndex: 'name', ellipsis: true },
    {
      title: '状态',
      dataIndex: 'status',
      width: 90,
      render: (s) => <TaskStatusBadge status={s} />,
    },
    { title: '设备IP', dataIndex: 'device_ip', width: 130 },
    {
      title: '时间',
      dataIndex: 'created_at',
      width: 120,
      render: (t: string) => formatShortTime(t),
    },
    {
      title: '操作',
      width: 70,
      render: (_: unknown, record: Task) => (
        <Button type="link" size="small" onClick={() => navigate(`/tasks/${record.id}`)}>
          查看
        </Button>
      ),
    },
  ];

  const trendOption = {
    tooltip: { trigger: 'axis' as const },
    xAxis: { type: 'category' as const, data: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'] },
    yAxis: { type: 'value' as const, name: 'IOPS' },
    series: [
      {
        name: 'IOPS',
        type: 'line',
        smooth: true,
        data: [120000, 132000, 101000, 134000, 90000, 230000, 210000],
        areaStyle: { opacity: 0.1 },
      },
    ],
    grid: { top: 40, bottom: 30, left: 60, right: 20 },
  };

  return (
    <div>
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={4}>
          <Card size="small">
            <Statistic title="任务总数" value={total} prefix={<UnorderedListOutlined />} />
          </Card>
        </Col>
        <Col span={5}>
          <Card size="small">
            <Statistic title="运行中" value={running} valueStyle={{ color: '#1890ff' }} prefix={<SyncOutlined spin={running > 0} />} />
          </Card>
        </Col>
        <Col span={5}>
          <Card size="small">
            <Statistic title="成功" value={success} valueStyle={{ color: '#52c41a' }} prefix={<CheckCircleOutlined />} />
          </Card>
        </Col>
        <Col span={5}>
          <Card size="small">
            <Statistic title="失败" value={failed} valueStyle={{ color: '#ff4d4f' }} prefix={<CloseCircleOutlined />} />
          </Card>
        </Col>
        <Col span={5}>
          <Card size="small">
            <Statistic title="设备在线" value={devOnline} valueStyle={{ color: '#13c2c2' }} prefix={<DesktopOutlined />} />
          </Card>
        </Col>
      </Row>

      <Card title="最近任务" size="small" style={{ marginBottom: 16 }}>
        <Table
          columns={recentColumns}
          dataSource={tasks.slice(0, 5)}
          rowKey="id"
          pagination={false}
          size="small"
        />
      </Card>

      <Row gutter={16}>
        <Col span={12}>
          <Card title="设备节点状态" size="small">
            <Space direction="vertical" style={{ width: '100%' }}>
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
            </Space>
          </Card>
        </Col>
        <Col span={12}>
          <Card title="全局IOPS趋势" size="small">
            <ReactECharts option={trendOption} style={{ height: 200 }} />
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Dashboard;
