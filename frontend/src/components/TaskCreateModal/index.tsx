import React, { useEffect, useState } from 'react';
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
  Alert,
  Typography,
  Divider,
  Tag,
  Radio,
} from 'antd';
import { useQuery } from '@tanstack/react-query';
import { useCreateTask } from '@/hooks/useTask';
import { buildFioConfig, type FioConfig } from '@/types/task';
import { deviceApi } from '@/api/device';
import {
  RW_OPTIONS,
  IOENGINE_OPTIONS,
  VERIFY_OPTIONS,
  MEM_OPTIONS,
  RANDOM_DIST_OPTIONS,
  FAULT_TYPE_OPTIONS,
  TASK_TEMPLATE_OPTIONS,
  TASK_TEMPLATE_PRESETS,
} from '@/utils/constants';
import type { Device, DeviceDisk } from '@/types/device';

type TaskTemplateKey = keyof typeof TASK_TEMPLATE_PRESETS | 'custom';

const DEFAULT_TEMPLATE: TaskTemplateKey = 'custom';

const DEFAULT_CONFIG: Partial<FioConfig> = {};

const RAW_COMMAND_PLACEHOLDER = 'fio --rw=randread --bs=4k --iodepth=32 --numjobs=4 --runtime=60 --time_based=1 --direct=1';

const templateHintMap: Record<TaskTemplateKey, string> = {
  'randread-latency': '适合看 4k 低队列深度场景的读延迟表现。',
  'randwrite-pressure': '适合观察高并发随机写压力下的稳定性和尾延迟。',
  'seqread-throughput': '适合测顺序读取带宽上限。',
  'seqwrite-throughput': '适合测顺序写入吞吐能力。',
  'mixed-7030': '适合数据库类读多写少混合负载。',
  'steady-state': '适合观察较长时间写压后的稳态表现。',
  custom: '完全手工指定 fio 参数，适合熟悉 fio 的用户。',
};

interface TaskCreateModalProps {
  visible: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

const TaskCreateModal: React.FC<TaskCreateModalProps> = ({ visible, onClose, onSuccess }) => {
  const [form] = Form.useForm();
  const { mutateAsync: createTask, isPending } = useCreateTask();
  const [advancedExpanded, setAdvancedExpanded] = useState(false);
  const selectedDeviceIp = Form.useWatch('device_ip', form);
  const inputMode = (Form.useWatch('input_mode', form) as 'guided' | 'native' | undefined) || 'guided';
  const selectedTemplate = (Form.useWatch('template', form) as TaskTemplateKey | undefined) || DEFAULT_TEMPLATE;
  const selectedConfig = (Form.useWatch(['config'], form) as Partial<FioConfig> | undefined) || DEFAULT_CONFIG;
  const selectedRw = Form.useWatch(['config', 'rw'], form) as FioConfig['rw'] | undefined;

  const { data: devices, isLoading: devicesLoading } = useQuery({
    queryKey: ['devices'],
    queryFn: () => deviceApi.list(),
    enabled: visible,
  });

  const selectedDevice = devices?.find((device) => device.ip === selectedDeviceIp);
  const { data: selectedDeviceInfo, isFetching: disksLoading } = useQuery({
    queryKey: ['device-info', selectedDevice?.id],
    queryFn: () => deviceApi.getInfo(selectedDevice!.id),
    enabled: visible && !!selectedDevice?.id,
  });

  useEffect(() => {
    if (!visible || !devices?.length) {
      return;
    }

    const hasSelectedDevice = devices.some((device) => device.ip === selectedDeviceIp);
    if (!selectedDeviceIp || !hasSelectedDevice) {
      form.setFieldValue('device_ip', devices[0].ip);
    }
  }, [devices, form, selectedDeviceIp, visible]);

  useEffect(() => {
    if (!visible) {
      return;
    }

    const currentPath = form.getFieldValue('device_path');
    if (!currentPath) {
      return;
    }

    if (!selectedDeviceInfo?.disks?.length || !selectedDeviceInfo.disks.some((disk) => disk.device === currentPath)) {
      form.setFieldValue('device_path', undefined);
    }
  }, [form, selectedDeviceInfo, visible]);

  useEffect(() => {
    if (!visible || inputMode !== 'guided' || selectedTemplate === 'custom') {
      return;
    }

    const preset = TASK_TEMPLATE_PRESETS[selectedTemplate];
    form.setFieldsValue({
      config: {
        ...DEFAULT_CONFIG,
        ...form.getFieldValue('config'),
        ...preset,
      },
    });
  }, [form, selectedTemplate, visible]);

  const hostOptions = (devices || []).map((device: Device) => ({
    value: device.ip,
    label: `${device.name} (${device.ip})`,
  }));

  const diskOptions = (selectedDeviceInfo?.disks || []).map((disk: DeviceDisk) => ({
    value: disk.device,
    label: disk.device === disk.name ? disk.name : `${disk.name} (${disk.device})`,
  }));

  const configSummary = [
    `模式 ${selectedConfig.rw || 'fio 默认'}`,
    `块大小 ${selectedConfig.bs || 'fio 默认'}`,
    `并发 ${selectedConfig.numjobs ?? 'fio 默认'}`,
    `队列 ${selectedConfig.iodepth ?? 'fio 默认'}`,
    selectedConfig.time_based === true
      ? `按时间 ${selectedConfig.runtime ?? 'fio 默认'}s`
      : selectedConfig.time_based === false
        ? `按数据量 ${selectedConfig.size || 'fio 默认'}`
        : '运行条件 fio 默认',
    selectedConfig.direct == null ? 'direct fio 默认' : `direct ${selectedConfig.direct ? 'on' : 'off'}`,
  ].join(' / ');

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      const fioConfig = buildFioConfig(values.config || {});
      await createTask({
        name: values.name,
        device_ip: values.device_ip,
        device_path: values.device_path,
        config: values.input_mode === 'native' ? {} : fioConfig,
        fio_command: values.input_mode === 'native' ? values.fio_command : undefined,
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
      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
        initialValues={{
          input_mode: 'guided',
          template: DEFAULT_TEMPLATE,
          fault_type: 'none',
          config: {},
        }}
      >
        {/* 任务名称 */}
        <Form.Item name="name" label="任务名称">
          <Input placeholder="可选，不填则自动生成" allowClear />
        </Form.Item>

        <Card title="设备与测试目标" size="small" style={{ marginBottom: 16 }}>
          <Row gutter={16}>
            <Col span={24}>
              <Form.Item name="input_mode" label="配置方式">
                <Radio.Group optionType="button" buttonStyle="solid">
                  <Radio.Button value="guided">引导配置</Radio.Button>
                  <Radio.Button value="native">原生命令</Radio.Button>
                </Radio.Group>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="device_ip" label="设备节点" rules={[{ required: true, message: '请选择设备节点' }]}>
                <Select
                  options={hostOptions}
                  placeholder="选择已接入的设备节点"
                  loading={devicesLoading}
                  showSearch
                  optionFilterProp="label"
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="fault_type" label="故障注入" initialValue="none">
                <Select options={FAULT_TYPE_OPTIONS} />
              </Form.Item>
            </Col>
            {inputMode === 'guided' && (
              <Col span={12}>
                <Form.Item name="template" label="测试模板">
                  <Select options={TASK_TEMPLATE_OPTIONS} />
                </Form.Item>
              </Col>
            )}
            <Col span={12}>
              <Form.Item name="device_path" label="设备路径" rules={[{ required: true, message: '请选择设备路径' }]}>
                {diskOptions.length > 0 ? (
                  <Select
                    options={diskOptions}
                    placeholder="选择磁盘设备"
                    loading={disksLoading}
                    showSearch
                    optionFilterProp="label"
                  />
                ) : (
                  <Input placeholder="Agent 未返回磁盘列表时可手动输入，如 /dev/nvme0n1" />
                )}
              </Form.Item>
            </Col>
            <Col span={12}>
              <Typography.Text type="secondary">
                {inputMode === 'native' ? '可直接输入 fio 原生命令；平台会统一接管 filename、name、output-format 等托管参数。' : templateHintMap[selectedTemplate]}
              </Typography.Text>
              <div style={{ marginTop: 8 }}>
                {selectedDevice && <Tag color={selectedDevice.agent_status === 'online' ? 'green' : 'red'}>{selectedDevice.agent_status === 'online' ? 'Agent在线' : 'Agent离线'}</Tag>}
                {selectedDeviceInfo?.disks?.length ? <Tag color="blue">磁盘 {selectedDeviceInfo.disks.length} 块</Tag> : null}
              </div>
            </Col>
          </Row>
        </Card>

        {inputMode === 'native' ? (
          <Card title="原生 fio 命令" size="small" style={{ marginBottom: 16 }}>
            <Form.Item
              name="fio_command"
              label="fio 标准命令"
              rules={[{ required: true, message: '请输入 fio 标准命令' }]}
              extra="支持 fio --rw=randread --bs=4k 这类标准 CLI 形式；device_path 仍由上方设备路径统一指定。"
            >
              <Input.TextArea rows={6} placeholder={RAW_COMMAND_PLACEHOLDER} />
            </Form.Item>
            <Alert
              type="info"
              showIcon
              message="命令要求"
              description="支持 --key=value 和 --key value 两种写法。filename、name、output-format、group_reporting、status-interval 由平台统一接管。"
            />
          </Card>
        ) : (
        <Card title="核心配置" size="small" style={{ marginBottom: 16 }}>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name={['config', 'rw']} label="读写模式" rules={[{ required: true, message: '请选择读写模式' }]}>
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
                <InputNumber min={1} max={64} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name={['config', 'iodepth']} label="IO深度">
                <InputNumber min={1} max={256} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name={['config', 'runtime']} label="运行时间(秒)">
                <InputNumber min={1} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            {selectedRw === 'randrw' && (
              <>
                <Col span={12}>
                  <Form.Item name={['config', 'rwmixread']} label="读比例(%)">
                    <InputNumber min={0} max={100} style={{ width: '100%' }} />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item name={['config', 'rwmixwrite']} label="写比例(%)">
                    <InputNumber min={0} max={100} style={{ width: '100%' }} />
                  </Form.Item>
                </Col>
              </>
            )}
          </Row>
          <Form.Item name={['config', 'time_based']} valuePropName="checked">
            <Checkbox>基于时间完成</Checkbox>
          </Form.Item>
          <Alert
            type="info"
            showIcon
            message="当前测试摘要"
            description={`仅会提交你显式填写或通过模板带入的参数。${configSummary}`}
          />
        </Card>
        )}

        {/* 高级配置 */}
        {inputMode === 'guided' && <Collapse
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
                            <InputNumber min={0} />
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
                            <InputNumber min={0} />
                          </Form.Item>
                          <Form.Item name={['config', 'latency_target']} label="延迟目标(μs)">
                            <InputNumber min={0} />
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
                            <InputNumber min={0} />
                          </Form.Item>
                          <Form.Item name={['config', 'rate_iops']} label="IOPS限制">
                            <InputNumber min={0} />
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
                            <InputNumber />
                          </Form.Item>
                        </>
                      ),
                    },
                    {
                      key: 'mix',
                      label: '混合读写',
                      disabled: selectedRw !== 'randrw',
                      children: (
                        <>
                          <Form.Item name={['config', 'rwmixread']} label="读比例(%)">
                            <InputNumber min={0} max={100} />
                          </Form.Item>
                          <Form.Item name={['config', 'rwmixwrite']} label="写比例(%)">
                            <InputNumber min={0} max={100} />
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
                            <InputNumber min={0} />
                          </Form.Item>
                          <Form.Item name={['config', 'loops']} label="循环次数">
                            <InputNumber min={1} />
                          </Form.Item>
                          <Form.Item name={['config', 'startdelay']} label="启动延迟(秒)">
                            <InputNumber min={0} />
                          </Form.Item>
                        </>
                      ),
                    },
                  ]}
                />
              ),
            },
          ]}
        />}

        <Divider style={{ margin: '16px 0' }} />

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
