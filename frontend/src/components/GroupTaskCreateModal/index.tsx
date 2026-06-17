import React, { useState } from 'react';
import {
  Modal,
  Form,
  Input,
  InputNumber,
  Select,
  Checkbox,
  Card,
  Row,
  Col,
  Transfer,
  Button,
  Space,
  message,
  Alert,
  Divider,
} from 'antd';
import { useQuery } from '@tanstack/react-query';
import { useCreateGroupTask } from '@/hooks/useGroupTask';
import { buildFioConfig, type FioConfig } from '@/types/task';
import { deviceApi } from '@/api/device';
import {
  RW_OPTIONS,
  IOENGINE_OPTIONS,
  TASK_TEMPLATE_OPTIONS,
  TASK_TEMPLATE_PRESETS,
} from '@/utils/constants';
import type { Device } from '@/types/device';

type TemplateKey = keyof typeof TASK_TEMPLATE_PRESETS | 'custom';

interface GroupTaskCreateProps {
  visible: boolean;
  onClose: () => void;
}

const GroupTaskCreate: React.FC<GroupTaskCreateProps> = ({ visible, onClose }) => {
  const [form] = Form.useForm();
  const { mutateAsync: createGroupTask, isPending } = useCreateGroupTask();
  const selectedTemplate = (Form.useWatch('template', form) as TemplateKey | undefined) || 'custom';
  const selectedRw = Form.useWatch(['config', 'rw'], form) as FioConfig['rw'] | undefined;

  const { data: devices } = useQuery({
    queryKey: ['devices'],
    queryFn: () => deviceApi.list(),
    enabled: visible,
  });

  const onlineDevices = (devices || []).filter((d: Device) => d.agent_status === 'online');
  const transferDataSource = onlineDevices.map((d: Device) => ({
    key: String(d.id),
    title: `${d.name} (${d.ip})`,
  }));

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      const fioConfig = buildFioConfig(values.config || {});
      const selectedIds = values.device_ids.map((id: string) => Number(id));
      await createGroupTask({
        name: values.name,
        device_ids: selectedIds,
        fio_config: fioConfig,
        device_path: values.device_path || undefined,
      });
      message.success('组任务创建成功');
      form.resetFields();
      onClose();
    } catch {
      // validation errors handled by antd
    }
  };

  return (
    <Modal
      title="创建多盘并发测试"
      open={visible}
      onCancel={onClose}
      footer={null}
      width={760}
      destroyOnClose
    >
      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
        initialValues={{ template: 'custom', config: {}, device_path: '/dev/nvme0n1' }}
      >
        <Form.Item name="name" label="任务名称" rules={[{ required: true, message: '请输入任务名称' }]}>
          <Input placeholder="如: 3盘 4K RandRead 并发测试" allowClear />
        </Form.Item>

        <Card title="选择设备" size="small" style={{ marginBottom: 16 }}>
          <Form.Item name="device_ids" rules={[{ required: true, message: '请选择至少一台设备' }]}>
            <Transfer
              dataSource={transferDataSource}
              render={(item) => item.title}
              titles={['在线设备', '已选设备']}
              showSearch
              listStyle={{ width: 280, height: 240 }}
              filterOption={(input, item) => item.title.toLowerCase().includes(input.toLowerCase())}
            />
          </Form.Item>
          <Form.Item name="device_path" label="统一设备路径">
            <Input placeholder="/dev/nvme0n1" allowClear />
          </Form.Item>
        </Card>

        <Card title="FIO 配置" size="small" style={{ marginBottom: 16 }}>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="template" label="测试模板">
                <Select options={TASK_TEMPLATE_OPTIONS} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name={['config', 'rw']} label="读写模式" rules={[{ required: true, message: '请选择' }]}>
                <Select options={RW_OPTIONS} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name={['config', 'bs']} label="块大小">
                <Input placeholder="4k" allowClear />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name={['config', 'iodepth']} label="IO深度">
                <InputNumber min={1} max={256} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name={['config', 'numjobs']} label="并发数">
                <InputNumber min={1} max={64} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name={['config', 'runtime']} label="运行时间(秒)">
                <InputNumber min={1} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name={['config', 'ioengine']} label="IO引擎">
                <Select options={IOENGINE_OPTIONS} allowClear placeholder="默认" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name={['config', 'time_based']} valuePropName="checked">
                <Checkbox>基于时间</Checkbox>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name={['config', 'direct']} valuePropName="checked">
                <Checkbox>Direct IO</Checkbox>
              </Form.Item>
            </Col>
          </Row>
          <Alert
            type="info"
            showIcon
            message="所有已选设备将使用相同的 FIO 配置执行测试"
          />
        </Card>

        <Divider style={{ margin: '16px 0' }} />

        <div style={{ textAlign: 'right' }}>
          <Space>
            <Button onClick={onClose}>取消</Button>
            <Button type="primary" htmlType="submit" loading={isPending}>
              创建并发任务
            </Button>
          </Space>
        </div>
      </Form>
    </Modal>
  );
};

export default GroupTaskCreate;
