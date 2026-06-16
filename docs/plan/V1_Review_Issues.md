# V1 实施审查与待确认问题

> 编码完成后的 review 记录，标注存疑、不完善或需求不明确的地方，等待检查。

---

## 一、已完成的变更清单

### 后端 (Backend)

| 文件 | 变更 |
|------|------|
| `backend/app/models/device.py` | 新增 hostname/os_version/kernel_version/cpu_usage/memory_usage 字段 + to_dict(include_disks) |
| `backend/app/services/device_status_checker.py` | _check_single_device 改用 get_health() 直接获取主机信息，去掉重复 test_connection；在线时写入主机字段，离线清空 cpu/mem |
| `backend/app/services/device_service.py` | get_agent_status 扩展：在线时写入 hostname/os/kernel/cpu/mem，离线清空 cpu/mem |
| `backend/app/services/dashboard_service.py` | 新增文件：DashboardService.get_summary() 含 5s 缓存 |
| `backend/app/api/dashboard.py` | 新增文件：GET /api/dashboard/summary |
| `backend/app/api/__init__.py` | 注册 dashboard 模块 |
| `backend/app/schemas/device.py` | DeviceTestConnectionRequest 的 user/password 改为 optional |
| `backend/app/executors/agent_executor.py` | 新增 get_nvme_feature() 和 get_nvme_fw_log() 方法 |
| `backend/init_mysql.sql` | 已包含 5 条 add_column_if_missing 调用（之前的提交） |

### Agent

| 文件 | 变更 |
|------|------|
| `agent/agent_server.py` | /health 扩展返回 hostname/os_version/kernel_version/cpu_usage/memory_usage（含 try/except 保护）；新增 /nvme/<device>/get-feature 和 /nvme/<device>/fw-log 端点 |

### 前端 (Frontend)

| 文件 | 变更 |
|------|------|
| `frontend/src/api/dashboard.ts` | 新增文件：DashboardSummary/RecentTask/ChartDataPoint 类型 + dashboardApi |
| `frontend/src/hooks/useDashboard.ts` | 新增文件：useDashboardSummary (5s refetch) |
| `frontend/src/pages/Dashboard/index.tsx` | 全面改造：真实数据 + CPU/MEM 卡片 + 双 Y 轴折线图 + 空状态 + 5s 刷新 |
| `frontend/src/api/index.ts` | 导出 dashboardApi |
| `frontend/src/types/device.ts` | Device 类型新增 hostname/os_version/kernel_version/cpu_usage/memory_usage |
| `frontend/src/pages/DeviceManage/index.tsx` | 表格新增主机信息列 + refetchInterval: 30000 |
| `frontend/src/pages/DeviceDetail/BasicInfoTab.tsx` | Descriptions 新增主机信息行 + 测试连接不再硬编码 user |
| `frontend/src/api/device.ts` | testConnection 删除默认密码逻辑，参数类型改为可选 |
| `frontend/src/hooks/useNvme.ts` | 新增 smart-log 类型映射，导出 NvmeDetailType |
| `frontend/src/pages/DeviceDetail/NvmeListTab.tsx` | modal 类型对齐 NvmeDetailType |
| `frontend/src/pages/DeviceDetail/NvmeDetailModal.tsx` | 统一使用 useNvmeDetail 处理所有类型含 smart-log，移除 useSmartLatest 隐式依赖 |

---

## 二、待手动删除的文件

以下文件应删除但因环境限制未能自动删除：

| 文件 | 原因 |
|------|------|
| `frontend/src/hooks/useWebSocket.ts` | V1 不使用 WebSocket，HTTP 轮询已足够 |
| `frontend/src/stores/taskStore.ts` | 零消费方，冗余代码 |

---

## 三、存疑与待确认问题

### 3.1 DeviceService.test_connection 中 `del user; del password` 的处理

**现状**：`test_connection` 方法仍然接收 `user` 和 `password` 参数，然后立即 `del` 丢弃它们。Schema 已改为可选（`default=None`），后端实际仅检测 Agent HTTP 可达性。

**存疑**：
- `del user; del password` 这两行是否需要保留？既然 Schema 已改为可选且后端不使用，是否应该直接从方法签名中移除这两个参数？
- 如果未来需要支持 SSH 连接测试，是否需要预留这些参数？

**建议**：当前保留不影响功能，但语义上不清晰。可在后续迭代中清理。

---

### 3.2 NvmeDetailModal 对 smart-log 的数据获取方式

**变更内容**：将 smart-log 数据获取从 `useSmartLatest` 独立调用改为通过 `useNvmeDetail` 统一入口，映射到 `smartApi.getLatest(deviceId)`。

**存疑**：
- `smartApi.getLatest(deviceId)` 返回的是该设备下**所有磁盘**的 SMART 数据（含 disks 数组），而 `useNvmeDetail` 的其他类型（id-ctrl/id-ns/error-log）是按单个磁盘维度请求。这是否会导致：
  1. `useNvmeDetail` 的 `queryKey` 包含 `diskName`，但 smart-log 请求实际不需要 diskName 参数。缓存可能在切换磁盘时产生不必要的新请求。
  2. 获取到的是全量 disks 数组，需在前端二次过滤 `diskName`，与其他类型直接返回目标数据的模式不一致。

**替代方案**：保持 NvmeDetailModal 原有的两路数据获取模式（smart-log 走 useSmartLatest，其余走 useNvmeDetail），但将 NvmeListTab 的类型联合与 NvmeDetailModal 的 type prop 对齐。

**建议**：当前实现功能正确，但缓存策略需在实际联调时验证。如果发现不必要的重复请求，可回退到原有方案。

---

### 3.3 DashboardService 中 avg_cpu/avg_memory 的 null 语义

**现状**：当没有在线设备或在线设备无 CPU/MEM 数据时，`avg_cpu` 和 `avg_memory` 返回 `null`。

**前端处理**：使用 `summary?.avg_cpu ?? '--'` 显示为 `--`。

**存疑**：
- 是否需要区分"无在线设备"和"在线设备但无数据"两种情况？目前两者都显示 `--`。
- 0.0% 和 null 是否需要不同的展示？（0% = 在线但 CPU 使用率为 0，null = 无数据）

**建议**：当前行为合理，null 表示无数据，0 表示有数据但值为 0，前端已正确区分。

---

### 3.4 chart_data 中的时间格式

**现状**：`chart_data` 的 `time` 字段使用 `to_beijing_iso(t.finished_at)` 输出 ISO 格式字符串。

**存疑**：
- ECharts X 轴直接使用 ISO 格式字符串（如 `2026-06-15T14:30:00+08:00`），是否需要在前端格式化为更友好的展示（如 `06-15 14:30`）？
- 当前未做格式化，如果数据点少于 5 个，X 轴标签可能显得过宽。

**建议**：联调时根据实际数据显示效果决定是否需要格式化。

---

### 3.5 Agent /health 端点的 cpu_usage_percent 和 mem_usage_percent 字段名映射

**现状**：Agent 端 collector 原始字段名为 `cpu_usage_percent` 和 `mem_usage_percent`，在 `/health` handler 中映射为 `cpu_usage` 和 `memory_usage`（按 7.2.2 字段映射表）。

**验证点**：
- 后端 `DeviceStatusChecker` 读取 `health.get('cpu_usage')` 和 `health.get('memory_usage')`，与 Agent 输出对齐。
- 需要确认 `CpuCollector.collect()` 在 `/proc` 不可用时确实抛出异常（而非返回空 dict），因为 `/health` 用 try/except 捕获后返回空默认值。当前 CpuCollector 在异常时 `raise`，行为正确。

---

### 3.6 Dashboard 缓存的线程安全

**现状**：`DashboardService` 使用模块级 `_cache` dict + `time.time()` 实现简单的 TTL 缓存。

**存疑**：
- Flask 使用多线程（`ThreadPoolExecutor`），多个并发请求可能同时读写 `_cache`。
- Python GIL 保证 dict 的单个操作原子性，但 `now - cached[0] < CACHE_TTL` 的读-比较不是原子的。
- 极端情况下可能有两个请求同时判定缓存过期并都查 DB，但这只导致多一次查询，不会导致数据错误。

**建议**：V1 可接受。如果后续高并发场景下 DB 压力大，可改为线程锁或 Redis。

---

### 3.7 V2.5 预留端点未测试

**现状**：Agent 端 `/nvme/<device>/get-feature` 和 `/nvme/<device>/fw-log`，以及 AgentExecutor 的 `get_nvme_feature()` 和 `get_nvme_fw_log()` 已实现但未暴露 Server API 路由。

**确认**：按照计划文档 7.2.1，V2.5 端点 V1 不作为验收项，未测试的代码路径不应阻塞 V1 发布。

---

### 3.8 DeviceManage 列宽度调整

**新增了 6 列（hostname/os/kernel/cpu/mem）**，总计约 800px 宽度，原有表格宽度约 700px。总宽度可能超出屏幕。

**建议**：联调时验证表格是否需要增加 `scroll={{ x: 1400 }}` 属性来支持水平滚动，或调整列宽/省略部分列。

---

### 3.9 DeviceInfo 类型未扩展主机字段

**现状**：`DeviceInfo extends Omit<Device, 'disks'>`，继承了 Device 新增的 hostname/os_version/kernel_version/cpu_usage/memory_usage 字段。

**确认**：由于 DeviceInfo 是 Device 的超集（仅 disks 类型不同），主机字段自动继承，不需要额外修改。正确。

---

## 四、需要在实际环境验证的项

| # | 验证项 | 前置条件 |
|---|--------|---------|
| 1 | Agent `/health` 返回扩展字段 | Agent 启动在 Linux 环境（有 /proc 和 psutil） |
| 2 | Server 30s 内同步主机信息到 Device 表 | Server + Agent 同时运行 |
| 3 | 新增设备即时获取主机信息 | 创建设备后调用 get_agent_status |
| 4 | Dashboard 5s 自动刷新 | 浏览器打开 Dashboard 页面 |
| 5 | Dashboard 双 Y 轴图表正确显示 | 至少有 1 条已完成且含 iops 的任务 |
| 6 | DeviceManage 表格主机列显示 | 设备在线/离线切换 |
| 7 | NvmeListTab SMART-LOG modal 正常 | 点击 SMART-LOG 按钮 |
| 8 | 前端无硬编码密码 | 审查 Network 请求 |
