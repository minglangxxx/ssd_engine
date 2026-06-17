import React, { useState } from 'react';
import { Table, Button, Space, Tag, Popconfirm, message, Modal, Input, Select } from 'antd';
import { EyeOutlined, DeleteOutlined, StopOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useSniaTaskList, useCreateSniaTask, useAbortSniaTask } from '@/hooks/useSniaTask';
import { useQuery } from '@tanstack/react-query';
import { deviceApi } from '@/api/device';
import { formatTime } from '@/utils/format';
import type { SniaTask, SniaStatus } from '@/types/snia';
import type { ColumnsType } from 'antd/es/table';

const STATUS_MAP: Record<SniaStatus, { color: string; text: string }> = {
  pending: { color: 'default', text: '等待中' },
  preconditioning: { color: 'processing', text: '预处理' },
  iops_test: { color: 'processing', text: 'IOPS 扫描' },
  steady_state: { color: 'processing', text: '稳态判定' },
  done: { color: 'success', text: '已完成' },
  failed: { color: 'error', text: '失败' },
  aborted: { color: 'warning', text: '已终止' },
};

const PHASE_MAP: Record<string, string> = {
  precondition: '预处理',
  iops_test: 'IOPS 扫描',
  steady_state: '稳态判定',
};

const SniaTaskList: React.FC = () => {
  const navigate = useNavigate();
  const [pagination, setPagination] = useState({ page: 1, pageSize: 10 });
  const [createVisible, setCreateVisible] = useState(false);

  const { data, isLoading } = useSniaTaskList(pagination);
  const { mutate: abortTask } = useAbortSniaTask();
  const { mutate: createTask, isPending: creating } = useCreateSniaTask();
  const { data: devices } = useQuery({
    queryKey: ['devices'],
    queryFn: () => deviceApi.list(),
    enabled: createVisible,
  });

  const [formName, setFormName] = useState('');
  const [formDeviceId, setFormDeviceId] = useState<number | undefined>();
  const [formDevicePath, setFormDevicePath] = useState('/dev/nvme0n1');

  const handleAbort = (id: number) => {
    abortTask(id, {
      onSuccess: () => message.success('已终止'),
    });
  };

  const handleCreate = () => {
    if (!formName.trim() || !formDeviceId) {
      message.warning('请填写名称并选择设备');
      return;
    }
    createTask(
      {
        name: formName.trim(),
        device_id: formDeviceId,
        device_path: formDevicePath,
      },
      {
        onSuccess: (result) => {
          message.success('SNIA 测试已创建');
          setCreateVisible(false);
          navigate(`/snia-tasks/${result.id}`);
        },
      },
    );
  };

  const columns: ColumnsType<SniaTask> = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: '名称', dataIndex: 'name', ellipsis: true },
    { title: '设备', dataIndex: 'device_ip', width: 130 },
    {
      title: '状态',
      dataIndex: 'status',
      width: 110,
      render: (s: SniaStatus) => {
        const m = STATUS_MAP[s] || { color: 'default', text: s };
        return <Tag color={m.color}>{m.text}</Tag>;
      },
    },
    {
      title: '当前阶段',
      dataIndex: 'current_phase',
      width: 100,
      render: (p: string | null) => p ? (PHASE_MAP[p] || p) : '-',
    },
    {
      title: '轮次',
      width: 100,
      render: (_: unknown, r: SniaTask) => `${r.current_round}/${r.total_rounds}`,
    },
    {
      title: '稳态达成',
      dataIndex: 'is_steady',
      width: 90,
      render: (v: boolean) => v ? <Tag color="green">是</Tag> : <Tag>否</Tag>,
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      width: 160,
      render: (t: string) => formatTime(t),
    },
    {
      title: '操作',
      width: 160,
      render: (_: unknown, record: SniaTask) => (
        <Space>
          <Button type="link" size="small" icon={<EyeOutlined />} onClick={() => navigate(`/snia-tasks/${record.id}`)}>
            详情
          </Button>
          {!['done', 'failed', 'aborted'].includes(record.status) && (
            <Popconfirm title="确认终止？" onConfirm={() => handleAbort(record.id)}>
              <Button type="link" size="small" danger icon={<StopOutlined />}>
                终止
              </Button>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <h2 style={{ margin: 0 }}>SNIA 标准测试</h2>
        <Button type="primary" onClick={() => setCreateVisible(true)}>
          创建 SNIA 测试
        </Button>
      </div>

      <Table
        columns={columns}
        dataSource={data?.items}
        rowKey="id"
        loading={isLoading}
        pagination={{
          current: pagination.page,
          pageSize: pagination.pageSize,
          total: data?.total,
          showTotal: (total) => `共 ${total} 条`,
          onChange: (page, pageSize) => setPagination({ page, pageSize }),
        }}
        size="small"
      />

      <Modal
        title="创建 SNIA 测试"
        open={createVisible}
        onCancel={() => setCreateVisible(false)}
        onOk={handleCreate}
        confirmLoading={creating}
        width={460}
      >
        <div style={{ marginBottom: 12 }}>
          <div style={{ marginBottom: 4 }}>测试名称</div>
          <Input
            value={formName}
            onChange={(e) => setFormName(e.target.value)}
            placeholder="例如: Samsung 980 Pro SNIA 稳态测试"
          />
        </div>
        <div style={{ marginBottom: 12 }}>
          <div style={{ marginBottom: 4 }}>选择设备（仅在线）</div>
          <Select
            value={formDeviceId}
            onChange={(v) => setFormDeviceId(v)}
            style={{ width: '100%' }}
            placeholder="选择在线设备"
            options={(devices || []).filter((d) => d.agent_status === 'online').map((d) => ({
              label: `#${d.id} ${d.ip} (${d.hostname || d.ip})`,
              value: d.id,
            }))}
          />
        </div>
        <div style={{ marginBottom: 12 }}>
          <div style={{ marginBottom: 4 }}>设备路径</div>
          <Input
            value={formDevicePath}
            onChange={(e) => setFormDevicePath(e.target.value)}
            placeholder="/dev/nvme0n1"
          />
        </div>
      </Modal>
    </div>
  );
};

export default SniaTaskList;
