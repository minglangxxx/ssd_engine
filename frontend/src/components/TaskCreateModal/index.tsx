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
  Tabs,
  Collapse,
  Button,
  Space,
  message,
} from 'antd';
import { useCreateTask } from '@/hooks/useTask';
import { buildFioConfig } from '@/types/task';
import {
  RW_OPTIONS,
  IOENGINE_OPTIONS,
  VERIFY_OPTIONS,
  MEM_OPTIONS,
  RANDOM_DIST_OPTIONS,
  FAULT_TYPE_OPTIONS,
} from '@/utils/constants';

interface TaskCreateModalProps {
  visible: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

const TaskCreateModal: React.FC<TaskCreateModalProps> = ({ visible, onClose, onSuccess }) => {
  const [form] = Form.useForm();
  const { mutateAsync: createTask, isPending } = useCreateTask();
  const [advancedExpanded, setAdvancedExpanded] = useState(false);

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      const fioConfig = buildFioConfig(values.config || {});
      await createTask({
        name: values.name,
        device_ip: values.device_ip,
        device_user: values.device_user,
        device_password: values.device_password,
        device_path: values.device_path,
        config: fioConfig,
        fault_type: values.fault_type || 'none',
      });
      message.success('任务创建成功');
      form.resetFields();
      onSuccess();
    } catch (error: unknown) {
      const err = error as { response?: { data?: { error?: { code?: string; message?: string } } } };
      if (err?.response?.data?.error?.code === 'FIO_CONFIG_ERROR') {
        Modal.error({
          title: 'FIO配置错误',
          content: err.response?.data?.error?.message,
        });
      }
    }
  };

  return (
    <Modal
      title="创建测试任务"
      open={visible}
      onCancel={onClose}
      footer={null}
      width={720}
      destroyOnClose
    >
      <Form form={form} layout="vertical" onFinish={handleSubmit}>
        {/* 任务名称 */}
        <Form.Item name="name" label="任务名称">
          <Input placeholder="可选，不填则自动生成" allowClear />
        </Form.Item>

        {/* 设备配置 */}
        <Card title="设备配置" size="small" style={{ marginBottom: 16 }}>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="device_ip" label="设备IP" rules={[{ required: true, message: '请输入设备IP' }]}>
                <Input placeholder="如: 10.0.0.1" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="device_user" label="SSH用户名" rules={[{ required: true, message: '请输入用户名' }]}>
                <Input placeholder="如: root" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="device_password" label="SSH密码" rules={[{ required: true, message: '请输入密码' }]}>
                <Input.Password placeholder="密码" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="device_path" label="设备路径" rules={[{ required: true, message: '请输入设备路径' }]}>
                <Input placeholder="如: /dev/nvme0n1" />
              </Form.Item>
            </Col>
          </Row>
        </Card>

        {/* FIO基础配置 */}
        <Card title="FIO基础配置" size="small" style={{ marginBottom: 16 }}>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name={['config', 'rw']} label="读写模式" rules={[{ required: true }]} initialValue="randread">
                <Select options={RW_OPTIONS} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name={['config', 'bs']} label="块大小">
                <Input placeholder="如: 4k, 64k, 1m" allowClear />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name={['config', 'size']} label="数据大小">
                <Input placeholder="如: 1G, 10G" allowClear />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name={['config', 'numjobs']} label="并发任务数">
                <InputNumber min={1} max={64} allowClear style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name={['config', 'iodepth']} label="IO深度">
                <InputNumber min={1} max={256} allowClear style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name={['config', 'runtime']} label="运行时间(秒)">
                <InputNumber min={1} allowClear style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name={['config', 'time_based']} valuePropName="checked" initialValue={true}>
            <Checkbox>基于时间完成</Checkbox>
          </Form.Item>
        </Card>

        {/* 高级配置 */}
        <Collapse
          activeKey={advancedExpanded ? ['1'] : []}
          onChange={() => setAdvancedExpanded(!advancedExpanded)}
          style={{ marginBottom: 16 }}
          items={[
            {
              key: '1',
              label: '高级配置',
              children: (
                <Tabs
                  size="small"
                  items={[
                    {
                      key: 'engine',
                      label: 'IO引擎',
                      children: (
                        <>
                          <Form.Item name={['config', 'ioengine']} label="IO引擎">
                            <Select options={IOENGINE_OPTIONS} allowClear placeholder="默认" />
                          </Form.Item>
                          <Form.Item name={['config', 'direct']} valuePropName="checked">
                            <Checkbox>直接IO (O_DIRECT)</Checkbox>
                          </Form.Item>
                          <Form.Item name={['config', 'sync']} valuePropName="checked">
                            <Checkbox>同步IO</Checkbox>
                          </Form.Item>
                        </>
                      ),
                    },
                    {
                      key: 'buffer',
                      label: '缓冲设置',
                      children: (
                        <>
                          <Form.Item name={['config', 'fsync']} label="fsync间隔">
                            <InputNumber min={0} allowClear />
                          </Form.Item>
                          <Form.Item name={['config', 'buffer_pattern']} label="缓冲填充">
                            <Input placeholder="如: 0x00, 0xff" allowClear />
                          </Form.Item>
                        </>
                      ),
                    },
                    {
                      key: 'latency',
                      label: '延迟控制',
                      children: (
                        <>
                          <Form.Item name={['config', 'thinktime']} label="思考时间(ms)">
                            <InputNumber min={0} allowClear />
                          </Form.Item>
                          <Form.Item name={['config', 'latency_target']} label="延迟目标(μs)">
                            <InputNumber min={0} allowClear />
                          </Form.Item>
                        </>
                      ),
                    },
                    {
                      key: 'rate',
                      label: '限速设置',
                      children: (
                        <>
                          <Form.Item name={['config', 'rate']} label="带宽限制(KB/s)">
                            <InputNumber min={0} allowClear />
                          </Form.Item>
                          <Form.Item name={['config', 'rate_iops']} label="IOPS限制">
                            <InputNumber min={0} allowClear />
                          </Form.Item>
                        </>
                      ),
                    },
                    {
                      key: 'verify',
                      label: '数据校验',
                      children: (
                        <>
                          <Form.Item name={['config', 'verify']} label="校验算法">
                            <Select options={VERIFY_OPTIONS} allowClear placeholder="无" />
                          </Form.Item>
                          <Form.Item name={['config', 'verify_fatal']} valuePropName="checked">
                            <Checkbox>校验失败时停止</Checkbox>
                          </Form.Item>
                        </>
                      ),
                    },
                    {
                      key: 'resource',
                      label: 'CPU/内存',
                      children: (
                        <>
                          <Form.Item name={['config', 'cpus_allowed']} label="CPU亲和性">
                            <Input placeholder="如: 0-3, 0,2" allowClear />
                          </Form.Item>
                          <Form.Item name={['config', 'mem']} label="内存分配">
                            <Select options={MEM_OPTIONS} allowClear placeholder="默认" />
                          </Form.Item>
                        </>
                      ),
                    },
                    {
                      key: 'random',
                      label: '随机IO',
                      children: (
                        <>
                          <Form.Item name={['config', 'random_distribution']} label="随机分布">
                            <Select options={RANDOM_DIST_OPTIONS} allowClear placeholder="默认" />
                          </Form.Item>
                          <Form.Item name={['config', 'randseed']} label="随机种子">
                            <InputNumber allowClear />
                          </Form.Item>
                        </>
                      ),
                    },
                    {
                      key: 'mix',
                      label: '混合读写',
                      children: (
                        <>
                          <Form.Item name={['config', 'rwmixread']} label="读比例(%)">
                            <InputNumber min={0} max={100} allowClear />
                          </Form.Item>
                          <Form.Item name={['config', 'rwmixwrite']} label="写比例(%)">
                            <InputNumber min={0} max={100} allowClear />
                          </Form.Item>
                        </>
                      ),
                    },
                    {
                      key: 'other',
                      label: '其他',
                      children: (
                        <>
                          <Form.Item name={['config', 'stats_interval']} label="统计间隔(ms)">
                            <InputNumber min={0} allowClear />
                          </Form.Item>
                          <Form.Item name={['config', 'loops']} label="循环次数">
                            <InputNumber min={1} allowClear />
                          </Form.Item>
                          <Form.Item name={['config', 'startdelay']} label="启动延迟(秒)">
                            <InputNumber min={0} allowClear />
                          </Form.Item>
                        </>
                      ),
                    },
                  ]}
                />
              ),
            },
          ]}
        />

        {/* 故障配置 */}
        <Card title="故障配置（可选）" size="small" style={{ marginBottom: 16 }}>
          <Form.Item name="fault_type" initialValue="none">
            <Select options={FAULT_TYPE_OPTIONS} />
          </Form.Item>
        </Card>

        <div style={{ textAlign: 'right' }}>
          <Space>
            <Button onClick={onClose}>取消</Button>
            <Button type="primary" htmlType="submit" loading={isPending}>
              提交任务
            </Button>
          </Space>
        </div>
      </Form>
    </Modal>
  );
};

export default TaskCreateModal;
