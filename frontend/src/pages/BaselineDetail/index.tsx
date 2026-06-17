import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, Descriptions, Row, Col, Statistic, Button, Space } from 'antd';
import { ArrowLeftOutlined } from '@ant-design/icons';
import { useBaselineDetail } from '@/hooks/useBaseline';
import { formatTime, formatNumber } from '@/utils/format';

const BaselineDetail: React.FC = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const baselineId = Number(id);
  const { data: baseline, isLoading } = useBaselineDetail(baselineId);

  if (isLoading || !baseline) {
    return <Card loading={isLoading}>加载中...</Card>;
  }

  const result = baseline.result;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/baselines')}>
            返回列表
          </Button>
          <h2 style={{ margin: 0 }}>基线详情 - {baseline.name}</h2>
        </Space>
      </div>

      <Card title="基本信息" size="small" style={{ marginBottom: 16 }}>
        <Descriptions column={3} size="small">
          <Descriptions.Item label="基线ID">{baseline.id}</Descriptions.Item>
          <Descriptions.Item label="名称">{baseline.name}</Descriptions.Item>
          <Descriptions.Item label="创建者">{baseline.created_by}</Descriptions.Item>
          <Descriptions.Item label="设备型号">{baseline.device_model || '-'}</Descriptions.Item>
          <Descriptions.Item label="固件版本">{baseline.firmware || '-'}</Descriptions.Item>
          <Descriptions.Item label="创建时间">{formatTime(baseline.created_at)}</Descriptions.Item>
          <Descriptions.Item label="设备IP">{baseline.device_ip}</Descriptions.Item>
          <Descriptions.Item label="设备路径">{baseline.device_path}</Descriptions.Item>
          <Descriptions.Item label="来源任务">
            <Button type="link" size="small" onClick={() => navigate(`/tasks/${baseline.source_task_id}`)}>
              任务 #{baseline.source_task_id}
            </Button>
          </Descriptions.Item>
        </Descriptions>
      </Card>

      <Card title="FIO 配置" size="small" style={{ marginBottom: 16 }}>
        <Descriptions column={4} size="small">
          <Descriptions.Item label="读写模式">{baseline.fio_config?.rw}</Descriptions.Item>
          <Descriptions.Item label="块大小">{baseline.fio_config?.bs || '4k'}</Descriptions.Item>
          <Descriptions.Item label="IO深度">{baseline.fio_config?.iodepth || 32}</Descriptions.Item>
          <Descriptions.Item label="运行时间">{baseline.fio_config?.runtime ? `${baseline.fio_config.runtime}s` : '-'}</Descriptions.Item>
        </Descriptions>
      </Card>

      {result && (
        <Card title="基线结果" size="small" style={{ marginBottom: 16 }}>
          <Row gutter={16}>
            <Col span={6}>
              <Statistic title="IOPS" value={result.iops} formatter={(v) => formatNumber(v as number)} />
            </Col>
            <Col span={6}>
              <Statistic title="带宽 (MB/s)" value={result.bandwidth} formatter={(v) => formatNumber(v as number)} />
            </Col>
            <Col span={6}>
              <Statistic title="平均延迟 (μs)" value={result.latency?.mean} precision={1} />
            </Col>
            <Col span={6}>
              <Statistic title="P99 延迟 (μs)" value={result.latency?.p99} precision={1} />
            </Col>
          </Row>
        </Card>
      )}
    </div>
  );
};

export default BaselineDetail;
