import React, { useState } from 'react';
import { Card, Checkbox, Space } from 'antd';
import ReactECharts from 'echarts-for-react';
import TimeRangeSelector from '@/components/TimeRangeSelector/index';
import { useFioTrend } from '@/hooks/useTask';
import { usePolling } from '@/hooks/usePolling';
import { formatChartTime } from '@/utils/format';
import type { TimeRange } from '@/types/monitor';
import type { TaskStatus, FioTrendPoint } from '@/types/task';
import type { Dayjs } from 'dayjs';

interface MetricVisibility {
  iops_total: boolean;
  iops_read: boolean;
  iops_write: boolean;
  bw_total: boolean;
  bw_read: boolean;
  bw_write: boolean;
  lat_mean: boolean;
  lat_p99: boolean;
  lat_max: boolean;
}

const FioTrendSection: React.FC<{ taskId: number; status: TaskStatus }> = ({ taskId, status }) => {
  const [timeRange, setTimeRange] = useState<TimeRange>('all');
  const [customRange, setCustomRange] = useState<[Dayjs, Dayjs] | null>(null);
  const [visible, setVisible] = useState<MetricVisibility>({
    iops_total: true, iops_read: false, iops_write: false,
    bw_total: true, bw_read: false, bw_write: false,
    lat_mean: true, lat_p99: false, lat_max: false,
  });

  const { data: trendData, refetch } = useFioTrend(taskId, { timeRange, customRange });

  usePolling({ fn: () => refetch(), enabled: status === 'RUNNING', interval: 2000 });

  const data: FioTrendPoint[] = trendData || [];

  const iopsBwOption = {
    tooltip: { trigger: 'axis' as const },
    legend: {},
    grid: { top: 50, bottom: 60, left: 60, right: 60 },
    xAxis: {
      type: 'category' as const,
      data: data.map((d) => formatChartTime(d.timestamp)),
    },
    yAxis: [
      { type: 'value' as const, name: 'IOPS', position: 'left' as const },
      { type: 'value' as const, name: '带宽(MB/s)', position: 'right' as const },
    ],
    series: [
      visible.iops_total && { name: 'IOPS(总)', type: 'line', data: data.map((d) => d.iops_total), smooth: true },
      visible.iops_read && { name: 'IOPS(读)', type: 'line', data: data.map((d) => d.iops_read), lineStyle: { type: 'dashed' } },
      visible.iops_write && { name: 'IOPS(写)', type: 'line', data: data.map((d) => d.iops_write), lineStyle: { type: 'dashed' } },
      visible.bw_total && { name: '带宽(总)', type: 'line', yAxisIndex: 1, data: data.map((d) => d.bw_total / 1024), smooth: true },
      visible.bw_read && { name: '带宽(读)', type: 'line', yAxisIndex: 1, data: data.map((d) => d.bw_read / 1024), lineStyle: { type: 'dashed' } },
      visible.bw_write && { name: '带宽(写)', type: 'line', yAxisIndex: 1, data: data.map((d) => d.bw_write / 1024), lineStyle: { type: 'dashed' } },
    ].filter(Boolean),
    dataZoom: [{ type: 'inside' }, { type: 'slider' }],
  };

  const latencyOption = {
    tooltip: { trigger: 'axis' as const },
    legend: {},
    grid: { top: 40, bottom: 60, left: 60, right: 20 },
    xAxis: {
      type: 'category' as const,
      data: data.map((d) => formatChartTime(d.timestamp)),
    },
    yAxis: { type: 'value' as const, name: '延迟(μs)' },
    series: [
      visible.lat_mean && { name: '平均延迟', type: 'line', data: data.map((d) => d.lat_mean), smooth: true },
      visible.lat_p99 && { name: 'P99延迟', type: 'line', data: data.map((d) => d.lat_p99), lineStyle: { type: 'dashed' } },
      visible.lat_max && { name: '最大延迟', type: 'line', data: data.map((d) => d.lat_max), lineStyle: { type: 'dotted' } },
    ].filter(Boolean),
    dataZoom: [{ type: 'inside' }, { type: 'slider' }],
  };

  const toggleMetric = (key: keyof MetricVisibility) => {
    setVisible((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  return (
    <Card title="FIO性能趋势图" size="small" style={{ marginBottom: 16 }}>
      <Space direction="vertical" style={{ width: '100%' }}>
        <TimeRangeSelector
          value={timeRange}
          onChange={setTimeRange}
          customRange={customRange}
          onCustomChange={setCustomRange}
          showShort
        />
        <Space wrap>
          <span>显示指标:</span>
          <Checkbox checked={visible.iops_total} onChange={() => toggleMetric('iops_total')}>IOPS(总)</Checkbox>
          <Checkbox checked={visible.iops_read} onChange={() => toggleMetric('iops_read')}>IOPS(读)</Checkbox>
          <Checkbox checked={visible.iops_write} onChange={() => toggleMetric('iops_write')}>IOPS(写)</Checkbox>
          <Checkbox checked={visible.bw_total} onChange={() => toggleMetric('bw_total')}>带宽(总)</Checkbox>
          <Checkbox checked={visible.bw_read} onChange={() => toggleMetric('bw_read')}>带宽(读)</Checkbox>
          <Checkbox checked={visible.bw_write} onChange={() => toggleMetric('bw_write')}>带宽(写)</Checkbox>
          <Checkbox checked={visible.lat_mean} onChange={() => toggleMetric('lat_mean')}>平均延迟</Checkbox>
          <Checkbox checked={visible.lat_p99} onChange={() => toggleMetric('lat_p99')}>P99延迟</Checkbox>
          <Checkbox checked={visible.lat_max} onChange={() => toggleMetric('lat_max')}>最大延迟</Checkbox>
        </Space>
        {data.length > 0 ? (
          <>
            <ReactECharts option={iopsBwOption} style={{ height: 320 }} />
            <ReactECharts option={latencyOption} style={{ height: 250 }} />
          </>
        ) : (
          <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>
            暂无趋势数据
          </div>
        )}
      </Space>
    </Card>
  );
};

export default FioTrendSection;
