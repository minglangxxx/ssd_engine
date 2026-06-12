import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Button, Space, Tabs, Tag } from 'antd';
import { ArrowLeftOutlined } from '@ant-design/icons';
import BasicInfoTab from './BasicInfoTab';
import NvmeListTab from './NvmeListTab';
import SmartMonitorTab from './SmartMonitorTab';

const DeviceDetail: React.FC = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const deviceId = Number(id);
  const [activeTab, setActiveTab] = useState('basic');

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/devices')}>
            返回列表
          </Button>
          <h2 style={{ margin: 0 }}>设备详情</h2>
        </Space>
      </div>

      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={[
          {
            key: 'basic',
            label: '基本信息',
            children: <BasicInfoTab deviceId={deviceId} />,
          },
          {
            key: 'nvme',
            label: 'NVMe列表',
            children: <NvmeListTab deviceId={deviceId} />,
          },
          {
            key: 'smart',
            label: 'SMART监控',
            children: <SmartMonitorTab deviceId={deviceId} />,
          },
        ]}
      />
    </div>
  );
};

export default DeviceDetail;
