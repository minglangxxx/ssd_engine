import React, { useState } from 'react';
import { Table, Button, Space, Select, Tag, message, Modal, InputNumber } from 'antd';
import { useNavigate, useLocation } from 'react-router-dom';
import { useRegressionList, useRunRegression } from '@/hooks/useRegression';
import { useBaselineList } from '@/hooks/useBaseline';
import { formatTime } from '@/utils/format';
import type { RegressionResult, RegressionVerdict } from '@/types/regression';
import type { ColumnsType } from 'antd/es/table';

const verdictColor: Record<RegressionVerdict, string> = {
  PASS: 'green',
  WARNING: 'orange',
  FAIL: 'red',
};

const RegressionList: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const stateTaskId = (location.state as { taskId?: number } | undefined)?.taskId;

  React.useEffect(() => {
    if (stateTaskId != null) {
      navigate(location.pathname, { replace: true, state: {} });
    }
  }, [stateTaskId]); // eslint-disable-line react-hooks/exhaustive-deps

  const [pagination, setPagination] = useState({ page: 1, pageSize: 10 });
  const [verdictFilter, setVerdictFilter] = useState<string | undefined>();
  const [runModalVisible, setRunModalVisible] = useState(stateTaskId != null);
  const [selectedBaselineId, setSelectedBaselineId] = useState<number | undefined>();
  const [preselectedTaskId, setPreselectedTaskId] = useState<number | undefined>(stateTaskId);

  const { data, isLoading } = useRegressionList({
    verdict: verdictFilter as RegressionVerdict | undefined,
    ...pagination,
  });
  const { data: baselines } = useBaselineList({ pageSize: 100 });
  const { mutate: runRegression, isPending: running } = useRunRegression();

  const handleRun = () => {
    if (!preselectedTaskId || !selectedBaselineId) {
      message.warning('请选择任务和基线');
      return;
    }
    runRegression(
      { task_id: preselectedTaskId, baseline_id: selectedBaselineId },
      {
        onSuccess: (result) => {
          message.success('回归比对完成');
          setRunModalVisible(false);
          navigate(`/regressions/${result.id}`);
        },
      },
    );
  };

  const columns: ColumnsType<RegressionResult> = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: '任务ID', dataIndex: 'task_id', width: 80 },
    { title: '基线ID', dataIndex: 'baseline_id', width: 80 },
    {
      title: '判定结果',
      dataIndex: 'verdict',
      width: 100,
      render: (v: RegressionVerdict) => <Tag color={verdictColor[v]}>{v}</Tag>,
    },
    {
      title: 'IOPS差异%',
      dataIndex: 'iops_diff',
      width: 100,
      render: (v: number | null) => v != null ? `${v > 0 ? '+' : ''}${v}%` : '-',
    },
    {
      title: '带宽差异%',
      dataIndex: 'bw_diff',
      width: 100,
      render: (v: number | null) => v != null ? `${v > 0 ? '+' : ''}${v}%` : '-',
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      width: 160,
      render: (t: string) => formatTime(t),
    },
    {
      title: '操作',
      width: 80,
      render: (_: unknown, record: RegressionResult) => (
        <Button type="link" size="small" onClick={() => navigate(`/regressions/${record.id}`)}>
          查看
        </Button>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <h2 style={{ margin: 0 }}>回归测试</h2>
        <Button type="primary" onClick={() => setRunModalVisible(true)}>
          执行回归比对
        </Button>
      </div>

      <div style={{ marginBottom: 16 }}>
        <Select
          placeholder="按判定结果筛选"
          value={verdictFilter}
          onChange={(v) => { setVerdictFilter(v); setPagination((p) => ({ ...p, page: 1 })); }}
          allowClear
          style={{ width: 160 }}
          size="small"
          options={[
            { label: 'PASS', value: 'PASS' },
            { label: 'WARNING', value: 'WARNING' },
            { label: 'FAIL', value: 'FAIL' },
          ]}
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

      <Modal
        title="执行回归比对"
        open={runModalVisible}
        onCancel={() => setRunModalVisible(false)}
        onOk={handleRun}
        okText="确认"
        cancelText="取消"
        confirmLoading={running}
        width={440}
      >
        <div style={{ marginBottom: 12 }}>
          <div style={{ marginBottom: 4 }}>任务ID</div>
          <InputNumber
            style={{ width: '100%' }}
            placeholder="输入已完成任务的ID"
            value={preselectedTaskId}
            onChange={(v) => setPreselectedTaskId(v ?? undefined)}
          />
        </div>
        <div style={{ marginBottom: 12 }}>
          <div style={{ marginBottom: 4 }}>选择基线</div>
          <Select
            placeholder="选择基线"
            value={selectedBaselineId}
            onChange={setSelectedBaselineId}
            style={{ width: '100%' }}
            options={(baselines?.items || []).map((b) => ({
              label: `#${b.id} ${b.name}`,
              value: b.id,
            }))}
          />
        </div>
      </Modal>
    </div>
  );
};

export default RegressionList;
