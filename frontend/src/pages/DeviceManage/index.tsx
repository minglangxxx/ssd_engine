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
  Descriptions,
  Card,
} from 'antd';
import { PlusOutlined, ApiOutlined } from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { deviceApi } from '@/api/device';
import { formatTime } from '@/utils/format';
import type { Device } from '@/types/device';
import type { ColumnsType } from 'antd/es/table';

const DeviceManage: React.FC = () => {
  const qc = useQueryClient();
  const [modalVisible, setModalVisible] = useState(false);
  const [editingDevice, setEditingDevice] = useState<Device | null>(null);
  const [selectedDevice, setSelectedDevice] = useState<Device | null>(null);
  const [form] = Form.useForm();

  const { data: devices, isLoading } = useQuery({
    queryKey: ['devices'],
    queryFn: () => deviceApi.list(),
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

  const testMutation = useMutation({
    mutationFn: deviceApi.testConnection,
    onSuccess: (result) => {
      if (result.success) {
        message.success('连接成功');
      } else {
        message.error(`连接失败: ${result.message}`);
      }
    },
  });

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
          <Button type="link" size="small" onClick={() => setSelectedDevice(record)}>
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
      </div>

      <Table
        columns={columns}
        dataSource={devices}
        rowKey="id"
        loading={isLoading}
        size="small"
        onRow={(record) => ({
          onClick: () => setSelectedDevice(record),
          style: { cursor: 'pointer' },
        })}
      />

      {selectedDevice && (
        <Card title={`设备详情 - ${selectedDevice.ip}`} size="small" style={{ marginTop: 16 }}>
          <Descriptions column={3} size="small">
            <Descriptions.Item label="节点IP">{selectedDevice.ip}</Descriptions.Item>
            <Descriptions.Item label="名称">{selectedDevice.name}</Descriptions.Item>
            <Descriptions.Item label="Agent端口">{selectedDevice.agent_port}</Descriptions.Item>
            <Descriptions.Item label="磁盘列表">
              {selectedDevice.disks?.join(', ') || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="版本">{selectedDevice.agent_version}</Descriptions.Item>
            <Descriptions.Item label="状态">
              <Tag color={selectedDevice.agent_status === 'online' ? 'green' : 'red'}>
                {selectedDevice.agent_status}
              </Tag>
            </Descriptions.Item>
          </Descriptions>
          <Space style={{ marginTop: 12 }}>
            <Button
              icon={<ApiOutlined />}
              loading={testMutation.isPending}
              onClick={() =>
                testMutation.mutate({
                  ip: selectedDevice.ip,
                  user: 'root',
                  password: '',
                })
              }
            >
              测试连接
            </Button>
          </Space>
        </Card>
      )}

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
