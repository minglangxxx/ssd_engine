import React, { useState } from 'react';
import { Table, Button, Space, Input, Radio, Popconfirm, message } from 'antd';
import { PlusOutlined, SearchOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useTaskList, useDeleteTask } from '@/hooks/useTask';
import TaskStatusBadge from '@/components/TaskStatusBadge/index';
import TaskCreateModal from '@/components/TaskCreateModal/index';
import { formatTime } from '@/utils/format';
import type { Task, TaskStatus } from '@/types/task';
import type { ColumnsType } from 'antd/es/table';

const TaskList: React.FC = () => {
  const navigate = useNavigate();
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [keyword, setKeyword] = useState('');
  const [pagination, setPagination] = useState({ page: 1, pageSize: 10 });

  const { data, isLoading, refetch } = useTaskList({
    status: statusFilter as TaskStatus | 'all',
    keyword: keyword || undefined,
    ...pagination,
  });
  const { mutate: deleteTask } = useDeleteTask();

  const handleDelete = (id: number) => {
    deleteTask(id, {
      onSuccess: () => message.success('删除成功'),
    });
  };

  const columns: ColumnsType<Task> = [
    { title: 'ID', dataIndex: 'id', width: 80 },
    { title: '任务名称', dataIndex: 'name', ellipsis: true },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      render: (s: TaskStatus) => <TaskStatusBadge status={s} />,
    },
    { title: '设备IP', dataIndex: 'device_ip', width: 140 },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      width: 170,
      render: (t: string) => formatTime(t),
    },
    {
      title: '操作',
      width: 140,
      render: (_: unknown, record: Task) => (
        <Space>
          <Button type="link" size="small" onClick={() => navigate(`/tasks/${record.id}`)}>
            查看
          </Button>
          <Popconfirm title="确认删除？" onConfirm={() => handleDelete(record.id)}>
            <Button type="link" size="small" danger>
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
        <h2 style={{ margin: 0 }}>任务管理</h2>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => setCreateModalVisible(true)}
        >
          创建任务
        </Button>
      </div>

      <div style={{ marginBottom: 16, display: 'flex', gap: 16, alignItems: 'center' }}>
        <Radio.Group
          value={statusFilter}
          onChange={(e) => {
            setStatusFilter(e.target.value);
            setPagination((p) => ({ ...p, page: 1 }));
          }}
          buttonStyle="solid"
          size="small"
        >
          <Radio.Button value="all">全部</Radio.Button>
          <Radio.Button value="PENDING">等待中</Radio.Button>
          <Radio.Button value="RUNNING">运行中</Radio.Button>
          <Radio.Button value="SUCCESS">成功</Radio.Button>
          <Radio.Button value="FAILED">失败</Radio.Button>
        </Radio.Group>
        <Input
          placeholder="搜索任务名称"
          prefix={<SearchOutlined />}
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
          onPressEnter={() => refetch()}
          style={{ width: 240 }}
          size="small"
          allowClear
        />
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

      <TaskCreateModal
        visible={createModalVisible}
        onClose={() => setCreateModalVisible(false)}
        onSuccess={() => {
          setCreateModalVisible(false);
          refetch();
        }}
      />
    </div>
  );
};

export default TaskList;
