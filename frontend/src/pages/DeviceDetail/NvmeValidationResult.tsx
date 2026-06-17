import React, { useState, useEffect } from 'react';
import { Modal, Table, Tag, Spin, Alert, Space, message } from 'antd';
import { useNvmeValidation, useNvmeValidationResult } from '@/hooks/useNvme';
import type { NvmeCheckItem } from '@/types/nvme';

interface NvmeValidationResultModalProps {
  open: boolean;
  deviceId: number;
  diskName: string;
  testType: 'identify' | 'namespace' | 'smart' | 'error_log' | 'feature' | 'fw_slot';
  onClose: () => void;
}

const testTypeLabels: Record<string, string> = {
  identify: 'Identify 校验',
  namespace: 'Namespace 校验',
  smart: 'SMART 校验',
  error_log: 'Error Log 校验',
  feature: 'Feature 校验',
  fw_slot: 'FW Slot 校验',
};

const verdictColors: Record<string, string> = {
  PASS: 'green',
  PARTIAL: 'orange',
  FAIL: 'red',
};

const NvmeValidationResultModal: React.FC<NvmeValidationResultModalProps> = ({
  open,
  deviceId,
  diskName,
  testType,
  onClose,
}) => {
  const [testId, setTestId] = useState<number | null>(null);
  const [pollEnabled, setPollEnabled] = useState(false);
  const [timedOut, setTimedOut] = useState(false);

  const validationMutation = useNvmeValidation(deviceId, diskName, testType);
  const { data: resultData, isLoading: resultLoading } = useNvmeValidationResult(
    testId || 0,
    pollEnabled && !timedOut,
  );

  useEffect(() => {
    if (open && !testId) {
      validationMutation.mutate(undefined, {
        onSuccess: (resp) => {
          setTestId(resp.test_id);
          setPollEnabled(true);
          setTimedOut(false);
        },
        onError: (err: Error) => {
          message.error(`校验触发失败: ${err.message}`);
        },
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, testId]);

  useEffect(() => {
    if (!open) {
      setTestId(null);
      setPollEnabled(false);
      setTimedOut(false);
    }
  }, [open]);

  // 5min timeout
  useEffect(() => {
    if (!pollEnabled) return;
    const timer = setTimeout(() => setTimedOut(true), 300000);
    return () => clearTimeout(timer);
  }, [pollEnabled]);

  const status = resultData?.status;
  const verdict = resultData?.verdict;
  const checkItems: NvmeCheckItem[] = resultData?.result || [];
  const error = resultData?.error;

  const isLoading = validationMutation.isPending || (pollEnabled && (status === 'pending' || status === 'running'));

  const columns = [
    {
      title: '字段',
      dataIndex: 'field',
      key: 'field',
      width: 200,
    },
    {
      title: '值',
      dataIndex: 'value',
      key: 'value',
      width: 150,
      render: (v: unknown) => (v === null || v === undefined ? '-' : String(v)),
    },
    {
      title: '检查项',
      dataIndex: 'check',
      key: 'check',
      width: 180,
    },
    {
      title: '结果',
      dataIndex: 'pass',
      key: 'pass',
      width: 80,
      render: (pass: boolean, record: NvmeCheckItem) => (
        <Tag color={pass ? 'green' : (record.level === 'warn' ? 'orange' : 'red')}>
          {pass ? 'Pass' : (record.level === 'warn' ? 'Warn' : 'Fail')}
        </Tag>
      ),
    },
    {
      title: '原因',
      dataIndex: 'reason',
      key: 'reason',
    },
  ];

  const renderFwSlotVisualization = () => {
    if (testType !== 'fw_slot' || !checkItems.length) return null;
    const activeSlot = checkItems.find(c => c.field === 'afi.active')?.value;
    const activeNum = activeSlot ? Number(activeSlot) : 0;

    return (
      <div style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {Array.from({ length: 7 }, (_, i) => {
            const slotNum = i + 1;
            const isActive = slotNum === activeNum;
            const versionItem = checkItems.find(c => c.field === `frs[${i}]`);
            const hasVersion = versionItem && versionItem.value;
            const passItem = checkItems.find(c => c.field === `frs[${i}]` && !c.pass);

            let bgColor = '#d9d9d9';
            if (isActive) bgColor = '#52c41a';
            else if (hasVersion) bgColor = '#1890ff';

            return (
              <div
                key={slotNum}
                style={{
                  width: 100,
                  textAlign: 'center',
                  border: `2px solid ${passItem && !passItem.pass ? '#ff4d4f' : bgColor}`,
                  borderRadius: 6,
                  padding: '8px 4px',
                  background: isActive ? '#f6ffed' : (hasVersion ? '#e6f7ff' : '#fafafa'),
                }}
              >
                <div style={{ fontSize: 12, color: '#888' }}>Slot {slotNum}</div>
                <div style={{ fontWeight: 500, fontSize: 13, marginTop: 2 }}>
                  {hasVersion ? String(versionItem!.value) : '(空)'}
                </div>
                {isActive && (
                  <Tag color="green" style={{ marginTop: 4 }}>Active</Tag>
                )}
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  return (
    <Modal
      open={open}
      title={`${testTypeLabels[testType] || testType} - ${diskName}`}
      onCancel={onClose}
      footer={null}
      width={900}
      destroyOnClose
    >
      {isLoading && <Spin tip="校验执行中..." />}
      {timedOut && !resultData && (
        <Alert
          type="warning"
          message="校验超时"
          description="校验执行超过5分钟，请稍后查看结果或重试"
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}
      {error && (
        <Alert
          type="error"
          message="校验失败"
          description={error}
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}
      {status === 'done' && (
        <>
          <Space style={{ marginBottom: 16 }}>
            <span style={{ fontWeight: 500 }}>综合判定：</span>
            {verdict && (
              <Tag color={verdictColors[verdict] || 'default'} style={{ fontSize: 14, padding: '2px 12px' }}>
                {verdict}
              </Tag>
            )}
          </Space>
          {renderFwSlotVisualization()}
          <Table
            dataSource={checkItems}
            columns={columns}
            rowKey="field"
            size="small"
            pagination={false}
          />
        </>
      )}
    </Modal>
  );
};

export default NvmeValidationResultModal;
