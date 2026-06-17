import React, { useState } from 'react';
import { Table, Button, Space, Tag, Popconfirm, message } from 'antd';
import { PlusOutlined, EyeOutlined, DeleteOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useGroupTaskList, useDeleteGroupTask } from '@/hooks/useGroupTask';
import { formatTime } from '@/utils/format';
import GroupTaskCreateModal from '@/components/GroupTaskCreateModal';
import type { GroupTask, GroupTaskStatus } from '@/types/group-task';
import type { ColumnsType } from 'antd/es/table';

const STATUS_MAP: Record<GroupTaskStatus, { color: string; text: string }> = {
  pending: { color: 'default', text: '等待中' },
  running: { color: 'processing', text: '运行中' },
  done: { color: 'success', text: '已完成' },
  failed: { color: 'error', text: '失败' },
  partial: { color: 'warning', text: '部分完成' },
};

const GroupTaskList: React.FC = () => {
  const navigate = useNavigate();
  const [createVisible, setCreateVisible] = useState(false);
  const [pagination, setPagination] = useState({ page: 1, pageSize: 10 });

  const { data, isLoading } = useGroupTaskList(pagination);
  const { mutate: deleteGroupTask } = useDeleteGroupTask();

  const handleDelete = (id: number) => {
    deleteGroupTask(id, {
      onSuccess: () => message.success('删除成功'),
    });
  };

  const columns: ColumnsType<GroupTask> = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: '名称', dataIndex: 'name', ellipsis: true },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      render: (s: GroupTaskStatus) => {
        const m = STATUS_MAP[s] || { color: 'default', text: s };
        return <Tag color={m.color}>{m.text}</Tag>;
      },
    },
    {
      title: '子任务',
      width: 110,
      render: (_: unknown, r: GroupTask) => `${r.done_count}/${r.total_count}`,
    },
    {
      title: 'IOPS Avg',
      width: 120,
      render: (_: unknown, r: GroupTask) => r.summary?.iops_avg != null ? r.summary.iops_avg.toLocaleString() : '-',
    },
    {
      title: '带宽 Avg (MB/s)',
      width: 130,
      render: (_: unknown, r: GroupTask) => r.summary?.bw_avg != null ? r.summary.bw_avg.toFixed(1) : '-',
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      width: 160,
      render: (t: string) => formatTime(t),
    },
    {
      title: '操作',
      width: 130,
      render: (_: unknown, record: GroupTask) => (
        <Space>
          <Button type="link" size="small" icon={<EyeOutlined />} onClick={() => navigate(`/group-tasks/${record.id}`)}>
            详情
          </Button>
          <Popconfirm title="确认删除？将级联删除所有子任务" onConfirm={() => handleDelete(record.id)}>
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <h2 style={{ margin: 0 }}>多盘并发测试</h2>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateVisible(true)}>
          创建并发测试
        </Button>
      </div>

      <Table
        columns={columns}
        dataSource={data?.items}
        rowKey="id"
        loading={isLoading}
        pagination={{
          current: pagination.page,
          pageSize: pagination.pageSize,
          total: data?.total,
          showTotal: (total) => `共 ${total} 条`,
          onChange: (page, pageSize) => setPagination({ page, pageSize }),
        }}
        size="small"
      />

      <GroupTaskCreateModal visible={createVisible} onClose={() => setCreateVisible(false)} />
    </div>
  );
};

export default GroupTaskList;
