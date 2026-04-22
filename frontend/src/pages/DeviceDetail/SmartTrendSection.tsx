import React, { useState, useEffect } from 'react';
import { Card, Select, Space, Empty } from 'antd';
import ReactECharts from 'echarts-for-react';
import TimeRangeSelector from '@/components/TimeRangeSelector/index';
import { useSmartHistory } from '@/hooks/useSmart';
import { formatChartTime, formatDataUnits } from '@/utils/format';
import type { TimeRange } from '@/types/monitor';
import type { SmartDiskSnapshot } from '@/types/smart';
import type { Dayjs } from 'dayjs';

interface SmartTrendSectionProps {
  deviceId: number;
  disks: SmartDiskSnapshot[];
}

const SmartTrendSection: React.FC<SmartTrendSectionProps> = ({ deviceId, disks }) => {
  const [selectedDisk, setSelectedDisk] = useState<string>('');
  const [timeRange, setTimeRange] = useState<TimeRange>('24h');
  const [customRange, setCustomRange] = useState<[Dayjs, Dayjs] | null>(null);

  useEffect(() => {
    if (disks.length > 0 && !selectedDisk) {
      setSelectedDisk(disks[0].disk_name);
    }
  }, [disks, selectedDisk]);

  const { data: historyData } = useSmartHistory(deviceId, selectedDisk, timeRange);
  const points = historyData?.points || [];

  const diskOptions = disks.map((d) => ({
    label: d.disk_name,
    value: d.disk_name,
  }));

  // Temperature trend chart
  const tempOption = {
    title: { text: '温度趋势', textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'axis' as const, valueFormatter: (v: number) => `${v} °C` },
    grid: { top: 40, bottom: 60, left: 50, right: 20 },
    xAxis: { type: 'category' as const, data: points.map((p) => formatChartTime(p.event_time)) },
    yAxis: { type: 'value' as const, name: '°C' },
    series: [{ name: '温度', type: 'line', data: points.map((p) => p.temperature), smooth: true, itemStyle: { color: '#ff4d4f' } }],
    dataZoom: [{ type: 'inside' }, { type: 'slider' }],
  };

  // Wear progress chart
  const wearOption = {
    title: { text: '磨损进展', textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'axis' as const, valueFormatter: (v: number) => `${v}%` },
    grid: { top: 40, bottom: 60, left: 50, right: 20 },
    xAxis: { type: 'category' as const, data: points.map((p) => formatChartTime(p.event_time)) },
    yAxis: { type: 'value' as const, name: '%', min: 0, max: 100 },
    series: [{ name: '磨损百分比', type: 'line', data: points.map((p) => p.percentage_used), smooth: true, itemStyle: { color: '#faad14' } }],
    dataZoom: [{ type: 'inside' }, { type: 'slider' }],
  };

  // Data volume trend chart (dual Y axis)
  const dataOption = {
    title: { text: '数据量趋势', textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'axis' as const },
    legend: {},
    grid: { top: 40, bottom: 60, left: 60, right: 60 },
    xAxis: { type: 'category' as const, data: points.map((p) => formatChartTime(p.event_time)) },
    yAxis: [
      { type: 'value' as const, name: '读取 (GB)', position: 'left' as const },
      { type: 'value' as const, name: '写入 (GB)', position: 'right' as const },
    ],
    series: [
      {
        name: '读取量',
        type: 'line',
        data: points.map((p) => (p.data_units_read * 512) / (1024 ** 3)),
        smooth: true,
        itemStyle: { color: '#1890ff' },
      },
      {
        name: '写入量',
        type: 'line',
        yAxisIndex: 1,
        data: points.map((p) => (p.data_units_written * 512) / (1024 ** 3)),
        smooth: true,
        itemStyle: { color: '#52c41a' },
      },
    ],
    dataZoom: [{ type: 'inside' }, { type: 'slider' }],
  };

  // Media errors step chart
  const mediaOption = {
    title: { text: '介质错误', textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'axis' as const },
    grid: { top: 40, bottom: 60, left: 50, right: 20 },
    xAxis: { type: 'category' as const, data: points.map((p) => formatChartTime(p.event_time)) },
    yAxis: { type: 'value' as const, name: '个' },
    series: [{ name: '介质错误', type: 'line', step: 'end', data: points.map((p) => p.media_errors), itemStyle: { color: '#cf1322' } }],
    dataZoom: [{ type: 'inside' }, { type: 'slider' }],
  };

  return (
    <Card title="SMART 历史趋势" size="small" style={{ marginBottom: 16 }}>
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        <Space wrap>
          <span>磁盘:</span>
          <Select
            value={selectedDisk || undefined}
            onChange={setSelectedDisk}
            options={diskOptions}
            style={{ width: 160 }}
            placeholder="选择磁盘"
          />
          <TimeRangeSelector
            value={timeRange}
            onChange={setTimeRange}
            customRange={customRange}
            onCustomChange={setCustomRange}
          />
        </Space>
        {points.length > 0 ? (
          <>
            <ReactECharts option={tempOption} style={{ height: 280 }} />
            <ReactECharts option={wearOption} style={{ height: 280 }} />
            <ReactECharts option={dataOption} style={{ height: 280 }} />
            <ReactECharts option={mediaOption} style={{ height: 280 }} />
          </>
        ) : (
          <Empty description="暂无 SMART 历史数据" />
        )}
      </Space>
    </Card>
  );
};

export default SmartTrendSection;