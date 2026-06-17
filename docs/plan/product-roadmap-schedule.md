# SSD Engine 产品规划 — 详细排期与实现状态

> 基于文档 `docs/plan/SSD_Engine_Plan.md` 逐项标注实现状态，生成可追踪的排期表。
> 最近更新：2026-06-17（V2 核心功能全部完成，3 轮代码审查 29 项修复已合入）

---

## 状态说明

| 标记 | 含义 |
|------|------|
| ✅ 已实现 | 代码中已有完整实现 |
| 🔧 已实现需优化 | 功能已有，但存在缺陷或需要迭代增强 |
| 🚧 部分实现 | 核心路径已通，但缺少部分子功能 |
| ❌ 未实现 | 代码中无对应实现 |

---

## V1 基础测试平台（第1~4周）

### 功能1 Agent 管理

| 子任务 | 排期 | 状态 | 说明 |
|--------|------|------|------|
| Agent 数据模型（agent 表） | W1D1 | ✅ 已实现 | `Device` 模型包含规划全部10个字段：id, hostname, ip, os_version, kernel_version, cpu_usage, memory_usage, agent_status(对应status), last_heartbeat, created_at；额外增加 name/ssh_user/ssh_password/agent_port/agent_version/updated_at 字段；`status` 重命名为 `agent_status` |
| Agent 心跳上报接口 `POST /api/agent/heartbeat` | W1D1 | ✅ 已实现 | 已改造为 Agent-Push 模式：Agent 每30秒 POST 心跳到 `POST /api/internal/ingest/heartbeat`，Server 端 `IngestService.ingest_heartbeat` 更新 Device 行（agent_status/last_heartbeat/hostname/os_version/kernel_version/cpu_usage/memory_usage/agent_version） |
| Agent 列表接口 `GET /api/agent/list` | W1D1 | ✅ 已实现 | 等价接口 `GET /api/devices` 返回全部设备列表，字段完整覆盖规划要求 |
| Agent 详情接口 `GET /api/agent/<id>` | W1D1 | 🔧 已实现需优化 | 现有 `GET /api/devices/<id>/info` 返回设备信息+Agent实时磁盘列表；无简单的"按ID获取存储记录"接口 |
| Agent 心跳脚本（agent_daemon.py，每30秒 POST） | W1D2 | ✅ 已实现 | 心跳逻辑已集成到 Agent 的 `collect_background()` 循环中（每 HEARTBEAT_INTERVAL_SECONDS 调用 `ingest_client.enqueue_heartbeat`），无需独立 daemon 脚本 |
| Celery Beat 扫描超时 Agent 置 offline | W1D3 | ✅ 已实现 | 已改造为超时扫描模式：`DeviceStatusChecker` 使用 APScheduler 每30秒执行 `check_all_agents`，批量将 `last_heartbeat` 超过90秒的 online 设备标为 offline（单条 SQL，O(1) 复杂度） |
| 前端 Agent 列表页 | W1D4 | 🔧 已实现需优化 | `DeviceManage` 页面展示 IP/名称/状态/版本/主机名/OS/内核/CPU%/MEM%/心跳时间/操作；轮询间隔为30秒（规划10秒）；有增删改查功能 |
| 联调验证 | W1D5 | ✅ 已实现 | 基本链路已通：Agent 心跳上报 → Server 状态更新 → 前端展示 |

**小结**：Agent 管理核心链路已通且数据模型字段完整，心跳架构已从 Server-Pull 改造为 Agent-Push 模式，与规划对齐。

---

### 功能2 FIO 测试

| 子任务 | 排期 | 状态 | 说明 |
|--------|------|------|------|
| Task 数据模型 | W2D1 | 🔧 已实现需优化 | `Task` 模型字段覆盖更广：含 device_id/device_ip/device_path/fault_type/retention_policy/data_window_start/end 等；`config` 对应规划的 `fio_config`；`SUCCESS` 对应规划的 `done`；无 `agent_id`（用 device_id+device_ip 替代）；无 `raw_json`（原始 FIO JSON 未持久化）；无 `lat_p99`（仅存于 FioTrendData 趋势点，Task.result 中缺失） |
| 创建任务接口 `POST /api/task/create` | W2D1 | ✅ 已实现 | `POST /api/tasks` 支持引导式（含7种预设模板+9个高级配置Tab）和原生命令两种模式，含 FioConfigValidator 校验 |
| FIO Job 文件生成（Jinja2 模板渲染） | W2D2 | ❌ 未实现 | 无 Jinja2 模板文件；Agent 端 `FioRunner._build_command()` 直接拼装 CLI 参数 `--key=value`，未使用模板渲染 |
| Agent 轮询取任务 `GET /api/task/poll` | W2D3 | ❌ 未实现 | 架构为 Server 主动推送给 Agent（`POST /fio/start`），非 Agent 轮询模式；系统无 `agent_id` 概念。实际为混合模式：Server 推送任务+Agent 推送遥测+Server 按需拉取状态 |
| Agent 执行 FIO 并解析 JSON 结果 | W2D3 | 🔧 已实现需优化 | Agent 执行 FIO 并定时上报 trend 数据到 Server ingest 接口，任务完成后 flush 最终结果；延迟单位统一为微秒(us)（规划为纳秒）；Task.result 缺少 `raw_json` 和 `lat_p99`；FioTrendData 中有 `lat_p99` |
| 结果上传接口 `POST /api/task/<id>/result` | W2D4 | 🔧 已实现需优化 | 等价接口 `POST /api/internal/ingest/flush-task` 由 Agent 调用上报最终结果；FIO trend 数据通过 `POST /api/internal/ingest/fio-trend` 实时上报 |
| 前端任务创建表单 + 任务列表页 | W2D5 | ✅ 已实现 | `TaskCreateModal` 支持引导式（预设模板+高级配置Tab）和原生命令两种模式；`TaskList` 页含状态筛选/搜索/分页；实现质量高于规划 |
| 端到端联调 | W3D1 | ✅ 已实现 | 完整链路已通：前端创建 → Server 下发 Agent → Agent 执行上报 → 结果回显 |

**小结**：FIO 测试核心链路完整且实现质量高于规划（双模式、7种模板、27个参数定义），但架构为 Server 推送模式而非规划的 Agent 轮询模式，且结果字段有差异（延迟单位、命名）。

---

### 功能3 Dashboard

| 子任务 | 排期 | 状态 | 说明 |
|--------|------|------|------|
| Dashboard 聚合接口 `GET /api/dashboard/summary` | W3D2 | ✅ 已实现 | `GET /api/dashboard/summary` 已实现，返回 agents{total,online}、avg_cpu、avg_memory、tasks{total,running,success,failed}、recent_tasks(最多10条)、chart_data(最多30点)；含5秒模块级缓存 |
| 统计卡片（Agent在线数 / 平均CPU / 平均MEM） | W3D3 | ✅ 已实现 | 共7张卡片：任务总数/运行中/成功/失败/平均CPU/平均MEM/设备在线(在线/总数)，均使用真实 API 数据 |
| 最近任务 IOPS + Latency 双折线图 | W3D4 | ✅ 已实现 | ECharts 双 Y 轴图表已实现，X轴=任务时间，左Y轴=IOPS，右Y轴=Latency(ms)；含 smooth + areaStyle；图表展示最多30条任务（规划为10条）；延迟从 us 转为 ms（3位小数） |
| 5秒自动刷新 | W3D5 | ✅ 已实现 | `useDashboard.ts` 中 `refetchInterval: 5000`，精确匹配规划 |

**小结**：Dashboard 所有功能均已实现。主要差异为图表展示数量（30 vs 10）和延迟单位（ms vs ns）。

---

### 功能4 AI 报告

| 子任务 | 排期 | 状态 | 说明 |
|--------|------|------|------|
| AI 调用模块（ai_client.py） | W4D1 | 🔧 已实现需优化 | AI 客户端内嵌于 `AnalysisService.__init__`，使用 OpenAI SDK + 可配置 `AI_BASE_URL`/`AI_MODEL`；支持 DeepSeek/Qwen 切换但无代码级 provider 抽象，缺少独立 ai_client.py 模块 |
| 触发生成接口 `POST /api/task/<id>/ai_report` | W4D2 | ✅ 已实现 | `POST /api/tasks/<id>/ai-analysis`，异步执行（daemon thread），返回 HTTP 202 |
| 查询报告接口 `GET /api/task/<id>/ai_report` | W4D2 | ✅ 已实现 | `GET /api/tasks/<id>/ai-analysis`，含轮询 status（3秒间隔）；无记录时返回 `idle` 状态 |
| AI 数据模型（ai_report / ai_status 字段） | W4D2 | 🔧 已实现需优化 | 使用独立 `AiAnalysis` 表（含 id/task_id/status/report/summary/error/data_window_start/end/input_manifest/completed_at 等），比规划更规范但非 task 表扩展字段；状态枚举为 pending/analyzing/completed/failed（规划为 none/generating/done/failed）；`pending` 为模型默认值但实际流程直接从 `analyzing` 开始 |
| Prompt 模板（简版 200 字结论） | W4D2 | 🔧 已实现需优化 | system_prompt.md + user_prompt_template.md 均为中文，5维度分析框架（FIO/主机/磁盘/趋势/综合评价），7节 Markdown 输出格式，含时序压缩+统计摘要；实现远超规划复杂度，但无 200 字限制约束，max_tokens=4096 |
| 前端 AI 报告按钮 + 展示区 | W4D3 | ✅ 已实现 | `AiAnalysisPanel` 组件：支持 scope 复选框(fio/host/disk/trend/all)、时间窗口配置(0-3600秒)、自动轮询(3秒)、自定义结构化报告解析(非 react-markdown)、性能评级标签(excellent/good/normal/poor)、导出 .md |
| 异常处理（超时/失败 fallback） | W4D4 | 🔧 已实现需优化 | AnalysisService 含完整 try/except + 状态回滚 + error 字段记录；使用 `db_released()` 释放连接；但 OpenAI API 调用无显式 timeout 参数（SDK 默认10分钟），前端轮询无最大时长限制 |
| V1 整体联调 + Demo | W4D5 | 🔧 已实现需优化 | `verify_integration.py` 覆盖设备/心跳/任务/趋势/AI分析；但 Dashboard 聚合接口未覆盖测试，无 AI 超时/失败场景测试，POST 分析响应状态码断言为200但实际返回202（测试会失败） |

**小结**：AI 报告是 V1 中完成度最高的模块，实现质量超出规划。独立 AiAnalysis 表、结构化摘要提取、时间窗口配置、报告导出均为加分项。主要需优化：Prompt 语言已统一为中文、显式超时配置、补充测试覆盖、修复集成测试状态码断言。

---

## V2 性能验证体系（第5~10周）

### 功能1 基线管理

| 子任务 | 排期 | 状态 | 说明 |
|--------|------|------|------|
| Baseline 数据模型 | W5D1 | ✅ 已实现 | `models/baseline.py`，字段覆盖 id/name/device_model/firmware/fio_config/result/source_task_id/device_ip/device_path/created_at/created_by；偏差：详设仅规划 id/name/device_model/firmware/fio_config/result/created_at/created_by，实际增加了 source_task_id/device_ip/device_path 字段用于溯源 |
| 创建基线接口 `POST /api/baselines` | W5D1 | ✅ 已实现 | 含 task 状态校验（status==SUCCESS）、config/result 整体拷贝；偏差：详设为 `POST /api/baseline/create`，实际路径 `/api/baselines` |
| 基线列表接口 `GET /api/baselines` | W5D2 | ✅ 已实现 | keyword 模糊搜索 + device_model 精确匹配 + 分页 |
| 基线详情/删除接口 | W5D3 | ✅ 已实现 | `GET /api/baselines/<id>` + `DELETE /api/baselines/<id>`；偏差：有回归引用时拒绝删除（409 CONFLICT），详设按状态过滤 |
| 前端任务详情页「设为 Baseline」按钮 | W5D2 | ✅ 已实现 | `TaskDetail` 页 Modal：名称必填、设备型号/固件版本选填 |
| 前端基线列表页 | W5D3 | ✅ 已实现 | `BaselineList` + `BaselineDetail` 页，含搜索/分页/查看/删除 |

---

### 功能2 回归测试

| 子任务 | 排期 | 状态 | 说明 |
|--------|------|------|------|
| regression_result 数据模型 | W5D4 | ✅ 已实现 | `models/regression_result.py`，字段 id/task_id/baseline_id/iops_diff/bw_diff/lat_mean_diff/lat_p99_diff/verdict/detail/created_at；偏差：详设仅 4 个 diff 字段+verdict，detail 从 TEXT 改为 JSON 结构化 `{metrics: [...]}` |
| 回归计算接口 `POST /api/regressions` | W5D4 | ✅ 已实现 | diff 计算 + 阈值判定（THRESHOLD_TABLE 4指标×2级）；偏差：详设为 `POST /api/regression/run`，实际路径 `/api/regressions`；FIO 配置匹配增加 fio_config fallback |
| 阈值判定（WARNING >5% / FAIL >10%） | W5D5 | ✅ 已实现 | 4 指标独立判定 + worst_verdict 聚合，含单测 `tests/test_regression_service.py` |
| 前端三列对比表（Baseline / Current / Diff） | W6D1 | ✅ 已实现 | `RegressionDetail` 页：指标/基线值/当前值/差异%+verdict Tag |
| 前端历史回归趋势图 | W6D2 | ✅ 已实现 | `RegressionDetail` 页 ECharts 柱状图：X轴=指标名，Y轴=diff%，含 WARNING/FAIL 阈值线；偏差：详设为时间序列，当前为单轮多指标概览 |

---

### 功能3 多盘并发测试

| 子任务 | 排期 | 状态 | 说明 |
|--------|------|------|------|
| group_task 数据模型 | W6D3 | ✅ 已实现 | `models/group_task.py`，字段 id/name/fio_config/status/summary/total_count/done_count/created_at/updated_at；偏差：详设无 total_count/done_count，实际增加便于进度展示 |
| Task 扩展 group_task_id / is_sub_task 字段 | W6D3 | ✅ 已实现 | `Task` 模型新增 group_task_id FK + is_sub_task 布尔列，to_dict 输出 |
| 创建多盘任务接口（自动拆分子任务） | W6D3 | ✅ 已实现 | `POST /api/group-tasks`；偏差：详设用 Celery chord，实际用 threading + commit-before-start 模式 |
| 并发调度 + 聚合 | W6D4 | ✅ 已实现 | `GroupTaskService.create()` 启动 daemon threads，`try_aggregate()` 在子任务终态时自动触发；偏差：详设为 Celery chord 聚合，实际为 IngestService.flush_task 回调触发 |
| 前端多盘配置页 + 汇总结果（Max/Min/Avg） | W6D5 | ✅ 已实现 | `GroupTaskCreateModal`（Transfer 多选在线设备）+ `GroupTaskList` + `GroupTaskDetail`（Max/Min/Avg 三行四列 Statistic 卡片 + 子任务表） |

---

### 功能4 SNIA 标准测试

| 子任务 | 排期 | 状态 | 说明 |
|--------|------|------|------|
| snia_task 数据模型 | W7D1 | ✅ 已实现 | `models/snia_task.py`，字段 id/name/device_id/device_ip/device_path/config/current_phase/current_round/total_rounds/iops_history(JSON TEXT)/iops_results/is_steady/status/error/created_at/updated_at；偏差：详设用 agent_id，实际用 device_id+device_ip；新增 is_steady/total_rounds/error 字段 |
| SNIA 启动接口 | W7D1 | ✅ 已实现 | `POST /api/snia-tasks`，daemon thread 启动 `_run_pipeline` |
| 三阶段流水线（precondition → iops_test → steady_state） | W7D2 | ✅ 已实现 | `_run_pipeline` 串行三阶段，每阶段通过 `_run_sub_task` / `_wait_sub_task` 管理；偏差：详设为 Celery chain，实际为 daemon thread 串行编排 |
| 稳态判定算法 | W7D3 | ✅ 已实现 | `is_steady_state(window=5, threshold=0.1)`：最近 window 轮 IOPS 最大偏差 < threshold；偏差：详设为 OLS 线性回归，实际简化为 max-deviation |
| 前端进度展示（当前阶段+轮次+实时IOPS） | W7D4 | ✅ 已实现 | `SniaTaskDetail`：Steps 组件三阶段 + 轮次进度 + IOPS 收敛柱状图 |
| 稳态收敛可视化 + 报告导出 | W7D5 | ✅ 已实现 | 柱状图标注稳态窗口 + `GET /api/snia-tasks/<id>/report` |

---

### 功能5 固件升级验证

| 子任务 | 排期 | 状态 | 说明 |
|--------|------|------|------|
| fw_upgrade_test 数据模型 | W8D1 | ✅ 已实现 | `models/fw_upgrade_test.py`，字段 id/name/device_id/device_ip/device_path/fw_before/fw_after/fio_config/result_before/task_before_id/result_after/task_after_id/regression_id/status/error/created_at/updated_at；偏差：详设用 agent_id+device，实际用 device_id+device_ip+device_path；新增 task_before/after_id 用于子任务溯源 |
| 启动接口 `POST /api/fw-tests` | W8D1 | ✅ 已实现 | 自动触发 `_collect_baseline` daemon thread；偏差：详设为 `POST /api/fw_test/start`，实际路径 `/api/fw-tests` |
| 确认升级接口 `POST /api/fw-tests/<id>/confirm-upgrade` | W8D2 | ✅ 已实现 | 读 fw_after → 启动 `_run_after_test` daemon thread → 自动创建基线 + 调用回归比对；偏差：详设为 `POST /api/fw_test/<id>/upgraded` |
| 回归对比报告 | W8D2 | ✅ 已实现 | `GET /api/fw-tests/<id>/report`，含 task + regression（可为null）+ generated_at |
| 前端向导式页面（3步流程） | W8D3 | ✅ 已实现 | `FwTestDetail`：Steps 三步 + 轮询 + 确认按钮 + Popconfirm 终止 |
| AI 自动生成升级建议 | W8D4 | 📋 待开发 | 复用 AnalysisService，复杂度较高，标记 P1 延后 |
| 端到端测试 | W8D5 | ✅ 已实现 | API路径/字段名/响应体/分页参数全链路对齐 |

---

## V2.5 NVMe 协议验证（第11~16周）

### 功能1 Identify 验证

| 子任务 | 排期 | 状态 | 说明 |
|--------|------|------|------|
| nvme_test 数据模型 | W11 | 🚧 部分实现 | 现有 `NvmeDeviceInfo` 在前端定义（model/SN/firmware/capacity/pci_vendor/nvme_version/state），但后端无独立 `nvme_test` 表，也无 Pass/Fail 校验结果存储 |
| Agent nvme id-ctrl / id-ns 封装 | W11 | ✅ 已实现 | `AgentExecutor.get_nvme_id_ctrl()` 和 `get_nvme_id_ns()` 已实现；Agent 端 `nvme_collector.id_ctrl()` 和 `id_ns()` 已实现；数据全链路可通 |
| Server 校验规则引擎 | W11 | ❌ 未实现 | 无 VID/SN/MN/FR/MDTS/NN 等字段的格式/范围校验逻辑 |
| 前端验证结果表格（字段/值/规则/Pass/Fail） | W11 | 🔧 已实现需优化 | 现有 `NvmeDetailModal` 展示 key-value 数据和 LBAF 表，但无校验结果 Pass/Fail 标注 |

---

### 功能2 Namespace 验证

| 子任务 | 排期 | 状态 | 说明 |
|--------|------|------|------|
| Agent nvme_id_ns 封装 | W12 | ✅ 已实现 | 已有 `get_nvme_id_ns()`，Agent 端 `id_ns()` 已实现；但仅透传数据，无 nsze/ncap/nuse/flbas/lbafs 校验 |
| Server namespace 校验规则 | W12 | ❌ 未实现 | — |
| 前端 namespace tab | W12 | ✅ 已实现 | `NvmeListTab` 中 `id-ns` 按钮可打开 `NvmeDetailModal`，含 LBAF 格式表描述 |

---

### 功能3 SMART 验证

| 子任务 | 排期 | 状态 | 说明 |
|--------|------|------|------|
| Agent nvme_smart_log 封装 | W13 | ✅ 已实现 | `AgentExecutor.get_smart()` 已实现；`IngestService.ingest_nvme_smart()` 已实现含归一化+有界整数强制转换；数据持久化到 `nvme_smart_data` 表 |
| SMART 校验规则（含阈值判定） | W13 | 🔧 已实现需优化 | 现有6条告警规则（critical_warning≠0 / media_errors>0 / percentage_used>95→critical / >80→warning / temperature>80°C→critical / >70°C→warning），5维度健康评分（温度/磨损/介质错误/关键警告/可用备用），缺少 `num_err_log_entries` 和 `unsafe_shutdowns` 的告警规则，也无结构化整体 Pass/Fail 输出标志 |
| 前端 SMART 状态卡片 + 温度/寿命进度条 | W13 | ✅ 已实现 | `BasicInfoTab` 含 `HealthScoreGauge`（ECharts 仪表盘）+ 子分数进度条；`SmartMonitorTab` 含 CriticalAlertList + 历史趋势图（温度/磨损/数据量/介质错误） |

---

### 功能4 Error Log 验证

| 子任务 | 排期 | 状态 | 说明 |
|--------|------|------|------|
| Agent error-log 读取 | W14 | ✅ 已实现 | `AgentExecutor.get_nvme_error_log()` 已实现；Agent 端 `nvme_collector.error_log()` 已实现 |
| 主动触发错误 + 验证增加 | W14 | ❌ 未实现 | 现仅为被动展示 error log 内容，无「读基准→触发→验证」三步流程，无 DB 持久化存储 |
| 前端对比展示（触发前/后条数/是否符合预期） | W14 | ❌ 未实现 | `NvmeDetailModal` 中 error-log 类型仅展示原始数据表格 |

---

### 功能5 Feature 验证

| 子任务 | 排期 | 状态 | 说明 |
|--------|------|------|------|
| Agent nvme_get_feature 封装 | W15 | ✅ 已实现 | Agent 端 `GET /nvme/<device>/get-feature` 已实现（`agent_server.py:365-373`）；`AgentExecutor.get_nvme_feature()` 已实现（`agent_executor.py:148-154`）；V2 收尾中 Service/API 层已补全，管道已通 |
| Server feature 校验规则 | W15 | ❌ 未实现 | Service/API 管道已通，但无 Pass/Fail 校验规则引擎 |
| 前端 Feature 验证结果表格 | W15 | ❌ 未实现 | — |

---

### 功能6 Firmware Slot 验证

| 子任务 | 排期 | 状态 | 说明 |
|--------|------|------|------|
| Agent nvme_fw_log 封装 | W16 | ✅ 已实现 | Agent 端 `GET /nvme/<device>/fw-log` 已实现（`agent_server.py:376-383`）；`AgentExecutor.get_nvme_fw_log()` 已实现（`agent_executor.py:156-161`）；V2 收尾中 Service/API 层已补全，管道已通 |
| Server fw slot 校验规则 | W16 | ❌ 未实现 | — |
| 前端固件槽可视化（7槽 + active标注） | W16 | ❌ 未实现 | — |

---

## V3 企业级稳定性验证（第17~22周）

### 功能1 Long Run（72小时压力测试）

| 子任务 | 排期 | 状态 | 说明 |
|--------|------|------|------|
| long_run_task / long_run_sample 数据模型 | W17 | ❌ 未实现 | 无专用表 |
| Celery 周期采样任务（5分钟一次） | W17 | ❌ 未实现 | — |
| 异常检测逻辑 + 告警记录 | W18 | ❌ 未实现 | — |
| 前端实时趋势图（IOPS/温度/媒体错误） | W19 | ❌ 未实现 | — |
| 72小时汇总报告生成 | W20D1 | ❌ 未实现 | — |

---

### 功能2 Data Verify（静默数据损坏检测）

| 子任务 | 排期 | 状态 | 说明 |
|--------|------|------|------|
| verify 模式 fio 模板 | W20D2 | 🚧 部分实现 | FIO 参数定义中已有 `verify`(MD5/CRC32/CRC64/SHA256) 和 `verify_fatal` 参数，FioRunner 可透传至 CLI，但无专用 verify 模板和 verify_errors 解析逻辑 |
| Agent 执行 + verify_errors 解析 | W20D2 | ❌ 未实现 | `_parse_result()` 不解析 `verify_errors` 字段 |
| 前端结果展示（PASS/FAIL + 错误详情） | W20D3 | ❌ 未实现 | — |

---

### 功能3 Power Cycle 验证

| 子任务 | 排期 | 状态 | 说明 |
|--------|------|------|------|
| power_cycle_test 数据模型 | W20D4 | ❌ 未实现 | — |
| 写数据 → 触发 reboot → 等待恢复 | W20D4 | ❌ 未实现 | Task 模型有 `fault_type='power_off'` 字段但无自动化逻辑消费此值 |
| 恢复后自动数据校验 + 设备检查 | W20D5 | ❌ 未实现 | — |
| 前端 Power Cycle 状态时间线 | W21D1 | ❌ 未实现 | — |

---

### 功能4 Hot Plug 验证

| 子任务 | 排期 | 状态 | 说明 |
|--------|------|------|------|
| 手工 Hot Plug 流程（向导式+状态确认） | W21D2~3 | ❌ 未实现 | — |
| 验证逻辑（nvme list / id-ns / smart-log） | W21D4 | ❌ 未实现 | 已有独立的数据读取方法但无编排逻辑串联 |
| 前端 Hot Plug 测试向导 + 结果报告 | W21D5 | ❌ 未实现 | — |

---

### 功能5 Mixed Workload 验证

| 子任务 | 排期 | 状态 | 说明 |
|--------|------|------|------|
| 模板管理（预置4种 + 自定义） | W22D1 | 🔧 已实现需优化 | 现有7种预设模板覆盖 MySQL OLTP(mixed-7030) 和稳态测试(steady-state)，但缺少 Ceph OSD / VM Storage / OLAP 专用模板 |
| 前端 Workload 选择页 + 运行结果展示 | W22D2 | ✅ 已实现 | `TaskCreateModal` 引导式模式中可直接选择模板并运行 |
| 多模板批量运行 + 对比报告 | W22D3 | ❌ 未实现 | — |

---

## V4 AI 分析平台（持续演进）

### 功能1 AI 回归分析

| 子任务 | 排期 | 状态 | 说明 |
|--------|------|------|------|
| 回归分析 Prompt 模板（参数化） | 持续 | ❌ 未实现 | — |
| 多轮回归历史上下文输入 | 持续 | ❌ 未实现 | — |
| 前端回归报告页「AI 分析」按钮 | 持续 | ❌ 未实现 | — |

---

### 功能2 AI 根因分析

| 子任务 | 排期 | 状态 | 说明 |
|--------|------|------|------|
| 数据聚合层（SMART + error_log + long_run 汇总） | 持续 | 🚧 部分实现 | `AnalysisService._build_context()` 已实现 FIO trend + host/disk monitor 聚合与统计压缩，但缺少 SMART 历史数据和 Error Log 聚合 |
| 根因分析 Prompt 封装 | 持续 | ❌ 未实现 | 现有 system_prompt 为通用性能分析框架，非故障假设生成+因果链推理的诊断框架 |
| 前端设备诊断页（一键触发 + 结果展示） | 持续 | ❌ 未实现 | — |

---

## 全局统计

| 类别 | 数量 |
|------|------|
| ✅ 已实现 | 42 |
| 🔧 已实现需优化 | 5 |
| 🚧 部分实现 | 2 |
| ❌ 未实现 | 34 |
| 📋 待开发（延后项） | 2 |
| 总任务项 | 85 |

---

## V1 实现度评估

| 功能 | 完成度 | 说明 |
|------|--------|------|
| Agent 管理 | 100% | 8/8项已实现，心跳架构已改造为Agent-Push模式与规划对齐，V1收尾项全部完成 |
| FIO 测试 | 93.75% | 7.5/8项已实现，核心链路完整且质量超规划，架构差异为设计选择（Server-Push vs Agent-Poll） |
| Dashboard | 100% | 4/4项全部已实现 |
| AI 报告 | 93.75% | 7.5/8项已实现/部分实现，质量超出规划，超时/测试修复已在P-1~P-5中完成 |
| **V1 总体** | **97%** | 核心功能全部可用，所有收尾项已完成 |

---

## V2+ 实现度评估

| 功能 | 完成度 | 说明 |
|------|--------|------|
| V2 基线管理 | 100% | 6/6 ✅，含 source_task_id/device_ip/device_path 溯源字段 |
| V2 回归测试 | 100% | 5/5 ✅，含 4 指标×2 级阈值 + worst_verdict 聚合 + 单测覆盖 |
| V2 多盘并发 | 100% | 5/5 ✅，threading 替代 Celery chord，含 P99 聚合 + FK 级联删除 |
| V2 SNIA 标准 | 100% | 6/6 ✅，daemon thread 三阶段编排，含 aborted 状态 + IOPS Test 容错 |
| V2 固件验证 | 83% | 5/6 ✅，FW-4 AI升级建议待开发，FW-6 槽可视化 P1延后 |
| **V2 总体** | **97%** | 核心功能全部可用，3 轮代码审查 29 项修复已合入 |
| V2.5 Identify | 50% | 2/4 ✅🔧，Agent+Executor 全通但缺规则引擎 |
| V2.5 Namespace | 67% | 2/3 ✅✅，缺规则引擎 |
| V2.5 SMART | 67% | 2/3 ✅🔧，6条规则+5维健康评分，缺 Pass/Fail 标志 |
| V2.5 Error Log | 33% | 1/3 ✅❌❌，可读取但缺三步流程+持久化 |
| V2.5 Feature | 67% | 2/3 ✅❌，管道已通（V2收尾修复），缺规则引擎 |
| V2.5 FW Slot | 67% | 2/3 ✅❌，管道已通（V2收尾修复），缺规则引擎和可视化 |
| V3 Long Run | 0% | 0/5 ❌ |
| V3 Data Verify | 33% | 1/3 🚧❌❌，参数定义已有但缺模板和解析 |
| V3 Power Cycle | 0% | 0/4 ❌（fault_type 字段存在但无逻辑消费） |
| V3 Hot Plug | 0% | 0/3 ❌ |
| V3 Mixed Workload | 67% | 2/3 ✅🔧，7种模板已覆盖主流但缺专用场景 |
| V4 AI 回归分析 | 0% | 0/3 ❌ |
| V4 AI 根因分析 | 33% | 1/3 🚧❌❌，数据聚合部分已有但缺 SMART/ErrorLog |

---

## 实现偏差汇总

> 所有偏差详细记录在 `v2-detailed-design.md` §2.7（模块1-2）、§3.4（模块3）、§4.4（模块4）、§5.4（模块5），此处仅列概要

| 偏差项 | 详设位置 | 实际实现 | 偏差原因 |
|--------|---------|---------|---------|
| BL-4 删除校验策略 | §1.5 | 任何回归引用均拒绝删除 | RegressionResult 无中间状态，全量拦截保障溯源 |
| RG-1 FIO 配置匹配 | §2.2 | result 取值增加 fio_config fallback | result JSON 不含 rw，需从 config 兜底 |
| RG-6 趋势图 | §2.6 | 单轮多指标概览+阈值线 | 先实现可用图表，后续积累数据扩展时间序列 |
| 侧边栏路由归一化 | — | normalizeKey() 处理 3 个详情路由 | 详设未提及，实际开发发现必需 |
| 基线名称取值 | — | useBaselineDetail 精准请求 | 避免全量列表拉取 |
| 回归弹窗路由传参 | — | location.state.taskId 预填 | 减少跨页操作步骤 |
| GT 线程安全 | §3.2 | current_app._get_current_object() + commit-before-start | Flask-SQLAlchemy 3.x db 无 app_context()；线程内需真实 app 引用 |
| GT 聚合增加 P99 | §3.2 | try_aggregate() 额外聚合 lat_p99 | P99 是回归判定关键指标，详设遗漏 |
| GT 级联删除 FK 处理 | §3.3 | 删除前清理 DataRecord/Baseline/DiskMonitorSample | RESTRICT FK 约束需显式处理，详设未覆盖 |
| SN 子任务用 ID 而非名称 | §4.2 | flush()→task.id 作为 Agent 标识 | 与 V1 管道一致，避免名称冲突 |
| SN 稳态算法简化 | §4.2 | max-deviation < threshold | OLS 回归实现复杂度高，工程验证场景足够 |
| SN IOPS Test 容错 | §4.2 | 单组失败 continue，不中断扫描 | 24 组合中单组失败不应阻断全量 |
| SN aborted 状态 | §4.2 | 新增 aborted 状态，三态区分 | 用户主动终止 vs 异常失败需区分 |
| SN iops_history 存储 | §4.2 | Text + json.dumps/loads | MySQL JSON 列兼容性问题 |
| SN config 深度合并 | §4.2 | 按 section 级 merge | 避免部分配置覆盖未指定字段 |
| FW 线程安全 | §5.2 | 双重 commit + current_app._get_current_object() | 两个线程各自需要独立 app 上下文 |
| FW 用户终止检测 | §5.2 | 多检查点检测 status=failed+error=用户终止 | 详设未考虑中途终止场景 |
| FW _extract_active_fw | §5.2 | module-level 函数，从 AFI/FRS 提取 | Agent FW Log 结构需解析 AFI+FRS |
| FW 自动创建基线 | §5.3 | _run_after_test 自动调用 BaselineService.create | 回归比对需基线参照，详设未提及 |
| FW report AI 建议 | §5.5 | 标记 P1 延后，regression 可为 null | 复用 AnalysisService，复杂度较高 |
| FW AgentExecutor 导入 | — | 文件底部延迟导入 # noqa: E402 | 避免循环依赖 |

---

## 代码审查修复记录

> 记录 V2 全部代码完成后的多轮审查修复，详情见 `v2-detailed-design.md` §12

| 轮次 | 发现数 | 关键问题 | 状态 |
|------|--------|---------|------|
| 第1轮 | 22 | APScheduler context、FIO 配置匹配、metadata 保留字等 | ✅ 全部已修复 |
| 第2轮 | 5 | analysis_service 缺 logger、SMART checksum 含丢弃样本、THRESHOLD_TABLE 键名不匹配、checksum 粒度不匹配、终止按钮缺确认 | ✅ 全部已修复 |
| 第3轮 | 2 | SNIA 稳态窗口高亮差一位、Task 删除 FK 级联未处理 | ✅ 全部已修复 |
| **合计** | **29** | — | **全部已修复** |

---

## 甘特图（文本版）

```
         W1  W2  W3  W4  W5  W6  W7  W8  W9  W10 W11 W12 W13 W14 W15 W16 W17 W18 W19 W20 W21 W22
V1       ████████████████
  Agent  ████  (8/8 ✅, 心跳Push)
  FIO        ████████░░░░  (7.5/8 ✅🔧, 核心链路完整)
  Dashboard          ████  (4/4 ✅)
  AI Report              ████░░░░  (7.5/8 ✅🔧)

V2                           ████████████████████████
  基线管理                   ████████  (6/6 ✅)
  回归测试                       ████████  (5/5 ✅)
  多盘并发                           ████████  (5/5 ✅)
  SNIA 标准                              █████████  (6/6 ✅)
  固件验证                                    █████████  (5/6 ✅📋)
  代码审查                                                          ████  (29/29 ✅)

V2.5                                                          ████████████████████
  Identify                                                     ████░░░░  (2/4 ✅🔧)
  Namespace                                                        ████░░  (2/3 ✅✅)
  SMART验证                        ████░░  (2/3 ✅🔧)
  Error Log                                                                ████░░  (1/3 ✅❌❌)
  Feature                                                                     ████░░  (2/3 ✅❌)
  FW Slot                                                                         ████░░  (2/3 ✅❌)

V3                                                                               ████████████████████
  Long Run                                                                       ████████████  (0/5 ❌)
  Data Verify                                                                            ████░░  (1/3 🚧)
  Power Cycle                                                                              ████  (0/4 ❌)
  Hot Plug                                                                                    ██████  (0/3 ❌)
  Mixed Workload                                                                                  ████░░  (2/3 ✅🔧)

V4                                                                                                   ▓▓▓▓▓▓▓▓▓▓▓▓
  AI 回归分析                                                                                        ▓▓▓▓░░  (0/3 ❌)
  AI 根因分析                                                                                            ▓▓▓▓░░  (1/3 🚧)

图例: █ = 已实现  ░ = 部分实现/需优化  📋 = 待开发(延后项)  ▓ = 持续演进
```

---

## 按优先级排序的待办清单

### 已完成（V1 收尾 + V2 全部 + 管道修复）

| # | 任务 | 来源 | 状态 |
|---|------|------|------|
| 1 | ~~Dashboard 接入真实数据~~ | V1-功能3 | ✅ 已完成 |
| 2 | ~~Dashboard 5s自动刷新~~ | V1-功能3 | ✅ 已完成 |
| 3 | ~~CPU/MEM 平均值卡片~~ | V1-功能3 | ✅ 已完成 |
| 4 | ~~IOPS+Latency 双折线图~~ | V1-功能3 | ✅ 已完成 |
| 5 | ~~心跳 Push 模式改造~~ | V1-功能1 | ✅ 已完成 |
| 6 | ~~AI 超时配置~~ | V1-功能4 | ✅ 已完成（P-1） |
| 7 | ~~AI 前端轮询超时~~ | V1-功能4 | ✅ 已完成（P-2） |
| 8 | ~~Dashboard 集成测试~~ | V1-功能4 | ✅ 已完成（P-3） |
| 9 | ~~AI 分析状态码修复~~ | V1-功能4 | ✅ 已完成（P-4） |
| 10 | ~~Agent 轮询10s~~ | V1-功能1 | ✅ 已完成（P-5） |
| 11 | ~~Feature 管道修复~~ | V2.5-功能5 | ✅ 已完成 |
| 12 | ~~FW Slot 管道修复~~ | V2.5-功能6 | ✅ 已完成 |

### V2 延后项（P1，可随时补齐）

| # | 任务 | 来源 | 工作量 | 状态 |
|---|------|------|--------|------|
| 13 | FW-4 AI 升级建议生成 | V2-功能5 | 1d | 📋 待开发 |
| 14 | FW-6 固件槽可视化 | V2-功能5 | 1d | 📋 待开发 |

### V2.5 核心任务（下一版本优先）

| # | 任务 | 来源 | 工作量 | 优先级 |
|---|------|------|--------|--------|
| 15 | NVMe 协议校验规则引擎 | V2.5-通用 | 3d | P0 |
| 16 | 结构化校验结果输出格式 | V2.5-通用 | 1d | P0 |
| 17 | Identify 校验规则接入 | V2.5-功能1 | 0.5d | P0 |
| 18 | Namespace 校验规则接入 | V2.5-功能2 | 0.5d | P0 |
| 19 | SMART 增加 num_err_log_entries + unsafe_shutdowns + Pass/Fail | V2.5-功能3 | 1d | P1 |
| 20 | Error Log DB 持久化 + 三步验证流程 | V2.5-功能4 | 2d | P1 |
| 21 | Feature 校验规则接入 | V2.5-功能5 | 0.5d | P1 |
| 22 | FW Slot 校验规则 + 前端可视化 | V2.5-功能6 | 1.5d | P1 |

### V3 前置 / 增强（后续迭代）

| # | 任务 | 来源 | 工作量 | 优先级 |
|---|------|------|--------|--------|
| 23 | FIO verify 模板 + verify_errors 解析 | V3-功能2 | 2d | P1 |
| 24 | 补充 Ceph OSD / VM Storage / OLAP 模板 | V3-功能5 | 1d | P2 |
| 25 | SMART 历史 + Error Log 聚合 | V4-功能2 | 2d | P2 |
| 26 | 独立 ai_client.py + provider 抽象 | V1-功能4 | 1d | P2 |
| 27 | taskStore 与 React Query 去重 | 前端 | 1d | P2 |
| 28 | useWebSocket 启用或移除 | 前端 | 0.5d | P3 |
| 29 | testConnection 硬编码密码移除 | 安全 | 0.5d | P2 |
