import React, { useState } from 'react';
import { Table, Button, Space, Input, Popconfirm, message, Tag } from 'antd';
import { SearchOutlined, EyeOutlined, DeleteOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useBaselineList, useDeleteBaseline } from '@/hooks/useBaseline';
import { formatTime, formatNumber } from '@/utils/format';
import type { Baseline } from '@/types/baseline';
import type { ColumnsType } from 'antd/es/table';

const BaselineList: React.FC = () => {
  const navigate = useNavigate();
  const [keyword, setKeyword] = useState('');
  const [pagination, setPagination] = useState({ page: 1, pageSize: 10 });

  const { data, isLoading } = useBaselineList({
    keyword: keyword || undefined,
    ...pagination,
  });
  const { mutate: deleteBaseline } = useDeleteBaseline();

  const handleDelete = (id: number) => {
    deleteBaseline(id, {
      onSuccess: () => message.success('删除成功'),
    });
  };

  const columns: ColumnsType<Baseline> = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: '名称', dataIndex: 'name', ellipsis: true },
    { title: '设备型号', dataIndex: 'device_model', width: 150, render: (v: string | null) => v || '-' },
    { title: '固件版本', dataIndex: 'firmware', width: 120, render: (v: string | null) => v || '-' },
    {
      title: 'IOPS',
      width: 100,
      render: (_: unknown, r: Baseline) => r.result?.iops != null ? formatNumber(r.result.iops) : '-',
    },
    {
      title: '带宽(MB/s)',
      width: 110,
      render: (_: unknown, r: Baseline) => r.result?.bandwidth != null ? formatNumber(r.result.bandwidth) : '-',
    },
    {
      title: '平均延迟(μs)',
      width: 120,
      render: (_: unknown, r: Baseline) => r.result?.latency?.mean != null ? r.result.latency.mean.toFixed(1) : '-',
    },
    { title: '来源任务', dataIndex: 'source_task_id', width: 90, render: (v: number) => <Button type="link" size="small" onClick={() => navigate(`/tasks/${v}`)}>{v}</Button> },
    { title: '创建时间', dataIndex: 'created_at', width: 160, render: (t: string) => formatTime(t) },
    {
      title: '操作',
      width: 130,
      render: (_: unknown, record: Baseline) => (
        <Space>
          <Button type="link" size="small" icon={<EyeOutlined />} onClick={() => navigate(`/baselines/${record.id}`)}>
            查看
          </Button>
          <Popconfirm title="确认删除？删除后不可恢复" onConfirm={() => handleDelete(record.id)}>
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
        <h2 style={{ margin: 0 }}>基线管理</h2>
      </div>

      <div style={{ marginBottom: 16, display: 'flex', gap: 16 }}>
        <Input
          placeholder="搜索基线名称"
          prefix={<SearchOutlined />}
          value={keyword}
          onChange={(e) => { setKeyword(e.target.value); setPagination((p) => ({ ...p, page: 1 })); }}
          style={{ width: 260 }}
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
    </div>
  );
};

export default BaselineList;
