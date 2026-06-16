import React, { useState } from 'react';
import { Modal, Select, Form, Input } from 'antd';

const PRESET_FEATURES = [
  { value: '0x01', label: '0x01 Arbitration' },
  { value: '0x02', label: '0x02 Power Management' },
  { value: '0x04', label: '0x04 Temperature Threshold' },
  { value: '0x06', label: '0x06 Write Cache' },
  { value: '0x07', label: '0x07 Number of Queues' },
  { value: '0x08', label: '0x08 Interrupt Coalescing' },
  { value: '0x09', label: '0x09 Interrupt Vector Config' },
  { value: '0x0A', label: '0x0A Write Atomicity' },
  { value: '0x0C', label: '0x0C Asymmetric Access' },
  { value: '0x0D', label: '0x0D Software Progress Marker' },
];

interface FeatureSelectModalProps {
  open: boolean;
  diskName: string;
  onConfirm: (diskName: string, fid: string) => void;
  onCancel: () => void;
}

const FeatureSelectModal: React.FC<FeatureSelectModalProps> = ({
  open,
  diskName,
  onConfirm,
  onCancel,
}) => {
  const [form] = Form.useForm();
  const [mode, setMode] = useState<'preset' | 'custom'>('preset');

  const handleOk = () => {
    const fid = form.getFieldValue('fid_preset') || form.getFieldValue('fid_custom');
    if (fid) {
      onConfirm(diskName, fid);
      form.resetFields();
      setMode('preset');
    }
  };

  const handleCancel = () => {
    onCancel();
    form.resetFields();
    setMode('preset');
  };

  return (
    <Modal
      open={open}
      title={`GET-FEATURE - ${diskName}`}
      onOk={handleOk}
      onCancel={handleCancel}
      okText="查询"
      cancelText="取消"
      destroyOnClose
      width={420}
    >
      <Form form={form} layout="vertical" initialValues={{ fid_preset: '0x06' }}>
        <Form.Item label="Feature ID">
          <Select
            value={mode}
            onChange={(v) => setMode(v as 'preset' | 'custom')}
            style={{ width: 120, marginBottom: 8 }}
            options={[
              { value: 'preset', label: '预设列表' },
              { value: 'custom', label: '手动输入' },
            ]}
          />
        </Form.Item>
        {mode === 'preset' ? (
          <Form.Item name="fid_preset" rules={[{ required: true, message: '请选择 Feature ID' }]}>
            <Select options={PRESET_FEATURES} placeholder="选择 Feature ID" />
          </Form.Item>
        ) : (
          <Form.Item
            name="fid_custom"
            rules={[
              { required: true, message: '请输入 Feature ID' },
              { pattern: /^0x[0-9a-fA-F]{1,4}$/, message: '格式: 0x01 ~ 0x0FFF' },
            ]}
          >
            <Input placeholder="如 0x06" />
          </Form.Item>
        )}
      </Form>
    </Modal>
  );
};

export default FeatureSelectModal;
