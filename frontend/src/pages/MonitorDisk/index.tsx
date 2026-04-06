import React, { useState } from 'react';
import { Card, Select, Row, Col, Checkbox, Space, Descriptions, Tag } from 'antd';
import ReactECharts from 'echarts-for-react';
import TimeRangeSelector from '@/components/TimeRangeSelector/index';
import { useDiskMonitor, useDiskList } from '@/hooks/useMonitor';
import { usePolling } from '@/hooks/usePolling';
import { useQuery } from '@tanstack/react-query';
import { deviceApi } from '@/api/device';
import { formatChartTime, formatNumber, formatBytes } from '@/utils/format';
import type { TimeRange, DiskMetricPoint } from '@/types/monitor';

const MonitorDisk: React.FC = () => {
  const [selectedHost, setSelectedHost] = useState<string>('');
  const [selectedDisks, setSelectedDisks] = useState<string[]>([]);
  const [timeRange, setTimeRange] = useState<TimeRange>('5m');
  const [autoRefresh, setAutoRefresh] = useState(true);

  const { data: devices } = useQuery({
    queryKey: ['devices'],
    queryFn: () => deviceApi.list(),
  });
  const { data: diskList } = useDiskList(selectedHost);
  const { data: monitorData, refetch } = useDiskMonitor(selectedHost, selectedDisks, timeRange);

  usePolling({ fn: () => refetch(), enabled: autoRefresh && selectedDisks.length > 0, interval: 5000 });

  const hostOptions = (devices || []).map((d) => ({ value: d.ip, label: `${d.ip} (${d.name})` }));
  const diskOptions = (diskList || []).map((d) => ({ label: d, value: d }));

  // Flatten disk metric arrays
  const allData: DiskMetricPoint[] = (monitorData || []).flat();
  const timestamps = [...new Set(allData.map((d) => d.timestamp))].sort();

  const buildDiskSeries = (
    metricFn: (d: DiskMetricPoint) => number,
    disks: string[]
  ) =>
    disks.map((disk) => {
      const diskData = allData.filter((d) => d.disk_name === disk);
      return {
        name: disk,
        type: 'line' as const,
        data: timestamps.map((t) => {
          const point = diskData.find((d) => d.timestamp === t);
          return point ? metricFn(point) : 0;
        }),
        smooth: true,
      };
    });

  const iopsOption = {
    tooltip: { trigger: 'axis' as const },
    legend: {},
    grid: { top: 40, bottom: 30, left: 60, right: 20 },
    xAxis: { type: 'category' as const, data: timestamps.map(formatChartTime) },
    yAxis: { type: 'value' as const, name: 'IOPS' },
    series: [
      ...buildDiskSeries((d) => d.disk_iops_read, selectedDisks).map((s) => ({ ...s, name: `${s.name} read` })),
      ...buildDiskSeries((d) => d.disk_iops_write, selectedDisks).map((s) => ({ ...s, name: `${s.name} write`, lineStyle: { type: 'dashed' as const } })),
    ],
  };

  const bwOption = {
    tooltip: { trigger: 'axis' as const },
    legend: {},
    grid: { top: 40, bottom: 30, left: 60, right: 20 },
    xAxis: { type: 'category' as const, data: timestamps.map(formatChartTime) },
    yAxis: { type: 'value' as const, name: 'MB/s', axisLabel: { formatter: (v: number) => (v / 1048576).toFixed(1) } },
    series: [
      ...buildDiskSeries((d) => d.disk_bw_read_bytes_per_sec, selectedDisks).map((s) => ({ ...s, name: `${s.name} read` })),
      ...buildDiskSeries((d) => d.disk_bw_write_bytes_per_sec, selectedDisks).map((s) => ({ ...s, name: `${s.name} write`, lineStyle: { type: 'dashed' as const } })),
    ],
  };

  const latencyOption = {
    tooltip: { trigger: 'axis' as const },
    legend: {},
    grid: { top: 40, bottom: 30, left: 60, right: 60 },
    xAxis: { type: 'category' as const, data: timestamps.map(formatChartTime) },
    yAxis: { type: 'value' as const, name: 'ms' },
    series: [
      ...buildDiskSeries((d) => d.disk_latency_read_ms, selectedDisks).map((s) => ({ ...s, name: `${s.name} read lat` })),
      ...buildDiskSeries((d) => d.disk_latency_write_ms, selectedDisks).map((s) => ({ ...s, name: `${s.name} write lat` })),
    ],
  };

  const queueOption = {
    tooltip: { trigger: 'axis' as const },
    legend: {},
    grid: { top: 40, bottom: 30, left: 60, right: 60 },
    xAxis: { type: 'category' as const, data: timestamps.map(formatChartTime) },
    yAxis: [
      { type: 'value' as const, name: '队列深度', position: 'left' as const },
      { type: 'value' as const, name: 'await(ms)', position: 'right' as const },
    ],
    series: [
      ...buildDiskSeries((d) => d.disk_queue_depth, selectedDisks),
      ...buildDiskSeries((d) => d.disk_await_ms, selectedDisks).map((s) => ({ ...s, name: `${s.name} await`, yAxisIndex: 1 })),
    ],
  };

  const utilOption = {
    tooltip: { trigger: 'axis' as const },
    legend: {},
    grid: { top: 40, bottom: 30, left: 50, right: 20 },
    xAxis: { type: 'category' as const, data: timestamps.map(formatChartTime) },
    yAxis: { type: 'value' as const, name: '%util', max: 100 },
    series: buildDiskSeries((d) => d.disk_util_percent, selectedDisks),
  };

  const hasData = allData.length > 0;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h2 style={{ margin: 0 }}>磁盘监控</h2>
        <Space wrap>
          <Select
            value={selectedHost || undefined}
            onChange={(v) => {
              setSelectedHost(v);
              setSelectedDisks([]);
            }}
            options={hostOptions}
            placeholder="选择设备节点"
            style={{ width: 200 }}
            size="small"
          />
          <Checkbox.Group
            options={diskOptions}
            value={selectedDisks}
            onChange={(vals) => setSelectedDisks(vals as string[])}
          />
          <TimeRangeSelector value={timeRange} onChange={setTimeRange} />
          <Checkbox checked={autoRefresh} onChange={(e) => setAutoRefresh(e.target.checked)}>
            自动刷新
          </Checkbox>
        </Space>
      </div>

      {!selectedHost || selectedDisks.length === 0 ? (
        <Card>
          <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>
            {!selectedHost ? '请选择设备节点' : '请选择磁盘'}
          </div>
        </Card>
      ) : (
        <>
          <Card title="IOPS 趋势" size="small" style={{ marginBottom: 16 }}>
            {hasData ? <ReactECharts option={iopsOption} style={{ height: 280 }} /> : <NoData />}
          </Card>

          <Card title="带宽趋势" size="small" style={{ marginBottom: 16 }}>
            {hasData ? <ReactECharts option={bwOption} style={{ height: 280 }} /> : <NoData />}
          </Card>

          <Row gutter={16} style={{ marginBottom: 16 }}>
            <Col span={12}>
              <Card title="延迟趋势" size="small">
                {hasData ? <ReactECharts option={latencyOption} style={{ height: 250 }} /> : <NoData />}
              </Card>
            </Col>
            <Col span={12}>
              <Card title="队列深度 & await" size="small">
                {hasData ? <ReactECharts option={queueOption} style={{ height: 250 }} /> : <NoData />}
              </Card>
            </Col>
          </Row>

          <Card title="磁盘繁忙度(%util)" size="small">
            {hasData ? <ReactECharts option={utilOption} style={{ height: 250 }} /> : <NoData />}
          </Card>
        </>
      )}
    </div>
  );
};

const NoData: React.FC = () => (
  <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>暂无数据</div>
);

export default MonitorDisk;
