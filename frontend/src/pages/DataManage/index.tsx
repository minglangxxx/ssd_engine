import React, { useState } from 'react';
import {
  Table,
  Button,
  Space,
  Tag,
  Card,
  Row,
  Col,
  Statistic,
  Select,
  DatePicker,
  Radio,
  Popconfirm,
  message,
} from 'antd';
import {
  DownloadOutlined,
  InboxOutlined,
  DeleteOutlined,
  CompressOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { dataApi } from '@/api/data';
import { downloadBlob } from '@/utils/download';
import { formatTime, formatBytes } from '@/utils/format';
import { DATA_STATUS_MAP, DATA_TYPE_MAP } from '@/utils/constants';
import type { DataRecord, DataStatus, DataType } from '@/types/data';
import type { ColumnsType } from 'antd/es/table';

const { RangePicker } = DatePicker;

const DataManage: React.FC = () => {
  const qc = useQueryClient();
  const [filters, setFilters] = useState<{
    data_type?: DataType;
    status?: DataStatus;
    page: number;
    pageSize: number;
  }>({ page: 1, pageSize: 20 });
  const [selectedIds, setSelectedIds] = useState<number[]>([]);

  const { data, isLoading } = useQuery({
    queryKey: ['data-list', filters],
    queryFn: () => dataApi.list(filters),
  });

  const { data: overview } = useQuery({
    queryKey: ['data-overview'],
    queryFn: () => dataApi.getOverview(),
  });

  const downloadMutation = useMutation({
    mutationFn: ({ ids, format }: { ids: number[]; format: 'json' | 'csv' }) =>
      dataApi.download(ids, format),
    onSuccess: (blob) => {
      downloadBlob(blob as unknown as Blob, `data-export-${Date.now()}.zip`);
      message.success('下载成功');
    },
  });

  const archiveMutation = useMutation({
    mutationFn: dataApi.archive,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['data-list'] });
      qc.invalidateQueries({ queryKey: ['data-overview'] });
      message.success('归档成功');
      setSelectedIds([]);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: dataApi.delete,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['data-list'] });
      qc.invalidateQueries({ queryKey: ['data-overview'] });
      message.success('删除成功');
      setSelectedIds([]);
    },
  });

  const compressMutation = useMutation({
    mutationFn: dataApi.compress,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['data-list'] });
      qc.invalidateQueries({ queryKey: ['data-overview'] });
      message.success('压缩成功');
      setSelectedIds([]);
    },
  });

  const columns: ColumnsType<DataRecord> = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: '关联任务', dataIndex: 'task_id', width: 80, render: (v) => v ?? '-' },
    {
      title: '数据类型',
      dataIndex: 'data_type',
      width: 100,
      render: (t: DataType) => DATA_TYPE_MAP[t] || t,
    },
    { title: '节点', dataIndex: 'device_ip', width: 120 },
    {
      title: '大小',
      dataIndex: 'size_bytes',
      width: 100,
      render: (v: number) => formatBytes(v),
    },
    {
      title: '时间',
      dataIndex: 'created_at',
      width: 160,
      render: (t: string) => formatTime(t),
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 80,
      render: (s: DataStatus) => {
        const cfg = DATA_STATUS_MAP[s];
        return <Tag color={cfg?.color}>{cfg?.text || s}</Tag>;
      },
    },
    {
      title: '操作',
      width: 60,
      render: (_: unknown, record: DataRecord) => (
        <Button
          type="link"
          size="small"
          icon={<DownloadOutlined />}
          onClick={() => downloadMutation.mutate({ ids: [record.id], format: 'json' })}
        />
      ),
    },
  ];

  return (
    <div>
      <h2 style={{ marginBottom: 16 }}>数据管理</h2>

      {/* 存储概览 */}
      {overview && (
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={6}>
            <Card size="small">
              <Statistic
                title="活跃数据"
                value={overview.active_count}
                suffix={`条 (${formatBytes(overview.active_size_bytes)})`}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Statistic
                title="归档数据"
                value={overview.archived_count}
                suffix={`条 (${formatBytes(overview.archived_size_bytes)})`}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Statistic
                title="压缩数据"
                value={overview.compressed_count}
                suffix={`条 (${formatBytes(overview.compressed_size_bytes)})`}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Statistic title="即将过期" value={overview.expiring_soon_count} suffix="条" />
            </Card>
          </Col>
        </Row>
      )}

      {/* 筛选 */}
      <div style={{ marginBottom: 16, display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
        <Select
          value={filters.data_type}
          onChange={(v) => setFilters((f) => ({ ...f, data_type: v, page: 1 }))}
          options={[
            { value: undefined, label: '全部类型' },
            { value: 'fio_result', label: 'FIO结果' },
            { value: 'fio_trend', label: 'FIO趋势' },
            { value: 'host_monitor', label: '主机监控' },
            { value: 'disk_monitor', label: '磁盘监控' },
          ]}
          placeholder="数据类型"
          style={{ width: 140 }}
          size="small"
          allowClear
        />
        <Radio.Group
          value={filters.status || 'all'}
          onChange={(e) =>
            setFilters((f) => ({
              ...f,
              status: e.target.value === 'all' ? undefined : e.target.value,
              page: 1,
            }))
          }
          buttonStyle="solid"
          size="small"
        >
          <Radio.Button value="all">全部</Radio.Button>
          <Radio.Button value="active">活跃</Radio.Button>
          <Radio.Button value="archived">归档</Radio.Button>
          <Radio.Button value="compressed">压缩</Radio.Button>
        </Radio.Group>
      </div>

      {/* 表格 */}
      <Table
        columns={columns}
        dataSource={data?.items}
        rowKey="id"
        loading={isLoading}
        size="small"
        rowSelection={{
          selectedRowKeys: selectedIds,
          onChange: (keys) => setSelectedIds(keys as number[]),
        }}
        pagination={{
          current: filters.page,
          pageSize: filters.pageSize,
          total: data?.total,
          showTotal: (total) => `共 ${total} 条`,
          onChange: (page, pageSize) => setFilters((f) => ({ ...f, page, pageSize })),
        }}
      />

      {/* 批量操作 */}
      {selectedIds.length > 0 && (
        <Space style={{ marginTop: 12 }}>
          <span>已选 {selectedIds.length} 条</span>
          <Button
            icon={<DownloadOutlined />}
            onClick={() => downloadMutation.mutate({ ids: selectedIds, format: 'json' })}
            loading={downloadMutation.isPending}
          >
            批量下载
          </Button>
          {data?.items?.every((item) => data.items.find((r) => selectedIds.includes(r.id))?.status === 'active') && (
            <Button
              icon={<InboxOutlined />}
              onClick={() => archiveMutation.mutate(selectedIds)}
              loading={archiveMutation.isPending}
            >
              手动归档
            </Button>
          )}
          {data?.items?.every((item) => data.items.find((r) => selectedIds.includes(r.id))?.status === 'archived') && (
            <Button
              icon={<CompressOutlined />}
              onClick={() => compressMutation.mutate(selectedIds)}
              loading={compressMutation.isPending}
            >
              手动压缩
            </Button>
          )}
          <Popconfirm title="确认删除选中数据？" onConfirm={() => deleteMutation.mutate(selectedIds)}>
            <Button icon={<DeleteOutlined />} danger loading={deleteMutation.isPending}>
              手动删除
            </Button>
          </Popconfirm>
        </Space>
      )}
    </div>
  );
};

export default DataManage;
