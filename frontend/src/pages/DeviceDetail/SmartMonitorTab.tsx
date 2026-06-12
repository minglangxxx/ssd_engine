import React from 'react';
import { Card } from 'antd';
import { useSmartLatest, useSmartAlerts } from '@/hooks/useSmart';
import CriticalAlertList from './CriticalAlertList';
import SmartTrendSection from './SmartTrendSection';

interface SmartMonitorTabProps {
  deviceId: number;
}

const SmartMonitorTab: React.FC<SmartMonitorTabProps> = ({ deviceId }) => {
  const { data: smartLatest } = useSmartLatest(deviceId);
  const { data: alertsData } = useSmartAlerts(deviceId);

  const smartDisks = smartLatest?.disks || [];
  const alerts = alertsData?.alerts || [];

  return (
    <>
      <Card title="临界告警" size="small" style={{ marginBottom: 16 }}>
        <CriticalAlertList alerts={alerts} />
      </Card>
      <SmartTrendSection deviceId={deviceId} disks={smartDisks} />
    </>
  );
};

export default SmartMonitorTab;
