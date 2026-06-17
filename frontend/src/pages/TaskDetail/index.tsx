import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, Row, Col, Statistic, Descriptions, Button, Tag, Space, Modal, Input, message } from 'antd';
import { ArrowLeftOutlined, SaveOutlined } from '@ant-design/icons';
import { useTaskDetail } from '@/hooks/useTask';
import { usePolling } from '@/hooks/usePolling';
import { useCreateBaseline } from '@/hooks/useBaseline';
import TaskStatusBadge from '@/components/TaskStatusBadge/index';
import FioTrendSection from './FioTrendSection';
import AiAnalysisSection from '@/components/AiAnalysisPanel/index';
import { formatTime, formatDuration, formatNumber, formatBytes } from '@/utils/format';
import { buildFioCommand } from '@/types/task';

const TaskDetail: React.FC = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const taskId = Number(id);
  const { data: task, isLoading, refetch } = useTaskDetail(taskId);
  const isRunning = task?.status === 'RUNNING';

  const [baselineModalVisible, setBaselineModalVisible] = useState(false);
  const [baselineForm, setBaselineForm] = useState({ name: '', device_model: '', firmware: '' });
  const { mutate: createBaseline, isPending: creatingBaseline } = useCreateBaseline();

  usePolling({ fn: () => refetch(), enabled: isRunning, interval: 3000 });

  const handleCreateBaseline = () => {
    if (!baselineForm.name.trim()) {
      message.warning('请输入基线名称');
      return;
    }
    createBaseline(
      { task_id: taskId, name: baselineForm.name.trim(), device_model: baselineForm.device_model.trim() || undefined, firmware: baselineForm.firmware.trim() || undefined },
      {
        onSuccess: (baseline) => {
          message.success('基线创建成功');
          setBaselineModalVisible(false);
          setBaselineForm({ name: '', device_model: '', firmware: '' });
          navigate(`/baselines/${baseline.id}`);
        },
      },
    );
  };

  if (isLoading || !task) {
    return <Card loading={isLoading}>加载中...</Card>;
  }

  const result = task.result;
  const fioCommand = buildFioCommand(task.config, task.device_path, task.id);

  return (
    <div>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/tasks')}>
            返回列表
          </Button>
          <h2 style={{ margin: 0 }}>任务详情 - {task.name}</h2>
        </Space>
        <Space>
          <TaskStatusBadge status={task.status} stale={task.stale} />
          {task.status === 'SUCCESS' && (
            <Button
              type="primary"
              icon={<SaveOutlined />}
              onClick={() => setBaselineModalVisible(true)}
            >
              设为基线
            </Button>
          )}
          {task.status === 'SUCCESS' && (
            <Button onClick={() => navigate('/regressions', { state: { taskId } })}>
              回归比对
            </Button>
          )}
        </Space>
      </div>

      {/* 基本信息 */}
      <Card title="基本信息" size="small" style={{ marginBottom: 16 }}>
        <Descriptions column={3} size="small">
          <Descriptions.Item label="任务ID">{task.id}</Descriptions.Item>
          <Descriptions.Item label="任务名称">{task.name}</Descriptions.Item>
          <Descriptions.Item label="状态"><TaskStatusBadge status={task.status} /></Descriptions.Item>
          <Descriptions.Item label="创建时间">{formatTime(task.created_at)}</Descriptions.Item>
          <Descriptions.Item label="更新时间">{formatTime(task.updated_at)}</Descriptions.Item>
          <Descriptions.Item label="故障类型">
            <Tag>{task.fault_type || '无'}</Tag>
          </Descriptions.Item>
        </Descriptions>
      </Card>

      {/* 设备 & FIO 配置 */}
      <Card title="设备 & FIO 配置" size="small" style={{ marginBottom: 16 }}>
        <Descriptions column={4} size="small">
          <Descriptions.Item label="设备IP">{task.device_ip}</Descriptions.Item>
          <Descriptions.Item label="设备路径">{task.device_path}</Descriptions.Item>
          <Descriptions.Item label="读写模式">{task.config.rw}</Descriptions.Item>
          <Descriptions.Item label="块大小">{task.config.bs || '4k'}</Descriptions.Item>
          <Descriptions.Item label="并发数">{task.config.numjobs || 1}</Descriptions.Item>
          <Descriptions.Item label="IO深度">{task.config.iodepth || 32}</Descriptions.Item>
          <Descriptions.Item label="运行时间">{task.config.runtime ? `${task.config.runtime}s` : '-'}</Descriptions.Item>
        </Descriptions>
        <div
          style={{
            marginTop: 16,
            padding: 12,
            background: '#fafafa',
            border: '1px solid #f0f0f0',
            borderRadius: 6,
            fontFamily: 'Consolas, Monaco, monospace',
            fontSize: 12,
            lineHeight: 1.6,
            wordBreak: 'break-all',
            whiteSpace: 'pre-wrap',
          }}
        >
          {fioCommand}
        </div>
      </Card>

      {/* 测试结果汇总 */}
      {result && (
        <Card title="测试结果汇总" size="small" style={{ marginBottom: 16 }}>
          <Row gutter={16}>
            <Col span={6}>
              <Statistic title="IOPS" value={result.iops} formatter={(v) => formatNumber(v as number)} />
            </Col>
            <Col span={6}>
              <Statistic title="带宽" value={result.bandwidth} formatter={(v) => formatBytes(v as number) + '/s'} />
            </Col>
            <Col span={6}>
              <Statistic title="平均延迟" value={result.latency?.mean} suffix="μs" precision={1} />
            </Col>
            <Col span={6}>
              <Statistic title="最大延迟" value={result.latency?.max} suffix="μs" precision={1} />
            </Col>
            {result.latency?.p99 != null && (
              <Col span={6}>
                <Statistic title="P99 延迟" value={result.latency.p99} suffix="μs" precision={1} />
              </Col>
            )}
          </Row>
        </Card>
      )}

      {/* FIO 趋势图 */}
      <FioTrendSection taskId={taskId} status={task.status} />

      {/* SMART 信息 */}
      {result?.smart && (
        <Card title="SMART 信息" size="small" style={{ marginBottom: 16 }}>
          <Descriptions column={4} size="small">
            <Descriptions.Item label="温度">{result.smart.temperature}°C</Descriptions.Item>
            <Descriptions.Item label="寿命已用">{result.smart.percentage_used}%</Descriptions.Item>
            <Descriptions.Item label="通电时长">{result.smart.power_on_hours}h</Descriptions.Item>
            <Descriptions.Item label="介质错误">{result.smart.media_errors}</Descriptions.Item>
          </Descriptions>
        </Card>
      )}

      {/* AI 分析 */}
      {task.status !== 'PENDING' && (
        <AiAnalysisSection taskId={taskId} status={task.status} />
      )}

      {/* 设为基线 Modal */}
      <Modal
        title="设为基线"
        open={baselineModalVisible}
        onOk={handleCreateBaseline}
        onCancel={() => setBaselineModalVisible(false)}
        confirmLoading={creatingBaseline}
        okText="确认创建"
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div>
            <div style={{ marginBottom: 4 }}>基线名称 <span style={{ color: '#ff4d4f' }}>*</span></div>
            <Input
              placeholder="例如：NVMe-A100 初始基线"
              value={baselineForm.name}
              onChange={(e) => setBaselineForm((f) => ({ ...f, name: e.target.value }))}
            />
          </div>
          <div>
            <div style={{ marginBottom: 4 }}>设备型号</div>
            <Input
              placeholder="例如：Samsung 980 Pro"
              value={baselineForm.device_model}
              onChange={(e) => setBaselineForm((f) => ({ ...f, device_model: e.target.value }))}
            />
          </div>
          <div>
            <div style={{ marginBottom: 4 }}>固件版本</div>
            <Input
              placeholder="例如：5B2QGXA7"
              value={baselineForm.firmware}
              onChange={(e) => setBaselineForm((f) => ({ ...f, firmware: e.target.value }))}
            />
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default TaskDetail;
