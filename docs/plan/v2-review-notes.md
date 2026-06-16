# V2 前置改动 Review & 存疑记录

> 日期：2026-06-16 | 分支：feature_v2 | 关联详设：v2-prerequisites-design.md

---

## 已完成改动清单

### P-8: Task.result 增加 lat_p99 字段

| 文件 | 改动 |
|------|------|
| `agent/executor/fio_runner.py:318-350` | `_parse_result()` 增加 `latency_p99` 计算，复用 `_extract_percentile_value`，取多方向 max |
| `frontend/src/types/task.ts:51` | `TaskResult.latency` 增加 `p99?: number` 可选字段 |
| `frontend/src/pages/TaskDetail/index.tsx:101-103` | 新增 P99 延迟 Statistic 卡片 |

### P-9: Task 增加独立 raw_output 列（方案B落地）

| 文件 | 改动 |
|------|------|
| `backend/app/models/task.py:25,38-60` | 新增 `raw_output = db.Column(db.Text)` 列；`to_dict()` 增加 `include_raw` 参数，默认不返回 |
| `agent/executor/fio_runner.py:30` | `FioTask` 新增 `raw_output: str | None` 字段 |
| `agent/executor/fio_runner.py:89-93` | `_run()` success 分支将 `raw_reports[-1]` 写入 `task.raw_output`，不再混入 `result` |
| `agent/ingest_client.py:249-275` | `flush_task()` 新增 `raw_output` 关键字参数，非空时加入 payload |
| `backend/app/services/ingest_service.py:340-342` | `flush_task()` 新增对 `payload['raw_output']` 的独立写入 |
| `backend/app/services/task_service.py:115-125,166` | 新增 `get_raw()` 方法；`retry()` 时清空 `raw_output` |
| `backend/app/services/task_service.py:232-234` | `refresh_runtime_state()` 从远程 status_payload 中分离写入 `raw_output` |
| `backend/app/api/task.py:45-47` | 新增 `GET /tasks/<id>/raw` 端点 |
| `docs/plan/migration_add_raw_output.sql` | 数据库迁移脚本：加列 + 从已有 result 中提取 raw_json 迁移 |

### P-7: Feature / FW Log API 管道修复

| 文件 | 改动 |
|------|------|
| `backend/app/services/nvme_service.py:448-526` | 提取 `_extract_nvme_controller()` 和 `_run_nvme_cmd()` 辅助方法，5个 NVMe 命令方法统一委托 |
| `backend/app/api/nvme.py:58-69` | 新增 `get-feature` 和 `fw-log` 两个 API 路由 |
| `frontend/src/api/nvme.ts` | 新增 `getFeature()` 和 `getFwLog()` API 函数 |
| `frontend/src/types/nvme.ts:25-41` | 新增 `NvmeFeatureResponse` 和 `NvmeFwLogResponse` 类型 |
| `frontend/src/hooks/useNvme.ts:12,18-19` | `NvmeDetailType` 扩展，`queryFnMap` 增加 2 个条目 |
| `frontend/src/pages/DeviceDetail/NvmeListTab.tsx:81-86` | 新增 GET-FEATURE 和 FW-LOG 按钮 |
| `frontend/src/pages/DeviceDetail/NvmeDetailModal.tsx:98-112,194-241` | 提取 `renderKvDescriptions` 共享组件，新增 `renderGetFeature` 和 `renderFwLog` |

---

## Review 修复项（已修复）

| # | 问题 | 来源 | 修复 |
|---|------|------|------|
| 1 | NvmeService 5个方法大量复制粘贴样板代码 | Reuse Review | 提取 `_run_nvme_cmd` + `_extract_nvme_controller` 辅助方法 |
| 2 | `raw_json` 使用 `json.dumps` 双重序列化 | Efficiency Review | 改为从 stdout buffer 捕获原始 JSON 文本，避免二次序列化 |
| 3 | `NvmeDetailModal` 中 `loading`/`queryError` 不必要别名 | Quality Review | 直接使用 `isLoading`/`error` |
| 4 | `renderGetFeature` 与 `renderIdNs` 重复的键值描述渲染逻辑 | Quality Review | 提取 `renderKvDescriptions` 共享渲染函数 |
| 5 | `get_nvme_list` 中控制器正则独立内联，与 Service 其他位置不一致 | Reuse Review | 统一使用 `_extract_nvme_controller` |
| 6 | `raw_json` 嵌套在 result JSON 内导致列表/轮询 API 膨胀 | Efficiency Review | **方案B落地**：独立 `raw_output` TEXT 列，默认不返回 |

---

## 存疑 & 待确认项

### 1. FIO stdout 原始文本截断风险 [MEDIUM]

**现状**：`_extract_json_reports` 使用 `raw_decode` 从 buffer 中解析 JSON，保存 `buffer[cursor:end]` 作为原始文本。但如果 FIO 在两次 `raw_decode` 调用之间输出了非 JSON 文本（如警告信息），这些文本会被跳过，`raw_reports` 只包含有效的 JSON 片段。

**影响**：`raw_output` 保存的是「成功解析的 JSON 片段」而非「完整 stdout」，与设计文档中"保存 FIO 的完整 JSON 输出"的描述有细微偏差。

**待确认**：是否需要保存完整 stdout（含非 JSON 文本），还是仅保存有效 JSON 片段即可满足 SNIA 报告需求？

### 2. fid 参数验证 [LOW]

**现状**：`NvmeService.get_nvme_feature` 接受 `fid: str` 参数，但无任何校验。任意字符串均可传给 Agent 的 `nvme get-feature` 命令。

**待确认**：是否需要对 fid 做白名单校验（如 `0x01`~`0x10`），还是依赖 nvme-cli 自身错误返回即可？

### 3. get-feature 前端交互 [MEDIUM]

**现状**：前端 GET-FEATURE 按钮硬编码 `fid='0x06'`（Temperature Threshold），用户无法选择其他 Feature ID。

**待确认**：是否需要在点击 GET-FEATURE 后弹出 Feature ID 选择器（如下拉框），还是保持当前硬编码行为？

### 4. fw-log 返回结构未校验 [LOW]

**现状**：`NvmeFwLogResponse.data` 类型定义假设 `afi.active` 为数字、`frs` 为字符串数组。但不同厂商/固件版本的 nvme-cli 输出可能有差异。

**待确认**：是否需要在前端添加更多防御性类型检查，还是信任 Agent 端 nvme-cli 的标准输出格式？

→ **已修复（2026-06-16）**：`NvmeDetailModal.tsx renderFwLog` 中对 `active` 增加 `Number()` 转换，对 `frs` 增加 `Array.isArray` + `map(String)` 兜底。

---

## 二轮走读新增修复项

| # | 问题 | 来源 | 修复 |
|---|------|------|------|
| 1 | FIO stdout 原始文本截断风险 | 存疑项 #1 | `_consume_stdout` 用独立 `full_stdout` buffer 保存完整 stdout，与 JSON 解析解耦；`_extract_json_reports` 删除 `raw_reports` 参数 |
| 2 | fid 参数无校验 | 存疑项 #2 | `NvmeService.get_nvme_feature` 入口加正则 `^0x[0-9a-fA-F]{1,4}$`，不匹配返回 400 |
| 3 | get-feature fid 硬编码 0x06 | 存疑项 #3 | 新增 `FeatureSelectModal` 选择弹窗（预设列表 + 手动输入），`useNvmeDetail` 支持 fid 参数 |
| 4 | fw-log 返回结构无防御性校验 | 存疑项 #4 | `Number()` + `Array.isArray` + `map(String)` 兜底 |
| 5 | 旧任务 P99 卡片显示空 "-" | 测试项 #6 | `{result.latency?.p99 != null && <Col>...</Col>}` 条件渲染 |
| 6 | FeatureSelectModal onChange 类型不匹配 | 二轮代码走读 | Select 的 `onChange` 传 `string | number`，`setMode` 期望联合类型，加 `(v) => setMode(v as 'preset' | 'custom')` |
| 7 | failed 分支 raw_output 丢失 | 二轮代码走读 | fio 非零退出时也将 `full_stdout` 写入 `task.raw_output`，保留诊断输出 |
| 8 | Agent 离线时 RUNNING 状态无过期提示 | 二轮代码走读 | `refresh_runtime_state` 标记 `_agent_offline`，`to_dict()`/`get_status()` 透传 `stale: true`，前端 `TaskStatusBadge` 支持 `stale` 属性显示橙色"运行中(离线)" |

---

## 存疑项状态汇总

| # | 存疑项 | 原优先级 | 状态 | 修复说明 |
|---|--------|----------|------|----------|
| 1 | FIO stdout 截断风险 | MEDIUM | **已修复** | 独立 buffer 保存完整 stdout |
| 2 | fid 参数验证 | LOW | **已修复** | Service 层正则校验 |
| 3 | get-feature 前端交互 | MEDIUM | **已修复** | FeatureSelectModal 选择器 |
| 4 | fw-log 防御性校验 | LOW | **已修复** | 前端类型兜底 |

---

## 测试验证清单

| # | 测试场景 | 预期结果 |
|---|----------|----------|
| 1 | 创建 FIO 任务并等待完成 | `result.latency.p99` 有值；`raw_output` 列有原始 JSON 文本 |
| 2 | `GET /tasks` 列表接口 | 响应体中**不含** `raw_output` 字段 |
| 3 | `GET /tasks/<id>` 详情接口 | 响应体中**不含** `raw_output` 字段 |
| 4 | `GET /tasks/<id>/status` 轮询接口 | 响应体中**不含** `raw_output` 字段 |
| 5 | `GET /tasks/<id>/raw` 原始输出接口 | 返回 `{"data": {"task_id": X, "raw_output": "..."}}` |
| 6 | 旧任务（无 p99/raw_output）前端渲染 | P99 卡片不显示，无报错 |
| 7 | `GET /api/devices/<id>/nvme/<disk>/get-feature?fid=0x06` | 返回 Feature 数据 |
| 8 | `GET /api/devices/<id>/nvme/<disk>/fw-log` | 返回固件槽数据 |
| 9 | Agent 离线时请求 get-feature/fw-log | 返回 502 错误 |
| 10 | disk_name 传入 `nvme0n1` | Service 正则提取 `nvme0`，传 Agent `/dev/nvme0` |
| 11 | 执行 migration_add_raw_output.sql | 成功加列 + 已有数据中 raw_json 迁移到 raw_output |
