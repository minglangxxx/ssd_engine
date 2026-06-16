import React, { useState } from 'react';
import { Table, Button, Empty, Space, Tag } from 'antd';
import { useNvmeList, type NvmeDetailType } from '@/hooks/useNvme';
import NvmeDetailModal from './NvmeDetailModal';
import FeatureSelectModal from './FeatureSelectModal';
import type { NvmeDeviceInfo } from '@/types/nvme';

interface NvmeListTabProps {
  deviceId: number;
}

const NvmeListTab: React.FC<NvmeListTabProps> = ({ deviceId }) => {
  const { data, isLoading } = useNvmeList(deviceId);
  const disks = data?.disks || [];

  const [modalOpen, setModalOpen] = useState(false);
  const [selectedDisk, setSelectedDisk] = useState('');
  const [modalType, setModalType] = useState<NvmeDetailType>('id-ctrl');
  const [featureFid, setFeatureFid] = useState<string | undefined>(undefined);

  const [featureSelectOpen, setFeatureSelectOpen] = useState(false);
  const [featureSelectDisk, setFeatureSelectDisk] = useState('');

  const openModal = (diskName: string, type: typeof modalType) => {
    setSelectedDisk(diskName);
    setModalType(type);
    if (type !== 'get-feature') {
      setFeatureFid(undefined);
    }
    setModalOpen(true);
  };

  const handleFeatureSelect = (diskName: string, fid: string) => {
    setFeatureSelectOpen(false);
    setSelectedDisk(diskName);
    setModalType('get-feature');
    setFeatureFid(fid);
    setModalOpen(true);
  };

  const columns = [
    {
      title: '磁盘名',
      dataIndex: 'disk_name',
      key: 'disk_name',
      width: 120,
      render: (name: string) => <Tag>{name}</Tag>,
    },
    {
      title: 'Model',
      dataIndex: 'model',
      key: 'model',
      ellipsis: true,
    },
    {
      title: 'SN',
      dataIndex: 'serial_number',
      key: 'serial_number',
      width: 180,
    },
    {
      title: 'Capacity',
      dataIndex: 'capacity_formatted',
      key: 'capacity_formatted',
      width: 120,
    },
    {
      title: 'Firmware',
      dataIndex: 'firmware_version',
      key: 'firmware_version',
      width: 140,
    },
    {
      title: 'NVMe Ver',
      dataIndex: 'nvme_version',
      key: 'nvme_version',
      width: 100,
    },
    {
      title: '操作',
      key: 'actions',
      width: 400,
      render: (_: unknown, record: NvmeDeviceInfo) => (
        <Space size="small">
          <Button size="small" onClick={() => openModal(record.disk_name, 'id-ctrl')}>
            ID-CTRL
          </Button>
          <Button size="small" onClick={() => openModal(record.disk_name, 'id-ns')}>
            ID-NS
          </Button>
          <Button size="small" onClick={() => openModal(record.disk_name, 'smart-log')}>
            SMART-LOG
          </Button>
          <Button size="small" danger onClick={() => openModal(record.disk_name, 'error-log')}>
            ERROR-LOG
          </Button>
          <Button size="small" onClick={() => {
            setFeatureSelectDisk(record.disk_name);
            setFeatureSelectOpen(true);
          }}>
            GET-FEATURE
          </Button>
          <Button size="small" onClick={() => openModal(record.disk_name, 'fw-log')}>
            FW-LOG
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <>
      <Table
        dataSource={disks}
        columns={columns}
        rowKey="disk_name"
        loading={isLoading}
        pagination={false}
        locale={{ emptyText: <Empty description="未检测到 NVMe 设备" /> }}
      />
      <NvmeDetailModal
        open={modalOpen}
        deviceId={deviceId}
        diskName={selectedDisk}
        type={modalType}
        fid={featureFid}
        onClose={() => setModalOpen(false)}
      />
      <FeatureSelectModal
        open={featureSelectOpen}
        diskName={featureSelectDisk}
        onConfirm={handleFeatureSelect}
        onCancel={() => setFeatureSelectOpen(false)}
      />
    </>
  );
};

export default NvmeListTab;
