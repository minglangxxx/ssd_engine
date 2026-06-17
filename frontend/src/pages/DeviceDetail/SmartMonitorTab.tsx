import React, { useState } from 'react';
import { Card, Button, Space } from 'antd';
import { useSmartLatest, useSmartAlerts } from '@/hooks/useSmart';
import CriticalAlertList from './CriticalAlertList';
import SmartTrendSection from './SmartTrendSection';
import NvmeValidationResult from './NvmeValidationResult';

interface SmartMonitorTabProps {
  deviceId: number;
}

const SmartMonitorTab: React.FC<SmartMonitorTabProps> = ({ deviceId }) => {
  const { data: smartLatest } = useSmartLatest(deviceId);
  const { data: alertsData } = useSmartAlerts(deviceId);

  const smartDisks = smartLatest?.disks || [];
  const alerts = alertsData?.alerts || [];

  const [validationOpen, setValidationOpen] = useState(false);
  const [validationDisk, setValidationDisk] = useState('');

  const handleValidation = (diskName: string) => {
    setValidationDisk(diskName);
    setValidationOpen(true);
  };

  return (
    <>
      <Card
        title="临界告警"
        size="small"
        style={{ marginBottom: 16 }}
        extra={
          smartDisks.length > 0 && (
            <Space>
              {smartDisks.map(d => (
                <Button key={d.disk_name} size="small" type="primary" onClick={() => handleValidation(d.disk_name)}>
                  校验 {d.disk_name}
                </Button>
              ))}
            </Space>
          )
        }
      >
        <CriticalAlertList alerts={alerts} />
      </Card>
      <SmartTrendSection deviceId={deviceId} disks={smartDisks} />
      <NvmeValidationResult
        open={validationOpen}
        deviceId={deviceId}
        diskName={validationDisk}
        testType="smart"
        onClose={() => setValidationOpen(false)}
      />
    </>
  );
};

export default SmartMonitorTab;
