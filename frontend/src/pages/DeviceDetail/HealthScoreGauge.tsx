import React, { useState } from 'react';
import { Row, Col, Progress, Collapse } from 'antd';
import ReactECharts from 'echarts-for-react';
import type { HealthScoreDetail } from '@/types/smart';

interface HealthScoreGaugeProps {
  diskName: string;
  score: number;
  level: 'good' | 'warning' | 'critical' | 'failed';
  details: {
    temperature_score: number;
    wear_score: number;
    media_errors_score: number;
    critical_warning_score: number;
    spare_score: number;
  };
}

const levelLabelMap: Record<string, string> = {
  good: '健康',
  warning: '需关注',
  critical: '危险',
  failed: '严重',
};

const levelColorMap: Record<string, string> = {
  good: '#52c41a',
  warning: '#faad14',
  critical: '#ff4d4f',
  failed: '#cf1322',
};

const detailItems = [
  { key: 'temperature_score', label: '温度评分', max: 30 },
  { key: 'wear_score', label: '磨损评分', max: 25 },
  { key: 'media_errors_score', label: '介质错误评分', max: 25 },
  { key: 'critical_warning_score', label: '警告评分', max: 15 },
  { key: 'spare_score', label: '备用空间评分', max: 10 },
] as const;

const HealthScoreGauge: React.FC<HealthScoreGaugeProps> = ({ diskName, score, level, details }) => {
  const [expanded, setExpanded] = useState(false);

  const gaugeOption = {
    series: [{
      type: 'gauge',
      min: 0,
      max: 100,
      splitNumber: 5,
      axisLine: {
        lineStyle: {
          width: 15,
          color: [
            [0.4, '#cf1322'],
            [0.6, '#ff4d4f'],
            [0.8, '#faad14'],
            [1, '#52c41a'],
          ],
        },
      },
      pointer: {
        itemStyle: { color: 'auto' },
      },
      axisTick: { distance: -15, length: 5, lineStyle: { color: '#fff', width: 1 } },
      splitLine: { distance: -15, length: 15, lineStyle: { color: '#fff', width: 2 } },
      axisLabel: { distance: -5, color: '#999', fontSize: 10 },
      detail: {
        valueAnimation: true,
        formatter: '{value}',
        fontSize: 36,
        fontWeight: 'bold',
        color: levelColorMap[level] || '#333',
        offsetCenter: [0, '70%'],
      },
      title: {
        offsetCenter: [0, '90%'],
        fontSize: 14,
        color: levelColorMap[level] || '#666',
      },
      data: [{ value: score, name: levelLabelMap[level] || level }],
    }],
    tooltip: {
      formatter: () => {
        const lines = detailItems.map((item) => {
          const val = details[item.key] ?? 0;
          return `${item.label}: ${val.toFixed(1)} / ${item.max}`;
        });
        return `<div style="line-height:1.8">${lines.join('<br/>')}</div>`;
      },
    },
  };

  return (
    <div
      style={{ border: '1px solid #f0f0f0', borderRadius: 8, padding: 12, cursor: 'pointer' }}
      onClick={() => setExpanded(!expanded)}
    >
      <div style={{ textAlign: 'center', fontWeight: 600, marginBottom: 4 }}>
        {diskName}
      </div>
      <ReactECharts option={gaugeOption} style={{ height: 200 }} />
      <Collapse
        activeKey={expanded ? ['details'] : []}
        ghost
        size="small"
        items={[{
          key: 'details',
          label: '评分明细',
          children: (
            <div style={{ padding: '0 8px' }}>
              {detailItems.map((item) => {
                const val = details[item.key] ?? 0;
                const percent = Math.round((val / item.max) * 100);
                const status: 'success' | 'normal' | 'exception' = percent >= 80 ? 'success' : percent >= 50 ? 'normal' : 'exception';
                return (
                  <div key={item.key} style={{ marginBottom: 4 }}>
                    <span style={{ fontSize: 12, color: '#666' }}>{item.label}</span>
                    <Progress percent={percent} size="small" status={status} format={() => `${val.toFixed(1)}/${item.max}`} />
                  </div>
                );
              })}
            </div>
          ),
        }]}
      />
    </div>
  );
};

export default HealthScoreGauge;