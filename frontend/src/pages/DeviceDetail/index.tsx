import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, Descriptions, Button, Tag, Space, Row, Col, Spin, Empty } from 'antd';
import { ArrowLeftOutlined, ApiOutlined, ReloadOutlined } from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { deviceApi } from '@/api/device';
import { useSmartLatest, useSmartAlerts } from '@/hooks/useSmart';
import { formatTime } from '@/utils/format';
import HealthScoreGauge from './HealthScoreGauge';
import CriticalAlertList from './CriticalAlertList';
import SmartTrendSection from './SmartTrendSection';
import { message } from 'antd';

const DeviceDetail: React.FC = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const deviceId = Number(id);

  const { data: deviceInfo, isLoading, refetch } = useQuery({
    queryKey: ['device-info', deviceId],
    queryFn: () => deviceApi.getInfo(deviceId),
    enabled: !!deviceId,
  });

  const { data: smartLatest } = useSmartLatest(deviceId);
  const { data: alertsData } = useSmartAlerts(deviceId);

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
    return <Card loading><Spin /></Card>;
  }

  const smartDisks = smartLatest?.disks || [];
  const alerts = alertsData?.alerts || [];

  return (
    <div>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/devices')}>
            返回列表
          </Button>
          <h2 style={{ margin: 0 }}>设备详情 - {deviceInfo.ip}</h2>
        </Space>
        <Tag color={deviceInfo.agent_status === 'online' ? 'green' : 'red'}>
          {deviceInfo.agent_status === 'online' ? '在线' : '离线'}
        </Tag>
      </div>

      {/* 基本信息 Card */}
      <Card title="基本信息" size="small" style={{ marginBottom: 16 }}>
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
        </Descriptions>
        <Space style={{ marginTop: 12 }}>
          <Button
            icon={<ReloadOutlined />}
            onClick={() => { refetch(); qc.invalidateQueries({ queryKey: ['smart-latest', deviceId] }); qc.invalidateQueries({ queryKey: ['smart-alerts', deviceId] }); }}
          >
            刷新数据
          </Button>
          <Button
            icon={<ApiOutlined />}
            loading={testMutation.isPending}
            onClick={() =>
              testMutation.mutate({
                ip: deviceInfo.ip,
                user: 'root',
                password: '',
              })
            }
          >
            测试连接
          </Button>
        </Space>
      </Card>

      {/* NVMe 健康评分 Card */}
      <Card title="NVMe 健康评分" size="small" style={{ marginBottom: 16 }}>
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

      {/* 临界告警 Card */}
      <Card title="临界告警" size="small" style={{ marginBottom: 16 }}>
        <CriticalAlertList alerts={alerts} />
      </Card>

      {/* SMART 历史趋势 Card */}
      <SmartTrendSection deviceId={deviceId} disks={smartDisks} />
    </div>
  );
};

export default DeviceDetail;