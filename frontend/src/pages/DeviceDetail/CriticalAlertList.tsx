import React from 'react';
import { Alert, Tag, Empty, Space } from 'antd';
import type { SmartAlert } from '@/types/smart';

interface CriticalAlertListProps {
  alerts: SmartAlert[];
}

const CriticalAlertList: React.FC<CriticalAlertListProps> = ({ alerts }) => {
  if (!alerts || alerts.length === 0) {
    return <Empty description="暂无告警" />;
  }

  // 排序: critical在前，同级别按detected_at倒序
  const sorted = [...alerts].sort((a, b) => {
    if (a.severity !== b.severity) {
      return a.severity === 'critical' ? -1 : 1;
    }
    return (b.detected_at || '').localeCompare(a.detected_at || '');
  });

  return (
    <Space direction="vertical" style={{ width: '100%' }}>
      {sorted.map((alert, index) => (
        <Alert
          key={`${alert.disk_name}-${alert.field}-${index}`}
          type={alert.severity === 'critical' ? 'error' : 'warning'}
          showIcon
          message={
            <Space>
              <Tag color={alert.severity === 'critical' ? 'red' : 'orange'}>{alert.disk_name}</Tag>
              <span>{alert.message}</span>
              <span style={{ color: '#999', fontSize: 12 }}>{alert.detected_at}</span>
            </Space>
          }
        />
      ))}
    </Space>
  );
};

export default CriticalAlertList;