import React from 'react';
import { Tag } from 'antd';
import type { TaskStatus } from '@/types/task';
import { TASK_STATUS_MAP } from '@/utils/constants';

const TaskStatusBadge: React.FC<{ status: TaskStatus }> = ({ status }) => {
  const config = TASK_STATUS_MAP[status] || { color: 'default', text: status };
  return <Tag color={config.color}>{config.text}</Tag>;
};

export default TaskStatusBadge;
