import React from 'react';
import { Tag } from 'antd';
import type { TaskStatus } from '@/types/task';
import { TASK_STATUS_MAP } from '@/utils/constants';

interface TaskStatusBadgeProps {
  status: TaskStatus;
  stale?: boolean;
}

const TaskStatusBadge: React.FC<TaskStatusBadgeProps> = ({ status, stale }) => {
  const key = stale && status === 'RUNNING' ? 'RUNNING_STALE' : status;
  const config = TASK_STATUS_MAP[key] || { color: 'default', text: status };
  return <Tag color={config.color}>{config.text}</Tag>;
};

export default TaskStatusBadge;
