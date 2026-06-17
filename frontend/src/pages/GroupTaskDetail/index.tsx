import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Card,
  Descriptions,
  Row,
  Col,
  Statistic,
  Button,
  Space,
  Table,
  Tag,
} from 'antd';
import { ArrowLeftOutlined } from '@ant-design/icons';
import { useGroupTaskDetail } from '@/hooks/useGroupTask';
import { formatTime, formatNumber } from '@/utils/format';
import type { GroupTask, GroupTaskStatus } from '@/types/group-task';
import type { TaskStatus } from '@/types/task';
import type { ColumnsType } from 'antd/es/table';

const GT_STATUS_MAP: Record<GroupTaskStatus, { color: string; text: string }> = {
  pending: { color: 'default', text: '等待中' },
  running: { color: 'processing', text: '运行中' },
  done: { color: 'success', text: '已完成' },
  failed: { color: 'error', text: '失败' },
  partial: { color: 'warning', text: '部分完成' },
};

const TASK_STATUS_MAP: Record<TaskStatus, { color: string; text: string }> = {
  PENDING: { color: 'default', text: '等待中' },
  RUNNING: { color: 'processing', text: '运行中' },
  SUCCESS: { color: 'success', text: '成功' },
  FAILED: { color: 'error', text: '失败' },
};

const GroupTaskDetail: React.FC = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const groupId = Number(id);
  const { data: group, isLoading } = useGroupTaskDetail(groupId);

  if (isLoading || !group) {
    return <Card loading={isLoading}>加载中...</Card>;
  }

  const s = group.summary;

  const subColumns: ColumnsType<GroupTask['sub_tasks'][0]> = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: '名称', dataIndex: 'name', width: 180, ellipsis: true },
    { title: '设备IP', dataIndex: 'device_ip', width: 140 },
    { title: '设备路径', dataIndex: 'device_path', width: 150 },
    {
      title: '状态',
      dataIndex: 'status',
      width: 90,
      render: (v: TaskStatus) => {
        const m = TASK_STATUS_MAP[v] || { color: 'default', text: v };
        return <Tag color={m.color}>{m.text}</Tag>;
      },
    },
    {
      title: 'IOPS',
      width: 110,
      render: (_: unknown, r: GroupTask['sub_tasks'][0]) =>
        r.result?.iops != null ? formatNumber(r.result.iops) : '-',
    },
    {
      title: '带宽(MB/s)',
      width: 110,
      render: (_: unknown, r: GroupTask['sub_tasks'][0]) =>
        r.result?.bandwidth != null ? formatNumber(r.result.bandwidth) : '-',
    },
    {
      title: '平均延迟(μs)',
      width: 120,
      render: (_: unknown, r: GroupTask['sub_tasks'][0]) =>
        r.result?.latency?.mean != null ? r.result.latency.mean.toFixed(1) : '-',
    },
    {
      title: 'P99延迟(μs)',
      width: 110,
      render: (_: unknown, r: GroupTask['sub_tasks'][0]) =>
        r.result?.latency?.p99 != null ? r.result.latency.p99.toFixed(1) : '-',
    },
    {
      title: '操作',
      width: 80,
      render: (_: unknown, r: GroupTask['sub_tasks'][0]) => (
        <Button type="link" size="small" onClick={() => navigate(`/tasks/${r.id}`)}>
          详情
        </Button>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/group-tasks')}>
            返回列表
          </Button>
          <h2 style={{ margin: 0 }}>组任务详情 - {group.name}</h2>
        </Space>
        <Tag color={GT_STATUS_MAP[group.status]?.color}>
          {GT_STATUS_MAP[group.status]?.text || group.status}
        </Tag>
      </div>

      <Card title="基本信息" size="small" style={{ marginBottom: 16 }}>
        <Descriptions column={4} size="small">
          <Descriptions.Item label="组任务ID">{group.id}</Descriptions.Item>
          <Descriptions.Item label="子任务进度">{group.done_count}/{group.total_count}</Descriptions.Item>
          <Descriptions.Item label="读写模式">{group.fio_config?.rw}</Descriptions.Item>
          <Descriptions.Item label="块大小">{group.fio_config?.bs || '4k'}</Descriptions.Item>
          <Descriptions.Item label="IO深度">{group.fio_config?.iodepth || 32}</Descriptions.Item>
          <Descriptions.Item label="运行时间">{group.fio_config?.runtime ? `${group.fio_config.runtime}s` : '-'}</Descriptions.Item>
          <Descriptions.Item label="创建时间">{formatTime(group.created_at)}</Descriptions.Item>
          <Descriptions.Item label="更新时间">{formatTime(group.updated_at)}</Descriptions.Item>
        </Descriptions>
      </Card>

      {s && (
        <Card title="汇总结果 (Max / Min / Avg)" size="small" style={{ marginBottom: 16 }}>
          <Row gutter={16}>
            <Col span={6}>
              <Statistic title="IOPS Max" value={s.iops_max} formatter={(v) => formatNumber(v as number)} />
            </Col>
            <Col span={6}>
              <Statistic title="IOPS Min" value={s.iops_min} formatter={(v) => formatNumber(v as number)} />
            </Col>
            <Col span={6}>
              <Statistic title="IOPS Avg" value={s.iops_avg} precision={1} />
            </Col>
          </Row>
          <Row gutter={16} style={{ marginTop: 16 }}>
            <Col span={6}>
              <Statistic title="带宽 Max (MB/s)" value={s.bw_max} precision={1} />
            </Col>
            <Col span={6}>
              <Statistic title="带宽 Min (MB/s)" value={s.bw_min} precision={1} />
            </Col>
            <Col span={6}>
              <Statistic title="带宽 Avg (MB/s)" value={s.bw_avg} precision={1} />
            </Col>
          </Row>
          <Row gutter={16} style={{ marginTop: 16 }}>
            <Col span={6}>
              <Statistic title="平均延迟 Max (μs)" value={s.lat_mean_max} precision={1} />
            </Col>
            <Col span={6}>
              <Statistic title="平均延迟 Min (μs)" value={s.lat_mean_min} precision={1} />
            </Col>
            <Col span={6}>
              <Statistic title="平均延迟 Avg (μs)" value={s.lat_mean_avg} precision={1} />
            </Col>
          </Row>
          {s.lat_p99_max != null && (
            <Row gutter={16} style={{ marginTop: 16 }}>
              <Col span={6}>
                <Statistic title="P99延迟 Max (μs)" value={s.lat_p99_max} precision={1} />
              </Col>
              <Col span={6}>
                <Statistic title="P99延迟 Min (μs)" value={s.lat_p99_min} precision={1} />
              </Col>
              <Col span={6}>
                <Statistic title="P99延迟 Avg (μs)" value={s.lat_p99_avg} precision={1} />
              </Col>
            </Row>
          )}
        </Card>
      )}

      <Card title="子任务列表" size="small">
        <Table
          columns={subColumns}
          dataSource={group.sub_tasks || []}
          rowKey="id"
          size="small"
          pagination={false}
        />
      </Card>
    </div>
  );
};

export default GroupTaskDetail;
