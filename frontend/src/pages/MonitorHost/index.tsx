import React, { useState } from 'react';
import { Card, Select, Row, Col, Statistic, Checkbox, Descriptions, Space, Progress } from 'antd';
import ReactECharts from 'echarts-for-react';
import TimeRangeSelector from '@/components/TimeRangeSelector/index';
import { useHostMonitor, useHostSummary } from '@/hooks/useMonitor';
import { usePolling } from '@/hooks/usePolling';
import { useQuery } from '@tanstack/react-query';
import { deviceApi } from '@/api/device';
import { formatChartTime, formatPercent, formatBytes, formatUptime } from '@/utils/format';
import type { TimeRange, HostMetricPoint } from '@/types/monitor';

const MonitorHost: React.FC = () => {
  const [selectedHost, setSelectedHost] = useState<string>('');
  const [timeRange, setTimeRange] = useState<TimeRange>('5m');
  const [autoRefresh, setAutoRefresh] = useState(true);

  const { data: devices } = useQuery({
    queryKey: ['devices'],
    queryFn: () => deviceApi.list(),
  });
  const { data: monitorData, refetch } = useHostMonitor(selectedHost, timeRange);
  const { data: summary } = useHostSummary(selectedHost);

  usePolling({ fn: () => refetch(), enabled: autoRefresh && !!selectedHost, interval: 5000 });

  const hostOptions = (devices || []).map((d) => ({ value: d.ip, label: `${d.ip} (${d.name})` }));
  const data: HostMetricPoint[] = monitorData || [];

  const cpuOption = {
    tooltip: { trigger: 'axis' as const },
    legend: {},
    grid: { top: 40, bottom: 30, left: 50, right: 20 },
    xAxis: { type: 'category' as const, data: data.map((d) => formatChartTime(d.timestamp)) },
    yAxis: { type: 'value' as const, name: '%', max: 100 },
    series: [
      { name: 'user', type: 'line', data: data.map((d) => d.cpu_user_percent), smooth: true, areaStyle: { opacity: 0.1 } },
      { name: 'system', type: 'line', data: data.map((d) => d.cpu_system_percent), smooth: true, areaStyle: { opacity: 0.1 } },
      { name: 'iowait', type: 'line', data: data.map((d) => d.cpu_iowait_percent), smooth: true },
    ],
  };

  const memOption = {
    tooltip: { trigger: 'axis' as const },
    legend: {},
    grid: { top: 40, bottom: 30, left: 60, right: 20 },
    xAxis: { type: 'category' as const, data: data.map((d) => formatChartTime(d.timestamp)) },
    yAxis: { type: 'value' as const, name: 'GB', axisLabel: { formatter: (v: number) => (v / 1073741824).toFixed(1) } },
    series: [
      { name: '已用', type: 'line', data: data.map((d) => d.mem_used_bytes), smooth: true, areaStyle: { opacity: 0.2 } },
      { name: '缓存', type: 'line', data: data.map((d) => d.mem_cached_bytes), smooth: true },
      { name: '可用', type: 'line', data: data.map((d) => d.mem_available_bytes), smooth: true },
    ],
  };

  const netOption = {
    tooltip: { trigger: 'axis' as const },
    legend: {},
    grid: { top: 40, bottom: 30, left: 60, right: 20 },
    xAxis: { type: 'category' as const, data: data.map((d) => formatChartTime(d.timestamp)) },
    yAxis: { type: 'value' as const, name: 'MB/s', axisLabel: { formatter: (v: number) => (v / 1048576).toFixed(1) } },
    series: [
      { name: '接收(rx)', type: 'line', data: data.map((d) => d.net_rx_bytes_per_sec), smooth: true },
      { name: '发送(tx)', type: 'line', data: data.map((d) => d.net_tx_bytes_per_sec), smooth: true },
    ],
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h2 style={{ margin: 0 }}>主机监控</h2>
        <Space>
          <Select
            value={selectedHost || undefined}
            onChange={setSelectedHost}
            options={hostOptions}
            placeholder="选择设备节点"
            style={{ width: 220 }}
            size="small"
          />
          <TimeRangeSelector value={timeRange} onChange={setTimeRange} />
          <Checkbox checked={autoRefresh} onChange={(e) => setAutoRefresh(e.target.checked)}>
            自动刷新
          </Checkbox>
        </Space>
      </div>

      {!selectedHost ? (
        <Card><div style={{ textAlign: 'center', padding: 40, color: '#999' }}>请选择设备节点</div></Card>
      ) : (
        <>
          {/* 概览卡片 */}
          {summary && (
            <Row gutter={16} style={{ marginBottom: 16 }}>
              <Col span={6}>
                <Card size="small">
                  <Statistic title="CPU使用率" value={summary.cpu_usage_percent} suffix="%" precision={1} />
                  <Progress percent={summary.cpu_usage_percent} showInfo={false} size="small" />
                </Card>
              </Col>
              <Col span={6}>
                <Card size="small">
                  <Statistic title="内存使用率" value={summary.mem_usage_percent} suffix="%" precision={1} />
                  <Progress percent={summary.mem_usage_percent} showInfo={false} size="small" />
                </Card>
              </Col>
              <Col span={6}>
                <Card size="small">
                  <Statistic title="IO等待" value={summary.iowait_percent} suffix="%" precision={1} />
                </Card>
              </Col>
              <Col span={6}>
                <Card size="small">
                  <Statistic title="负载(1m)" value={summary.load_avg_1m} precision={2} />
                </Card>
              </Col>
            </Row>
          )}

          {/* CPU 图表 */}
          <Card title="CPU 监控" size="small" style={{ marginBottom: 16 }}>
            {data.length > 0 ? (
              <ReactECharts option={cpuOption} style={{ height: 280 }} />
            ) : (
              <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>暂无数据</div>
            )}
          </Card>

          {/* 内存图表 */}
          <Card title="内存 & Swap" size="small" style={{ marginBottom: 16 }}>
            {data.length > 0 ? (
              <ReactECharts option={memOption} style={{ height: 280 }} />
            ) : (
              <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>暂无数据</div>
            )}
          </Card>

          {/* 网络图表 */}
          <Card title="网络" size="small" style={{ marginBottom: 16 }}>
            {data.length > 0 ? (
              <ReactECharts option={netOption} style={{ height: 250 }} />
            ) : (
              <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>暂无数据</div>
            )}
          </Card>

          {/* 系统信息 */}
          {summary && (
            <Card title="系统信息" size="small">
              <Descriptions column={4} size="small">
                <Descriptions.Item label="内核版本">{summary.kernel_version}</Descriptions.Item>
                <Descriptions.Item label="运行时长">{formatUptime(summary.uptime_seconds)}</Descriptions.Item>
                <Descriptions.Item label="进程数">{summary.process_count}</Descriptions.Item>
                <Descriptions.Item label="负载">{`${summary.load_avg_1m} / ${summary.load_avg_5m} / ${summary.load_avg_15m}`}</Descriptions.Item>
              </Descriptions>
            </Card>
          )}
        </>
      )}
    </div>
  );
};

export default MonitorHost;
