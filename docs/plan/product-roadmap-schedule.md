# SSD Engine 产品规划 — 详细排期与实现状态

> 基于文档 `docs/plan/SSD_Engine_Plan.md` 逐项标注实现状态，生成可追踪的排期表。
> 最近更新：2026-06-16（基于完整代码走读复查）

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
| Baseline 数据模型 | W5D1 | ❌ 未实现 | 无 `baseline` 表，无相关模型 |
| 创建基线接口 `POST /api/baseline/create` | W5D1 | ❌ 未实现 | 无基线 CRUD 接口 |
| 基线列表接口 `GET /api/baseline/list` | W5D2 | ❌ 未实现 | — |
| 基线详情/删除接口 | W5D3 | ❌ 未实现 | — |
| 前端任务详情页「设为 Baseline」按钮 | W5D2 | ❌ 未实现 | — |
| 前端基线列表页 | W5D3 | ❌ 未实现 | — |

---

### 功能2 回归测试

| 子任务 | 排期 | 状态 | 说明 |
|--------|------|------|------|
| regression_result 数据模型 | W5D4 | ❌ 未实现 | 无回归结果表 |
| 回归计算接口 `POST /api/regression/run` | W5D4 | ❌ 未实现 | 无 diff 计算逻辑 |
| 阈值判定（WARNING >5% / FAIL >10%） | W5D5 | ❌ 未实现 | — |
| 前端三列对比表（Baseline / Current / Diff） | W6D1 | ❌ 未实现 | — |
| 前端历史回归趋势图 | W6D2 | ❌ 未实现 | — |

---

### 功能3 多盘并发测试

| 子任务 | 排期 | 状态 | 说明 |
|--------|------|------|------|
| group_task 数据模型 | W6D3 | ❌ 未实现 | 无 group_task 表，Task 仅有单一 device_path 字段 |
| Task 扩展 group_task_id 字段 | W6D3 | ❌ 未实现 | — |
| 创建多盘任务接口（自动拆分子任务） | W6D3 | ❌ 未实现 | — |
| Celery chord 并发调度 + 聚合 | W6D4 | | 当前无 Celery，使用 APScheduler + threading |
| 前端多盘配置页 + 汇总结果（Max/Min/Avg） | W6D5 | ❌ 未实现 | — |

---

### 功能4 SNIA 标准测试

| 子任务 | 排期 | 状态 | 说明 |
|--------|------|------|------|
| snia_task 数据模型 | W7D1 | ❌ 未实现 | — |
| SNIA 启动接口 | W7D1 | ❌ 未实现 | — |
| Celery 任务链（precondition → iops_test → steady_state） | W7D2 | ❌ 未实现 | — |
| 稳态判定算法 | W7D3 | ❌ 未实现 | — |
| 前端进度展示（当前阶段+轮次+实时IOPS） | W7D4 | ❌ 未实现 | — |
| 稳态收敛可视化 + 报告导出 | W7D5 | ❌ 未实现 | — |

---

### 功能5 固件升级验证

| 子任务 | 排期 | 状态 | 说明 |
|--------|------|------|------|
| fw_upgrade_test 数据模型 | W8D1 | ❌ 未实现 | — |
| 启动接口 `POST /api/fw_test/start` | W8D1 | ❌ 未实现 | — |
| 确认升级接口 `POST /api/fw_test/<id>/upgraded` | W8D2 | ❌ 未实现 | — |
| 回归对比报告 | W8D2 | ❌ 未实现 | — |
| 前端向导式页面（3步流程） | W8D3 | ❌ 未实现 | — |
| AI 自动生成升级建议 | W8D4 | ❌ 未实现 | — |
| 端到端测试 | W8D5 | ❌ 未实现 | — |

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
| Agent nvme_get_feature 封装 | W15 | 🚧 部分实现 | Agent 端 `GET /nvme/<device>/get-feature` 已实现（`agent_server.py:365-373`）；`AgentExecutor.get_nvme_feature()` 已实现（`agent_executor.py:148-154`）；但后端 `nvme_service.py` 无对应 Service 方法，API 层 `nvme.py` 无暴露端点——管道断裂 |
| Server feature 校验规则 | W15 | ❌ 未实现 | — |
| 前端 Feature 验证结果表格 | W15 | ❌ 未实现 | — |

---

### 功能6 Firmware Slot 验证

| 子任务 | 排期 | 状态 | 说明 |
|--------|------|------|------|
| Agent nvme_fw_log 封装 | W16 | 🚧 部分实现 | Agent 端 `GET /nvme/<device>/fw-log` 已实现（`agent_server.py:376-383`）；`AgentExecutor.get_nvme_fw_log()` 已实现（`agent_executor.py:156-161`）；但后端 Service/API 层未接入——管道断裂，同 Feature |
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
| ✅ 已实现 | 17 |
| 🔧 已实现需优化 | 14 |
| 🚧 部分实现 | 7 |
| ❌ 未实现 | 61 |
| 总任务项 | 99 |

---

## V1 实现度评估

| 功能 | 完成度 | 说明 |
|------|--------|------|
| Agent 管理 | 87.5% | 7/8项已实现，心跳架构已改造为Agent-Push模式与规划对齐 |
| FIO 测试 | 75% | 6/8项已实现，核心链路完整且质量超规划，架构差异3项 |
| Dashboard | 100% | 4/4项全部已实现，部分字段/数值有差异 |
| AI 报告 | 75% | 6/8项已实现/部分实现，质量超出规划，需优化2项 |
| **V1 总体** | **84%** | 核心功能全部可用，心跳架构已与规划对齐 |

---

## V2+ 实现度评估

| 功能 | 完成度 | 说明 |
|------|--------|------|
| V2 基线管理 | 0% | 0/6 ❌ |
| V2 回归测试 | 0% | 0/5 ❌ |
| V2 多盘并发 | 0% | 0/5 ❌ |
| V2 SNIA 标准 | 0% | 0/6 ❌ |
| V2 固件验证 | 0% | 0/7 ❌ |
| V2.5 Identify | 50% | 2/4 ✅🔧，Agent+Executor 全通但缺规则引擎 |
| V2.5 Namespace | 67% | 2/3 ✅✅，缺规则引擎 |
| V2.5 SMART | 67% | 2/3 ✅🔧，6条规则+5维健康评分，缺 Pass/Fail 标志 |
| V2.5 Error Log | 33% | 1/3 ✅❌❌，可读取但缺三步流程+持久化 |
| V2.5 Feature | 33% | 1/3 🚧❌❌，Agent+Executor 通但 Service/API 断裂 |
| V2.5 FW Slot | 33% | 1/3 🚧❌❌，Agent+Executor 通但 Service/API 断裂 |
| V3 Long Run | 0% | 0/5 ❌ |
| V3 Data Verify | 33% | 1/3 🚧❌❌，参数定义已有但缺模板和解析 |
| V3 Power Cycle | 0% | 0/4 ❌（fault_type 字段存在但无逻辑消费） |
| V3 Hot Plug | 0% | 0/3 ❌ |
| V3 Mixed Workload | 67% | 2/3 ✅🔧，7种模板已覆盖主流但缺专用场景 |
| V4 AI 回归分析 | 0% | 0/3 ❌ |
| V4 AI 根因分析 | 33% | 1/3 🚧❌❌，数据聚合部分已有但缺 SMART/ErrorLog |

---

## 甘特图（文本版）

```
         W1  W2  W3  W4  W5  W6  W7  W8  W9  W10 W11 W12 W13 W14 W15 W16 W17 W18 W19 W20 W21 W22
V1       ████████████████
  Agent  ████  (7/8 ✅🔧, 心跳Push)
  FIO        ████████░░░░  (6/8 ✅🔧, 核心链路完整)
  Dashboard          ████  (4/4 ✅)
  AI Report              ████░░░░  (6/8 ✅🔧)

V2                           ████████████████████████
  基线管理                   ████████  (0/6 ❌)
  回归测试                       ████████  (0/5 ❌)
  多盘并发                           ████████  (0/5 ❌)
  SNIA 标准                              █████████  (0/6 ❌)
  固件验证                                    █████████  (0/7 ❌)

V2.5                                                          ████████████████████
  Identify                                                     ████░░░░  (2/4 ✅🔧)
  Namespace                                                        ████░░  (2/3 ✅✅)
  SMART验证                        ████░░  (2/3 ✅🔧)
  Error Log                                                                ████░░  (1/3 ✅❌❌)
  Feature                                                                     ████░░  (1/3 🚧❌❌)
  FW Slot                                                                         ████░░  (1/3 🚧❌❌)

V3                                                                               ████████████████████
  Long Run                                                                       ████████████  (0/5 ❌)
  Data Verify                                                                            ████░░  (1/3 🚧)
  Power Cycle                                                                              ████  (0/4 ❌)
  Hot Plug                                                                                    ██████  (0/3 ❌)
  Mixed Workload                                                                                  ████░░  (2/3 ✅🔧)

V4                                                                                                   ▓▓▓▓▓▓▓▓▓▓▓▓
  AI 回归分析                                                                                        ▓▓▓▓░░  (0/3 ❌)
  AI 根因分析                                                                                            ▓▓▓▓░░  (1/3 🚧)

图例: █ = 已实现  ░ = 部分实现/需优化  █ = 规划排期(未实现)  ▓ = 持续演进
```

---

## 按优先级排序的待办清单

### 紧急（影响产品可用性 / V1 收尾）

| # | 任务 | 来源 | 工作量估算 | 状态 |
|---|------|------|-----------|------|
| 1 | ~~Dashboard 接入真实数据，替换硬编码占位~~ | V1-功能3 | ~~2天~~ | ✅ 已完成 |
| 2 | ~~Dashboard 增加5s自动刷新~~ | V1-功能3 | ~~0.5天~~ | ✅ 已完成 |
| 3 | ~~Dashboard 增加 CPU/MEM 平均值卡片~~ | V1-功能3 | ~~1天~~ | ✅ 已完成 |
| 4 | ~~Dashboard IOPS+Latency 双折线图接入真实数据~~ | V1-功能3 | ~~1天~~ | ✅ 已完成 |
| 5 | ~~Agent 心跳架构改造为 Push 模式~~ | V1-功能1 | ~~1天~~ | ✅ 已完成 |
| 6 | AI 调用增加显式超时配置（OpenAI API timeout） | V1-功能4 | 0.5天 | 待开发 |
| 7 | AI 前端轮询增加最大等待时长（避免无限轮询） | V1-功能4 | 0.5天 | 待开发 |
| 8 | 补充 verify_integration.py 对 Dashboard 接口的测试 | V1-功能4 | 0.5天 | 待开发 |
| 9 | 修复 verify_integration.py 中 POST AI 分析状态码断言（预期200→202） | V1-功能4 | 0.1天 | 待开发 |
| 10 | 前端 Agent 列表页轮询间隔从30s调整至10s | V1-功能1 | 0.1天 | 待开发 |

### 重要（V2 前置依赖 / V2.5 管道修复）

| # | 任务 | 来源 | 工作量估算 | 状态 |
|---|------|------|-----------|------|
| 11 | Feature 管道修复：nvme_service + API 层接入 get-feature | V2.5-功能5 | 1天 | 待开发 |
| 12 | FW Slot 管道修复：nvme_service + API 层接入 fw-log | V2.5-功能6 | 1天 | 待开发 |
| 13 | NVMe 协议校验规则引擎（可配置 Pass/Fail 判定） | V2.5-通用 | 3天 | 待开发 |
| 14 | 结构化校验结果输出格式统一 | V2.5-通用 | 1天 | 待开发 |
| 15 | FIO verify 模式专用模板 + verify_errors 解析 | V3-功能2 | 2天 | 待开发 |
| 16 | SMART 校验增加 `num_err_log_entries` 和 `unsafe_shutdowns` 告警规则 | V2.5-功能3 | 1天 | 待开发 |
| 17 | Error Log DB 持久化 + 主动触发验证三步流程 | V2.5-功能4 | 2天 | 待开发 |

### 增强（已有模块的迭代优化）

| # | 任务 | 来源 | 工作量估算 | 状态 |
|---|------|------|-----------|------|
| 18 | 抽取独立 ai_client.py 模块（支持 provider 抽象） | V1-功能4 | 1天 | 待开发 |
| 19 | AnalysisService 增加 SMART 历史 + Error Log 聚合 | V4-功能2 | 2天 | 待开发 |
| 20 | 补充 Ceph OSD / VM Storage / OLAP 预设模板 | V3-功能5 | 1天 | 待开发 |
| 21 | FIO 结果增加 raw_json 字段和 lat_p99 字段 | V1-功能2 | 0.5天 | 待开发 |
| 22 | testConnection 硬编码密码 `123456` 移除 | 安全 | 0.5天 | 待开发 |
| 23 | 前端 taskStore 与 React Query 去重 | 前端 | 1天 | 待开发 |
| 24 | useWebSocket hook 启用或移除 | 前端 | 0.5天 | 待开发 |
