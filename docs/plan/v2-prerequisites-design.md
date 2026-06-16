# P-7 / P-8 / P-9 V2 前置改动详设文档

> 版本：v1.0 | 日期：2026-06-16 | 分支：feature_v2 | 关联详设：`docs/plan/v2-detailed-design.md §0 §6`

**架构边界声明**：本文档三项改动均位于实现层（P-8/P-9 改 Agent 内部解析逻辑，P-7 补全断裂管道），不涉及平台层或契约层变更，遵循 `v2-detailed-design.md §0` 的边界规则。

---

## P-8：Task.result 增加 lat_p99 字段

### 1. 需求说明

**现状**：Agent 端 `FioRunner._parse_result()` 返回的 result 结构为：
```python
{
  'iops': int, 'bandwidth': int,
  'read_iops': int, 'write_iops': int,
  'read_bw': int, 'write_bw': int,
  'latency': { 'mean': float, 'min': float, 'max': float }  # 均为 us
}
```
p99 延迟数据仅存在于 `FioTrendData` 趋势点中（`lat_p99` 字段），Task 最终结果中缺失。

**目标**：在 Task.result 的 `latency` 对象中增加 `p99` 字段，使回归比对（RG-1）和 SNIA 报告可使用最终的 p99 延迟值，不再依赖趋势点数据。

**影响范围**：Agent 端 `_parse_result()` + 前端 `TaskResult` 类型定义 + 前端 TaskDetail 页面渲染。后端 `IngestService.flush_task()` 和 `Task.to_dict()` 无需改动，因为它们是 JSON 透传。

### 2. 使用场景

1. **回归比对**：RG-1 计算 `lat_p99_diff` 时需要从 Task.result 中直接取 p99 值，而非从 FioTrendData 最后一个点取近似值
2. **SNIA 报告**：导出 SNIA 测试报告时需包含每轮的最终 p99 延迟
3. **固件升级验证**：FW-4 对比升级前后 p99 延迟差异

### 3. 后端设计（Agent 端）

#### 3.1 修改文件

`agent/executor/fio_runner.py` → `_parse_result()` 方法（行 303-363）

#### 3.2 修改逻辑

在 `_parse_result` 中，已有 `_extract_latency_stats` 和 `_extract_percentile_value` 用于趋势点构建。需复用相同逻辑在最终结果中提取 p99。

当前 `_parse_result` 遍历 jobs 的 read/write 方向提取 latency 时，已收集 `latency_samples`，但未提取 percentile。修改方案：在计算 mean/min/max 的同时，从 samples 中提取 p99 并按方向取 max。

#### 3.3 伪代码

```python
def _parse_result(self, report: dict[str, Any] | None) -> dict[str, Any]:
    # ... 现有逻辑不变（jobs 解析、iops/bw 计算、latency_samples 收集）...

    latency_p99 = 0.0
    if latency_samples:
        # 现有 mean/min/max 计算保持不变
        latency_mean = ...
        latency_min = ...
        latency_max = ...

        # 新增：从 samples 中取 p99 的最大值（代表最差方向的 p99）
        latency_p99 = max(
            self._convert_to_microseconds(
                self._extract_percentile_value(sample), float(sample.get('divisor', 1) or 1)
            )
            for sample in latency_samples
        )

    result = {
        'iops': read_iops + write_iops,
        'bandwidth': read_bw + write_bw,
        'read_iops': read_iops,
        'write_iops': write_iops,
        'read_bw': read_bw,
        'write_bw': write_bw,
        'latency': {
            'mean': latency_mean,
            'min': latency_min,
            'max': latency_max,
            'p99': round(latency_p99, 1),   # 新增，单位 us
        },
    }
    return result
```

#### 3.4 注意事项

- `_extract_percentile_value` 已有逻辑搜索 `'99.000000'`, `'99.00'`, `'99.0'`, `'99'` 四种 key，直接复用
- 若某个方向的 latency 统计中无 percentile 信息（某些 fio 版本输出差异），`_extract_percentile_value` 返回 0.0，max 取值不受影响
- `round(latency_p99, 1)` 保留一位小数，与趋势点精度一致

### 4. 后端设计（Server 端）**。Server 端 `Task.result` 为 JSON 列，`IngestService.flush_task()` 直接写入 payload.result，`Task.to_dict()` 直接返回 JSON。结构变更对 Server 透明。

### 5. 前端设计

#### 5.1 修改文件

`frontend/src/types/task.ts`（行 48-58）

#### 5.2 类型变更

```typescript
// 修改前
export interface TaskResult {
  iops: number;
  bandwidth: number;
  latency: { mean: number; min: number; max: number };
  read_iops?: number;
  // ...
}

// 修改后
export interface TaskResult {
  iops: number;
  bandwidth: number;
  latency: { mean: number; min: number; max: number; p99?: number };
  read_iops?: number;
  // ...
}
```

`p99` 为可选字段（`p99?`），确保旧数据（无 p99）不会导致前端报错。

#### 5.3 页面渲染变更

`frontend/src/pages/TaskDetail/index.tsx` 中结果摘要卡片需展示 p99 延迟：

```tsx
// 在现有 latency mean/max 展示之后追加
{task.result?.latency?.p99 != null && (
  <Descriptions.Item label="P99 延迟">
    {formatDuration(task.result.latency.p99)}  {/* us 单位，复用现有格式化 */}
  </Descriptions.Item>
)}
```

### 6. 联调校验

| 校验项 | 预期 |
|--------|------|
| Agent flush_task payload 中 result.latency.p99 类型 | float，单位 us |
| Server Task.result JSON 结构 | `{..., "latency": {"mean": X, "min": X, "max": X, "p99": Y}}` |
| 前端 TaskResult.latency.p99 | `number | undefined`，向后兼容 |
| 旧 Task 数据（无 p99）前端渲染 | 不展示 p99 行，无报错 |
| 回归模块读取 p99 | `task.result.get('latency', {}).get('p99')` 可为 None，需 fallback |

---

## P-9：Task.result 增加 raw_json 字段

### 1. 需求说明

**现状**：Agent 完成后仅上报摘要结果ops/bw/latency），FIO 原始 JSON 输出被丢弃。

**目标**：在 Task.result 中增加 `raw_json` 字段，保存 FIO 的完整 JSON 输出，用于 SNIA 报告导出及后续深度分析。

**影响范围**：Agent 端 `_run()` 方法的 finally 块 + `flush_task` 调用。Server 端无需改动（JSON 透传）。前端无感知（不需要渲染 raw_json）。

### 2. 使用场景

1. **SNIA 报告导出**：SN-8 需导出完整 FIO 输出，含 per-job 详情、IO depth 分布、latency histogram 等
2. **AI 深度分析**：V4 AI 根因分析需要 latency 分布直方图等完整数据
3. **问题排查**：当摘要指标异常时，需回溯完整输出定位原因

### 3. 后端设计（Agent 端）

#### 3.1 修改文件

`agent/executor/fio_runner.py` → `_run()` 方法（行 50-115）

#### 3.2 修改逻辑

在 `_run` 的 finally 块中，`ingest_client.flush_task()` 调用时传入的 result 已由 `_parse_result` 构建。需在 `_parse_result` 返回后，将最终 JSON report 序列化为字符串追加到 result 中。

关键点：`reports` 列表中最后一个元素即为 FIO 最终完整输出（含 `job options`、`fio version` 等元信息），但可能有多份 report（status-interval 中间报告 + 最终报告）。只需保存最终报告。

#### 3.3 伪代码

在 `_run()` 方法中，success 分支修改如下：

```python
# 修改前（行 87-90）
if task.process.returncode == 0:
    task.status = 'success'
    task.result = self._parse_result(reports[-1] if reports else None)
    task.error = None

# 修改后
if task.process.returncode == 0:
    task.status = 'success'
    task.result = self._parse_result(reports[-1] if reports else None)
    if task.result is not None and reports:
        task.result['raw_json'] = json.dumps(reports[-1], ensure_ascii=False)
    task.error = None
```

failed 分支无需变更——失败时 result 为 `{'error': ...}`，无 raw_json。

#### 3.4 注意事项

- `raw_json` 可能为大字符串（单 job ~50KB，多 job 可达数百 KB），需确认 MySQL JSON 列无长度限制问题。MySQL 5.7+ JSON 类型上限约 1GB，无实际限制
- 确保 `json.dumps` 使用 `ensure_ascii=False`，避免中文转义
- `IngestService.flush_task()` 已将 `result')` 直接写入 `task.result`（JSON 列），raw_json 字符串作为 result 的子字段会被正常序列化存储

### 4. 后端设计（Server 端）

**无需改动**。同 P-8，Server 对 Task.result JSON 透传。

### 5. 前端设计

**无前端改动**。raw_json 为服务端数据，仅供 SNIA 报告导出和 AI 分析使用。前端如需查看原始数据，后续可通过独立 API `GET /api/tasks/<id>/raw` 单独返回，不在本次范围内。

### 6. 联调校验

| 校验项 | 预期 |
|--------|------|
| Agent flush_task payload.result.raw_json 类型 | string（JSON 序列化后的字符串） |
| Server Task.result JSON 中 raw_json 字段 | 嵌套的 JSON 字符串，`SELECT JSON_EXTRACT(result, '$.raw_json')` 返回带引号的字符串 |
| SNIA 报告导出读取 raw_json | `json.loads(task.result['raw_json'])` 可还原完整 FIO 输出 |
| raw_json 数据完整性 | 包含 fio version、job options、timestamp、per-job read/write/clat/lat 完整节点 |

---

## P-7：Feature / FW Log API 管道修复

### 1. 需求说明

**现状**：Agent 端已暴露 `GET /nvme/<device>/get-feature` 和 `GET /nvme/<device>/fw-log` 两个 HTTP 端点（`agent_server.py` 行 365-383），Server 端 `AgentExecutor` 已封装 `get_nvme_feature()` 和 `get_nvme_fw_log()` 两个方法（`agent_executor.py` 行 148-161），但 Server 端 `NvmeService` 和 `nvme.py` API 层完全未接入这两个功能——管道在 Executor → Service 之间断裂。

**目标**：打通完整管道：前端按钮 → API 路由 → NvmeService → AgentExecutor → Agent HTTP 端点，使 get-feature 和 fw-log 功能可用。

**影响范围**：
- 后端：`nvme_service.py`（新增 2 个方法）、`nvme.py` 路由（新增 2 个端点）
- 前端：`nvme.ts` API（新增 2 个函数）、`useNvme.ts` hook（扩展类型枚举）、`NvmeListTab.tsx`（新增 2 个按钮）、`NvmeDetailModal.tsx`（新增 2 个渲染视图）

### 2. 使用场景

1. **Feature 查询**：用户点击 GET-FEATURE 按钮，选择 Feature ID（如 0x06 Write Cache），查看当前 NVMe Feature 设置值
2. **FW Slot 查看**：用户点击 FW-LOG 按钮，查看固件槽信息（7 个 slot、active 标注、各 slot 固件版本），固件升级验证需要读取 fw_before/fw_after

### 3. 后端设计

#### 3.1 修改文件

`backend/app/services/nvme_service.py`（行末追加）

#### 3.2 新增 NvmeService 方法

```python
@staticmethod
def get_nvme_feature(device_id: int, disk_name: str, fid: str = '0x06') -> dict:
    """查询 NVMe Feature 当前值"""
    device = Device.query.get(device_id)
    if device is None:
        raise ApiError('NOT_FOUND', '设备不存在', 404)

    # 设备名可能传 nvme0n1，但 get-feature 需要 nvme0（控制器）
    ctrl_match = re.match(r'^(nvme\d+)', disk_name)
    controller = ctrl_match.group(1) if ctrl_match else disk_name

    agent = AgentExecutor(f'http://{device.ip}:{device.agent_port}')
    try:
        with db_released():
            data = agent.get_nvme_feature(f'/dev/{controller}', fid)
        if not data:
            raise ApiError('NVME_CMD_FAILED', f'nvme get-feature 执行失败: fid={fid}', 502)
        return {
            'device_id': device.id,
            'disk_name': disk_name,
            'fid': fid,
            'data': data,
        }
    finally:
        agent.close()


@staticmethod
def get_nvme_fw_log(device_id: int, disk_name: str) -> dict:
    """查询 NVMe 固件槽日志"""
    device = Device.query.get(device_id)
    if device is None:
        raise ApiError('NOT_FOUND', '设备不存在', 404)

    ctrl_match = re.match(r'^(nvme\d+)', disk_name)
    controller = ctrl_match.group(1) if ctrl_match else disk_name

    agent = AgentExecutor(f'http://{device.ip}:{device.agent_port}')
    try:
        with db_released():
            data = agent.get_nvme_fw_log(f'/dev/{controller}')
        if not data:
            raise ApiError('NVME_CMD_FAILED', f'nvme fw-log 执行失败: {disk_name}', 502)
        return {
            'device_id': device.id,
            'disk_name': disk_name,
            'data': data,
        }
    finally:
        agent.close()
```

#### 3.3 联调校验

- `AgentExecutor.get_nvme_feature(device, fid)` 的 `device` 参数格式：`/dev/nvme0`（控制器设备），与 Agent 端 `GET /nvme/<path:device>/get-feature?fid=0x06` 对齐
- `AgentExecutor.get_nvme_fw_log(device)` 的 `device` 参数格式同上
- 返回的 `data` 字段直接透传 Agent 端 JSON 输出，不额外包装

#### 3.4 修改文件

`backend/app/api/nvme.py`（行末追加）

#### 3.5 新增 API 路由

```python
@api_bp.get('/devices/<int:device_id>/nvme/<disk_name>/get-feature')
def get_nvme_feature(device_id: int, disk_name: str):
    fid = request.args.get('fid', '0x06')
    result = NvmeService.get_nvme_feature(device_id, disk_name, fid)
    return success_response(result)


@api_bp.get('/devices/<int:device_id>/nvme/<disk_name>/fw-log')
def get_nvme_fw_log(device_id: int, disk_name: str):
    result = NvmeService.get_nvme_fw_log(device_id, disk_name)
    return success_response(result)
```

#### 3.6 联调校验

- 路由路径与现有 `id-ctrl`/`id-ns`/`error-log` 风格一致：`/devices/<device_id>/nvme/<disk_name>/<command>`
- `success_response()` 是项目现有封装，返回 `{"data": result}` 格式
- `fid` 参数默认 `0x06`（Write Cache），前端下拉选择时传不同值

### 4. 前端设计

#### 4.1 修改文件

`frontend/src/api/nvme.ts`

#### 4.2 新增 API 函数

```typescript
export const nvmeApi = {
  // ... 现有函数不变

  getFeature: (deviceId: number, diskName: string, fid: string = '0x06') =>
    request.get<unknown, NvmeFeatureResponse>(
      `/devices/${deviceId}/nvme/${diskName}/get-feature`,
      { params: { fid } }
    ),

  getFwLog: (deviceId: number, diskName: string) =>
    request.get<unknown, NvmeFwLogResponse>(
      `/devices/${deviceId}/nvme/${diskName}/fw-log`
    ),
};
```

#### 4.3 新增类型定义

`frontend/src/types/nvme.ts`

```typescript
// 现有接口保持不变，新增以下

export interface NvmeFeatureResponse {
  device_id: number;
  disk_name: string;
  fid: string;
  data: Record<string, unknown>;  // nvme get-feature 输出
}

export interface NvmeFwLogResponse {
  device_id: number;
  disk_name: string;
  data: {
    afi: { active: number };  // active firmware slot (1~7)
    frs: string[];             // 各 slot 固件版本，如 ["", "", "5B2QGXA7", ...]
  };
}
```

#### 4.4 修改 Hook

`frontend/src/hooks/useNvme.ts`

```typescript
// NvmeDetailType 扩展
export type NvmeDetailType = 'id-ctrl' | 'id-ns' | 'smart-log' | 'error-log' | 'get-feature' | 'fw-log' | null;

// queryFnMap 扩展
const queryFnMap: Record<string, () => Promise<unknown>> = {
  'id-ctrl': () => nvmeApi.getIdCtrl(deviceId, diskName),
  'id-ns': () => nvmeApi.getIdNs(deviceId, diskName),
  'smart-log': () => smartApi.getLatest(deviceId),
  'error-log': () => nvmeApi.getErrorLog(deviceId, diskName),
  'get-feature': () => nvmeApi.getFeature(deviceId, diskName, '0x06'),
  'fw-log': () => nvmeApi.getFwLog(deviceId, diskName),
};
```

#### 4.5 修改 NvmeListTab

`frontend/src/pages/DeviceDetail/NvmeListTab.tsx`

在操作列 `Space` 中追加两个按钮：

```tsx
<Button size="small" onClick={() => openModal(record.disk_name, 'get-feature')}>
  GET-FEATURE
</Button>
<Button size="small" onClick={() => openModal(record.disk_name, 'fw-log')}>
  FW-LOG
</Button>
```

#### 4.6 修改 NvmeDetailModal

`frontend/src/pages/DeviceDetail/NvmeDetailModal.tsx`

新增两个渲染函数：

```tsx
const renderGetFeature = () => {
  const resp = nvmeData as NvmeFeatureResponse | null;
  const data = resp?.data;
  if (!data) return <Empty description="无 Feature 数据" />;
  const entries = Object.entries(data).filter(
    ([, v]) => v !== undefined && v !== null && v !== ''
  );
  return (
    <Descriptions bordered column={2} size="small">
      {entries.map(([k, v]) => (
        <Descriptions.Item key={k} label={k}>
          {typeof v === 'object' ? JSON.stringify(v) : String(v)}
        </Descriptions.Item>
      ))}
    </Descriptions>
  );
};

const renderFwLog = () => {
  const resp = nvmeData as NvmeFwLogResponse | null;
  const data = resp?.data;
  if (!data) return <Empty description="无固件日志" />;
  const activeSlot = data.afi?.active ?? 0;
  const frs = data.frs ?? [];

  // 固件槽可视化：7 个 slot，标注 active 和已安装
  const slots = Array.from({ length: 7 }, (_, i) => {
    const slotNum = i + 1;
    const fw = (frs[i] || '').trim();
    const isActive = slotNum === activeSlot;
    return { slotNum, fw, isActive };
  });

  return (
    <>
      <Descriptions bordered column={1} size="small" style={{ marginBottom: 16 }}>
        <Descriptions.Item label="当前激活槽">Slot {activeSlot}</Descriptions.Item>
      </Descriptions>
      <Table
        dataSource={slots}
        rowKey="slotNum"
        size="small"
        pagination={false}
        columns={[
          { title: 'Slot', dataIndex: 'slotNum', width: 80 },
          {
            title: '固件版本',
            dataIndex: 'fw',
            render: (fw: string) => fw || '(空)',
          },
          {
            title: '状态',
            dataIndex: 'isActive',
            width: 100,
            render: (active: boolean) =>
              active ? <Tag color="green">Active</Tag> : <Tag>空闲</Tag>,
          },
        ]}
      />
    </>
  );
};
```

在 `renderContent` 的 switch 中追加：

```tsx
case 'get-feature': return renderGetFeature();
case 'fw-log': return renderFwLog();
```

在 `titleMap` 中追加：

```tsx
'get-feature': `NVMe GET-FEATURE - ${diskName}`,
'fw-log': `NVMe FW-LOG - ${diskName}`,
```

### 5. 联调校验清单

| # | 校验项 | 预期 |
|---|--------|------|
| 1 | `GET /api/devices/<id>/nvme/<disk>/get-feature?fid=0x06` 返回 | `{"data": {"device_id": 1, "disk_name": "nvme0n1", "fid": "0x06", "data": {...}}}` |
| 2 | `GET /api/devices/<id>/nvme/<disk>/fw-log` 返回 | `{"data": {"device_id": 1, "disk_name": "nvme0n1", "data": {"afi": {"active": 1}, "frs": ["5B2QGXA7", "", ...]}}}` |
| 3 | 前端点击 GET-FEATURE 按钮 | 打开 Modal，展示 key-value Descriptions |
| 4 | 前端点击 FW-LOG 按钮 | 打开 Modal，展示 7 行 slotactive 行绿色 Tag |
| 5 | Agent 离线时请求 | 返回 502 `{"error": {"code": "NVME_CMD_FAILED", ...}}` |
| 6 | disk_name 传入 `nvme0n1` | Service 层正则提取 `nvme0`，传给 Agent `/dev/nvme0` |
| 7 | fid 传入非标准值（如 `0x02`） | Agent 端透传 nvme-cli，返回对应 Feature 数据或 502 |

### 6. Agent 端已实现功能确认

| Agent 端点 | 对应 nvme-cli 命令 | 已有代码位置 | 状态 |
|-----------|-------------------|-------------|------|
| `GET /nvme/<device>/get-feature` | `nvme get-feature {device} -f {fid} -o json` | `agent_server.py:365-373` | ✅ 已实现 |
| `GET /nvme/<device>/fw-log` | `nvme fw-log {device} -o json` | `agent_server.py:376-383` | ✅ 已实现 |
| `AgentExecutor.get_nvme_feature()` | 调用 Agent 上述端点 | `agent_executor.py:148-154` | ✅ 已实现 |
| `AgentExecutor.get_nvme_fw_log()` | 调用 Agent 上述端点 | `agent_executor.py:156-161` | ✅ 已实现 |

断裂点确认：`NvmeService` + `nvme.py` 路由缺失 → 本次补全。

---

## 实施顺序与依赖

```
P-8 (lat_p99) ──→ 可独立开发，无外部依赖
P-9 (raw_json) ──→ 可独立开发，无外部依赖
P-7 (管道修复) ──→ 可独立开发，无外部依赖

三者互不依赖，可并行开发。
```

**推荐实施顺序**：P-8 → P-7 → P-9

理由：
- P-8 最小改动（Agent 1 处 + 前端 1 类型 + 1 行渲染），可快速验证端到端流程
- P-7 改动涉及 3 层（Service + Route + 前端 3 文件），复杂度中等，在 P-8 基础上确认 Agent 通信链路正常后再做更安心
- P-9 改动最小（Agent 2 行），优先级最低

**总工作量估算**：

| 任务 | Agent | Server | 前端 | 联调 | 合计 |
|------|-------|--------|------|------|------|
| P-8 | 0.5d | 0d | 0.3d | 0.2d | 1d |
| P-9 | 0.3d | 0d | 0d | 0.2d | 0.5d |
| P-7 | 0d | 0.5d | 1d | 0.5d | 2d |
| **合计** | **0.8d** | **0.5d** | **1.3d** | **0.9d** | **3.5d** |
