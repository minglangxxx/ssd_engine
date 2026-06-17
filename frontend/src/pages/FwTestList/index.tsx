import React, { useState } from 'react';
import { Table, Button, Tag, Space, message, Modal, Input, Select, Popconfirm } from 'antd';
import { useNavigate } from 'react-router-dom';
import { useFwTestList, useCreateFwTest, useAbortFwTest } from '@/hooks/useFwTest';
import { useQuery } from '@tanstack/react-query';
import { deviceApi } from '@/api/device';
import { formatTime, formatNumber } from '@/utils/format';
import type { FwUpgradeTest, FwTestStatus } from '@/types/fw-test';
import type { ColumnsType } from 'antd/es/table';

const STATUS_MAP: Record<FwTestStatus, { color: string; text: string }> = {
  pending: { color: 'default', text: '等待中' },
  collecting_baseline: { color: 'processing', text: '采集基线' },
  waiting_upgrade: { color: 'warning', text: '等待升级' },
  testing_after: { color: 'processing', text: '升级后测试' },
  done: { color: 'success', text: '已完成' },
  failed: { color: 'error', text: '失败' },
};

const FwTestList: React.FC = () => {
  const navigate = useNavigate();
  const [pagination, setPagination] = useState({ page: 1, pageSize: 10 });
  const [createVisible, setCreateVisible] = useState(false);

  const { data, isLoading } = useFwTestList(pagination);
  const { data: devices } = useQuery({
    queryKey: ['devices'],
    queryFn: () => deviceApi.list(),
    enabled: createVisible,
  });
  const { mutate: createTest, isPending: creating } = useCreateFwTest();
  const { mutate: abortTest } = useAbortFwTest();

  const [formName, setFormName] = useState('');
  const [formDeviceId, setFormDeviceId] = useState<number | undefined>();
  const [formDevicePath, setFormDevicePath] = useState('/dev/nvme0n1');
  const [formRw, setFormRw] = useState<string>('randread');
  const [formBs, setFormBs] = useState<string>('4k');
  const [formIodepth, setFormIodepth] = useState<number>(32);
  const [formRuntime, setFormRuntime] = useState<number>(300);

  const handleCreate = () => {
    if (!formName.trim() || !formDeviceId) {
      message.warning('请填写名称并选择设备');
      return;
    }
    createTest(
      {
        name: formName.trim(),
        device_id: formDeviceId,
        device_path: formDevicePath,
        fio_config: { rw: formRw, bs: formBs, iodepth: formIodepth, runtime: formRuntime },
      },
      {
        onSuccess: (result) => {
          message.success('固件升级测试已创建');
          setCreateVisible(false);
          navigate(`/fw-tests/${result.id}`);
        },
      },
    );
  };

  const columns: ColumnsType<FwUpgradeTest> = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: '名称', dataIndex: 'name', width: 200, ellipsis: true },
    { title: '设备IP', dataIndex: 'device_ip', width: 140 },
    { title: '设备路径', dataIndex: 'device_path', width: 140 },
    {
      title: '升级前FW',
      dataIndex: 'fw_before',
      width: 120,
      render: (v: string | null) => v || '-',
    },
    {
      title: '升级后FW',
      dataIndex: 'fw_after',
      width: 120,
      render: (v: string | null) => v || '-',
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      render: (s: FwTestStatus) => (
        <Tag color={STATUS_MAP[s]?.color}>{STATUS_MAP[s]?.text || s}</Tag>
      ),
    },
    {
      title: 'IOPS(前)',
      width: 110,
      render: (_: unknown, r: FwUpgradeTest) =>
        r.result_before ? formatNumber(r.result_before.iops) : '-',
    },
    {
      title: 'IOPS(后)',
      width: 110,
      render: (_: unknown, r: FwUpgradeTest) =>
        r.result_after ? formatNumber(r.result_after.iops) : '-',
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      width: 160,
      render: (t: string) => formatTime(t),
    },
    {
      title: '操作',
      width: 140,
      render: (_: unknown, record: FwUpgradeTest) => (
        <Space>
          <Button type="link" size="small" onClick={() => navigate(`/fw-tests/${record.id}`)}>
            详情
          </Button>
          {record.status !== 'done' && record.status !== 'failed' && (
            <Popconfirm title="确认终止此测试？" onConfirm={() => abortTest(record.id)}>
              <Button type="link" size="small" danger>终止</Button>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  const onlineDevices = (devices || []).filter((d) => d.agent_status === 'online');

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <h2 style={{ margin: 0 }}>固件升级验证</h2>
        <Button type="primary" onClick={() => setCreateVisible(true)}>
          创建测试
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
        title="创建固件升级测试"
        open={createVisible}
        onCancel={() => setCreateVisible(false)}
        onOk={handleCreate}
        confirmLoading={creating}
        width={520}
      >
        <div style={{ marginBottom: 12 }}>
          <div style={{ marginBottom: 4 }}>测试名称</div>
          <Input
            value={formName}
            onChange={(e) => setFormName(e.target.value)}
            placeholder="例如: Samsung 980 Pro FW升级验证"
          />
        </div>
        <div style={{ marginBottom: 12 }}>
          <div style={{ marginBottom: 4 }}>选择设备（仅在线）</div>
          <Select
            value={formDeviceId}
            onChange={(v) => setFormDeviceId(v)}
            style={{ width: '100%' }}
            placeholder="选择在线设备"
            options={onlineDevices.map((d) => ({
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
        <div style={{ marginBottom: 12 }}>
          <div style={{ marginBottom: 4 }}>读写模式</div>
          <Select
            value={formRw}
            onChange={setFormRw}
            style={{ width: '100%' }}
            options={[
              { label: '随机读 (randread)', value: 'randread' },
              { label: '随机写 (randwrite)', value: 'randwrite' },
              { label: '随机读写 (randrw)', value: 'randrw' },
              { label: '顺序读 (read)', value: 'read' },
              { label: '顺序写 (write)', value: 'write' },
            ]}
          />
        </div>
        <div style={{ display: 'flex', gap: 12 }}>
          <div style={{ flex: 1 }}>
            <div style={{ marginBottom: 4 }}>块大小</div>
            <Input value={formBs} onChange={(e) => setFormBs(e.target.value)} />
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ marginBottom: 4 }}>IO深度</div>
            <Input
              type="number"
              value={formIodepth}
              onChange={(e) => setFormIodepth(Number(e.target.value) || 1)}
            />
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ marginBottom: 4 }}>运行时间(秒)</div>
            <Input
              type="number"
              value={formRuntime}
              onChange={(e) => setFormRuntime(Number(e.target.value) || 60)}
            />
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default FwTestList;
