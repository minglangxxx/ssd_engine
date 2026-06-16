import React, { useMemo } from 'react';
import { Modal, Descriptions, Table, Spin, Alert, Empty, Tag } from 'antd';
import { useNvmeDetail, type NvmeDetailType } from '@/hooks/useNvme';
import type { SmartDiskSnapshot } from '@/types/smart';
import type { NvmeFeatureResponse, NvmeFwLogResponse } from '@/types/nvme';

interface NvmeDetailModalProps {
  open: boolean;
  deviceId: number;
  diskName: string;
  type: NvmeDetailType;
  fid?: string;
  onClose: () => void;
}

const idCtrlTopKeys = [
  { key: 'sn', label: 'SN (序列号)' },
  { key: 'mn', label: 'MN (型号)' },
  { key: 'fr', label: 'FR (固件版本)' },
  { key: 'vid', label: 'VID (厂商ID)' },
  { key: 'nvme_version', label: 'NVMe 版本' },
  { key: 'tnvmcap', label: '总容量 (tnvmcap)' },
  { key: 'mdts', label: 'MDTS' },
  { key: 'oacs', label: 'OACS' },
  { key: 'frmw', label: 'FRMW' },
  { key: 'lpa', label: 'LPA' },
  { key: 'elpe', label: 'ELPE' },
  { key: 'cntlid', label: 'CNTLID' },
  { key: 'ver', label: 'VER' },
  { key: 'rab', label: 'RAB' },
  { key: 'ieee', label: 'IEEE' },
  { key: 'cmic', label: 'CMIC' },
];

const NvmeDetailModal: React.FC<NvmeDetailModalProps> = ({
  open,
  deviceId,
  diskName,
  type,
  fid,
  onClose,
}) => {
  const { data: nvmeData, isLoading, error } = useNvmeDetail(deviceId, diskName, type, fid);

  const smartDisk = useMemo(() => {
    if (type !== 'smart-log' || !nvmeData?.disks) return null;
    return nvmeData.disks.find((d: SmartDiskSnapshot) => d.disk_name === diskName) || null;
  }, [nvmeData, diskName, type]);

  const titleMap: Record<string, string> = {
    'id-ctrl': `NVMe ID-CTRL - ${diskName}`,
    'id-ns': `NVMe ID-NS - ${diskName}`,
    'error-log': `NVMe ERROR-LOG - ${diskName}`,
    'smart-log': `NVMe SMART-LOG - ${diskName}`,
    'get-feature': `NVMe GET-FEATURE - ${diskName}`,
    'fw-log': `NVMe FW-LOG - ${diskName}`,
  };

  const renderIdCtrl = () => {
    const data = (nvmeData as { data?: Record<string, unknown> })?.data;
    if (!data) return <Empty description="无数据" />;
    const topEntries = idCtrlTopKeys
      .filter((k) => data[k.key] !== undefined && data[k.key] !== null && data[k.key] !== '')
      .map((k) => ({ key: k.key, label: k.label, value: String(data[k.key]) }));
    const allKeys = Object.keys(data).filter(
      (k) => !idCtrlTopKeys.some((tk) => tk.key === k),
    );
    return (
      <>
        {topEntries.length > 0 && (
          <Descriptions
            bordered
            column={2}
            size="small"
            style={{ marginBottom: 16 }}
          >
            {topEntries.map((e) => (
              <Descriptions.Item key={e.key} label={e.label}>
                {e.value}
              </Descriptions.Item>
            ))}
          </Descriptions>
        )}
        {allKeys.length > 0 && (
          <Table
            dataSource={allKeys.map((k) => ({ key: k, field: k, value: String(data[k]) }))}
            columns={[
              { title: '字段', dataIndex: 'field', width: 250 },
              { title: '值', dataIndex: 'value' },
            ]}
            rowKey="key"
            size="small"
            pagination={{ pageSize: 20 }}
          />
        )}
      </>
    );
  };

  const renderKvDescriptions = (data: Record<string, unknown> | undefined, emptyText: string, column = 2, style?: React.CSSProperties) => {
    if (!data) return <Empty description={emptyText} />;
    const entries = Object.entries(data).filter(
      ([, v]) => v !== undefined && v !== null && v !== '',
    );
    return (
      <Descriptions bordered column={column} size="small" style={style}>
        {entries.map(([k, v]) => (
          <Descriptions.Item key={k} label={k}>
            {typeof v === 'object' ? JSON.stringify(v) : String(v)}
          </Descriptions.Item>
        ))}
      </Descriptions>
    );
  };

  const renderIdNs = () => {
    const data = (nvmeData as { data?: Record<string, unknown> })?.data;
    if (!data) return <Empty description="无数据" />;
    const lbaf = Array.isArray(data.lbaf) ? data.lbaf : [];
    const { lbaf: _lbaf, ...rest } = data;
    return (
      <>
        {renderKvDescriptions(rest, '无数据', 2, { marginBottom: 16 })}
        {lbaf.length > 0 && (
          <Table
            dataSource={lbaf.map((item: Record<string, unknown>, idx: number) => ({
              key: idx,
              index: idx,
              ms: item.ms,
              ds: item.ds,
              rp: item.rp,
            }))}
            columns={[
              { title: 'Index', dataIndex: 'index', width: 80 },
              { title: 'MS (Metadata Size)', dataIndex: 'ms' },
              { title: 'DS (Data Size, 2^N)', dataIndex: 'ds' },
              { title: 'RP (Relative Performance)', dataIndex: 'rp' },
            ]}
            size="small"
            pagination={false}
          />
        )}
      </>
    );
  };

  const renderErrorLog = () => {
    const data = (nvmeData as { data?: Record<string, unknown> })?.data;
    const entries = (data?.error_log_entries || []) as Array<Record<string, unknown>>;
    if (!entries || entries.length === 0) return <Empty description="无错误日志" />;
    const columns = [
      { title: 'error_count', dataIndex: 'error_count', width: 120 },
      { title: 'sqid', dataIndex: 'sqid', width: 80 },
      { title: 'cmdid', dataIndex: 'cmdid', width: 80 },
      { title: 'status_field', dataIndex: 'status_field', width: 120 },
      { title: 'parm_err_loc', dataIndex: 'parm_err_loc', width: 140 },
      { title: 'lba', dataIndex: 'lba', width: 150 },
      { title: 'nsid', dataIndex: 'nsid', width: 80 },
    ];
    return (
      <Table
        dataSource={entries.map((e, idx) => ({ ...e, key: idx }))}
        columns={columns}
        size="small"
        pagination={entries.length > 20 ? { pageSize: 20 } : false}
      />
    );
  };

  const renderSmartLog = () => {
    if (!smartDisk) return <Empty description="无 SMART 数据" />;
    const fields = [
      { label: '温度', value: `${smartDisk.temperature}°C` },
      { label: '磨损百分比', value: `${smartDisk.percentage_used}%` },
      { label: '通电时长', value: `${smartDisk.power_on_hours} 小时` },
      { label: '通电次数', value: String(smartDisk.power_cycles) },
      { label: '介质错误数', value: String(smartDisk.media_errors) },
      { label: '临界警告', value: String(smartDisk.critical_warning) },
      { label: '数据读取量', value: `${((smartDisk.data_units_read * 512) / (1024 ** 3)).toFixed(2)} GB` },
      { label: '数据写入量', value: `${((smartDisk.data_units_written * 512) / (1024 ** 3)).toFixed(2)} GB` },
      { label: '可用备用空间', value: smartDisk.available_spare != null ? `${smartDisk.available_spare}%` : '-' },
      { label: '健康评分', value: `${smartDisk.health_score} (${smartDisk.health_level})` },
      { label: '事件时间', value: smartDisk.event_time || '-' },
    ];
    return (
      <Descriptions bordered column={2} size="small">
        {fields.map((f) => (
          <Descriptions.Item key={f.label} label={f.label}>
            {f.value}
          </Descriptions.Item>
        ))}
      </Descriptions>
    );
  };

  const renderGetFeature = () => {
    const data = (nvmeData as NvmeFeatureResponse | null)?.data;
    return renderKvDescriptions(data, '无 Feature 数据');
  };

  const renderFwLog = () => {
    const resp = nvmeData as NvmeFwLogResponse | null;
    const data = resp?.data;
    if (!data) return <Empty description="无固件日志" />;
    const activeSlot = Number(data.afi?.active ?? 0) || 0;
    const frs = Array.isArray(data.frs) ? data.frs.map(String) : [];

    const slots = Array.from({ length: 7 }, (_, i) => {
      const slotNum = i + 1;
      const fw = (frs[i] || '').trim();
      const isActive = slotNum === activeSlot;
      return { slotNum, fw, isActive };
    });

    return (
      <>
        <Descriptions bordered column={1} size="small" style={{ marginBottom: 16 }}>
          <Descriptions.Item label="当前激活槽">Slot {activeSlot}</Descriptions.Item>
        </Descriptions>
        <Table
          dataSource={slots}
          rowKey="slotNum"
          size="small"
          pagination={false}
          columns={[
            { title: 'Slot', dataIndex: 'slotNum', width: 80 },
            {
              title: '固件版本',
              dataIndex: 'fw',
              render: (fw: string) => fw || '(空)',
            },
            {
              title: '状态',
              dataIndex: 'isActive',
              width: 100,
              render: (active: boolean) =>
                active ? <Tag color="green">Active</Tag> : <Tag>空闲</Tag>,
            },
          ]}
        />
      </>
    );
  };

  const renderContent = () => {
    if (isLoading) return <Spin />;
    if (error) return <Alert type="error" message={`请求失败: ${error.message}`} showIcon />;
    switch (type) {
      case 'id-ctrl': return renderIdCtrl();
      case 'id-ns': return renderIdNs();
      case 'error-log': return renderErrorLog();
      case 'smart-log': return renderSmartLog();
      case 'get-feature': return renderGetFeature();
      case 'fw-log': return renderFwLog();
      default: return <Empty description="未知类型" />;
    }
  };

  return (
    <Modal
      open={open}
      title={titleMap[type]}
      onCancel={onClose}
      footer={null}
      width={800}
      destroyOnClose
    >
      {renderContent()}
    </Modal>
  );
};

export default NvmeDetailModal;
