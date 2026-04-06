import React from 'react';
import { Space, Radio, DatePicker } from 'antd';
import type { TimeRange } from '@/types/monitor';
import type { Dayjs } from 'dayjs';

const { RangePicker } = DatePicker;

interface TimeRangeSelectorProps {
  value: TimeRange;
  onChange: (range: TimeRange) => void;
  customRange?: [Dayjs, Dayjs] | null;
  onCustomChange?: (range: [Dayjs, Dayjs] | null) => void;
  showShort?: boolean;
}

const TimeRangeSelector: React.FC<TimeRangeSelectorProps> = ({
  value,
  onChange,
  customRange,
  onCustomChange,
  showShort = false,
}) => {
  return (
    <Space>
      <Radio.Group
        value={value}
        onChange={(e) => onChange(e.target.value)}
        buttonStyle="solid"
        size="small"
      >
        {showShort && <Radio.Button value="1m">1分钟</Radio.Button>}
        <Radio.Button value="5m">5分钟</Radio.Button>
        <Radio.Button value="15m">15分钟</Radio.Button>
        <Radio.Button value="1h">1小时</Radio.Button>
        <Radio.Button value="all">全部</Radio.Button>
        <Radio.Button value="custom">自定义</Radio.Button>
      </Radio.Group>
      {value === 'custom' && (
        <RangePicker
          showTime
          value={customRange}
          onChange={(vals) =>
            onCustomChange?.(vals as [Dayjs, Dayjs] | null)
          }
          size="small"
        />
      )}
    </Space>
  );
};

export default TimeRangeSelector;
