import React, { useState } from 'react';
import {
  Table,
  Button,
  Space,
  Tag,
  Modal,
  Form,
  Input,
  InputNumber,
  Popconfirm,
  message,
} from 'antd';
import { PlusOutlined, ReloadOutlined } from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { deviceApi } from '@/api/device';
import { formatTime } from '@/utils/format';
import type { Device } from '@/types/device';
import type { ColumnsType } from 'antd/es/table';

const DeviceManage: React.FC = () => {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [modalVisible, setModalVisible] = useState(false);
  const [editingDevice, setEditingDevice] = useState<Device | null>(null);
  const [form] = Form.useForm();

  const { data: devices, isLoading, isFetching, refetch } = useQuery({
    queryKey: ['devices'],
    queryFn: () => deviceApi.list(),
    refetchOnMount: 'always',
  });

  const addMutation = useMutation({
    mutationFn: deviceApi.add,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['devices'] });
      message.success('添加成功');
      setModalVisible(false);
      form.resetFields();
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: { name?: string; agent_port?: number } }) =>
      deviceApi.update(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['devices'] });
      message.success('更新成功');
      setModalVisible(false);
      setEditingDevice(null);
      form.resetFields();
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deviceApi.delete,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['devices'] });
      message.success('删除成功');
    },
  });

  const handleRefreshStatus = async () => {
    await refetch();
    message.success('设备状态已刷新');
  };

  const handleSubmit = async () => {
    const values = await form.validateFields();
    if (editingDevice) {
      updateMutation.mutate({ id: editingDevice.id, data: { name: values.name, agent_port: values.agent_port } });
    } else {
      addMutation.mutate(values);
    }
  };

  const handleEdit = (device: Device) => {
    setEditingDevice(device);
    form.setFieldsValue(device);
    setModalVisible(true);
  };

  const columns: ColumnsType<Device> = [
    { title: 'IP地址', dataIndex: 'ip', width: 140 },
    { title: '名称', dataIndex: 'name', width: 120 },
    {
      title: 'Agent状态',
      dataIndex: 'agent_status',
      width: 100,
      render: (s: string) => (
        <Tag color={s === 'online' ? 'green' : 'red'}>{s === 'online' ? '在线' : '离线'}</Tag>
      ),
    },
    { title: '版本', dataIndex: 'agent_version', width: 80 },
    {
      title: '最后心跳',
      dataIndex: 'last_heartbeat',
      width: 160,
      render: (t: string) => (t ? formatTime(t) : '-'),
    },
    {
      title: '操作',
      width: 180,
      render: (_: unknown, record: Device) => (
        <Space>
          <Button type="link" size="small" onClick={() => navigate(`/devices/${record.id}`)}>
            详情
          </Button>
          <Button type="link" size="small" onClick={() => handleEdit(record)}>
            编辑
          </Button>
          <Popconfirm title="确认删除？" onConfirm={() => deleteMutation.mutate(record.id)}>
            <Button type="link" size="small" danger>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <h2 style={{ margin: 0 }}>设备管理</h2>
        <Space>
          <Button icon={<ReloadOutlined />} loading={isFetching && !isLoading} onClick={handleRefreshStatus}>
            刷新状态
          </Button>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => {
              setEditingDevice(null);
              form.resetFields();
              setModalVisible(true);
            }}
          >
            添加设备
          </Button>
        </Space>
      </div>

      <Table
        columns={columns}
        dataSource={devices}
        rowKey="id"
        loading={isLoading}
        size="small"
      />

      <Modal
        title={editingDevice ? '编辑设备' : '添加设备'}
        open={modalVisible}
        onCancel={() => {
          setModalVisible(false);
          setEditingDevice(null);
        }}
        onOk={handleSubmit}
        confirmLoading={addMutation.isPending || updateMutation.isPending}
      >
        <Form form={form} layout="vertical">
          {!editingDevice && (
            <Form.Item name="ip" label="IP地址" rules={[{ required: true }]}>
              <Input placeholder="如: 10.0.0.1" />
            </Form.Item>
          )}
          <Form.Item name="name" label="名称" rules={[{ required: true }]}>
            <Input placeholder="如: Node-01" />
          </Form.Item>
          <Form.Item name="agent_port" label="Agent端口" initialValue={8080}>
            <InputNumber min={1} max={65535} style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default DeviceManage;