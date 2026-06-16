import React from 'react';
import { Card, Descriptions, Button, Tag, Row, Col, Empty, Space, message } from 'antd';
import { ApiOutlined, ReloadOutlined } from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { deviceApi } from '@/api/device';
import { useSmartLatest } from '@/hooks/useSmart';
import { formatTime } from '@/utils/format';
import HealthScoreGauge from './HealthScoreGauge';

interface BasicInfoTabProps {
  deviceId: number;
}

const BasicInfoTab: React.FC<BasicInfoTabProps> = ({ deviceId }) => {
  const qc = useQueryClient();

  const { data: deviceInfo, isLoading, refetch } = useQuery({
    queryKey: ['device-info', deviceId],
    queryFn: () => deviceApi.getInfo(deviceId),
    enabled: !!deviceId,
  });

  const { data: smartLatest } = useSmartLatest(deviceId);

  const testMutation = useMutation({
    mutationFn: deviceApi.testConnection,
    onSuccess: async (result) => {
      if (result.success) {
        message.success('连接成功');
        await refetch();
      } else {
        message.error(`连接失败: ${result.message}`);
      }
    },
  });

  if (isLoading || !deviceInfo) {
    return <Card loading />;
  }

  const smartDisks = smartLatest?.disks || [];

  return (
    <>
      <Card title="节点信息" size="small" style={{ marginBottom: 16 }}>
        <Descriptions column={3} size="small">
          <Descriptions.Item label="节点IP">{deviceInfo.ip}</Descriptions.Item>
          <Descriptions.Item label="名称">{deviceInfo.name}</Descriptions.Item>
          <Descriptions.Item label="Agent端口">{deviceInfo.agent_port}</Descriptions.Item>
          <Descriptions.Item label="磁盘列表">
            {deviceInfo.disks?.map((d) => d.name || d.device).join(', ') || '-'}
          </Descriptions.Item>
          <Descriptions.Item label="版本">{deviceInfo.agent_version}</Descriptions.Item>
          <Descriptions.Item label="最后心跳">{deviceInfo.last_heartbeat ? formatTime(deviceInfo.last_heartbeat) : '-'}</Descriptions.Item>
          <Descriptions.Item label="状态">
            <Tag color={deviceInfo.agent_status === 'online' ? 'green' : 'red'}>
              {deviceInfo.agent_status}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="主机名">{deviceInfo.hostname || '--'}</Descriptions.Item>
          <Descriptions.Item label="操作系统">{deviceInfo.os_version || '--'}</Descriptions.Item>
          <Descriptions.Item label="内核版本">{deviceInfo.kernel_version || '--'}</Descriptions.Item>
          <Descriptions.Item label="CPU 使用率">
            {deviceInfo.cpu_usage !== null && deviceInfo.cpu_usage !== undefined ? `${deviceInfo.cpu_usage}%` : '--'}
          </Descriptions.Item>
          <Descriptions.Item label="内存使用率">
            {deviceInfo.memory_usage !== null && deviceInfo.memory_usage !== undefined ? `${deviceInfo.memory_usage}%` : '--'}
          </Descriptions.Item>
        </Descriptions>
        <Space style={{ marginTop: 12 }}>
          <Button
            icon={<ReloadOutlined />}
            onClick={() => {
              refetch();
              qc.invalidateQueries({ queryKey: ['smart-latest', deviceId] });
              qc.invalidateQueries({ queryKey: ['smart-alerts', deviceId] });
            }}
          >
            刷新数据
          </Button>
          <Button
            icon={<ApiOutlined />}
            loading={testMutation.isPending}
            onClick={() =>
              testMutation.mutate({
                ip: deviceInfo.ip,
                user: '',
                password: '',
              })
            }
          >
            测试连接
          </Button>
        </Space>
      </Card>

      <Card title="NVMe 健康评分" size="small">
        {smartDisks.length > 0 ? (
          <Row gutter={[16, 16]}>
            {smartDisks.map((disk) => (
              <Col key={disk.disk_name} span={smartDisks.length <= 2 ? 12 : 8}>
                <HealthScoreGauge
                  diskName={disk.disk_name}
                  score={disk.health_score}
                  level={disk.health_level}
                  details={disk.health_details}
                />
              </Col>
            ))}
          </Row>
        ) : (
          <Empty description="暂无 SMART 数据" />
        )}
      </Card>
    </>
  );
};

export default BasicInfoTab;
