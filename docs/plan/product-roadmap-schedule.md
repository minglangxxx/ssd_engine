# SSD Engine 产品规划 — 详细排期与实现状态

> 基于文档 `docs/SSD_Engine_产品规划.md` 逐项标注实现状态，生成可追踪的排期表。

---

## 状态说明

| 标记 | 含义 |
|------|------|
| ✅ 已实现 | 代码中已有完整实现 |
| 🔧 已实现需优化 | 功能已有，但存在缺陷或需要迭代增强 |
| 🚧 部分实现 | 核心路径已通，但缺少部分子功能 |
| ❌ 未实现 | 代码中无对应实现 |
| 📋 规划中 | 仅有设计，尚无代码 |

---

## V1 基础测试平台（第1~4周）

### 功能1 Agent 管理

| 子任务 | 排期 | 状态 | 说明 |
|--------|------|------|------|
| Agent 数据模型（agent 表） | W1D1 | 🔧 已实现需优化 | 现有 `Device` 模型含 ip/name/agent_port/agent_status/last_heartbeat，但缺少 `hostname`、`os_version`、`kernel_version`、`cpu_usage`、`memory_usage` 字段 |
| Agent 心跳上报接口 `POST /api/agent/heartbeat` | W1D1 | 🔧 已实现需优化 | 现有 `POST /api/internal/ingest/*` 系列接口由 Agent 主动推送数据，但无独立心跳接口；Agent 状态由 Server 端 `DeviceStatusChecker` 每30秒主动探测决定，而非 Agent 上报 |
| Agent 列表接口 `GET /api/agent/list` | W1D1 | 🔧 已实现需优化 | 现有 `GET /api/devices` 返回设备列表，字段不完全匹配规划（无 hostname/os/kernel/cpu/memory） |
| Agent 详情接口 `GET /api/agent/<id>` | W1D1 | 🔧 已实现需优化 | 现有 `GET /api/devices/<id>/info` 返回设备信息+磁盘列表，但缺少 OS/内核/CPU/内存等 Agent 主机信息 |
| Agent 心跳脚本（agent_daemon.py，每30秒 POST） | W1D2 | 🔧 已实现需优化 | 现有 Agent 是一个独立的 HTTP 服务进程（Flask），被动响应 Server 请求，而非规划中的主动心跳上报模式；Agent 有 `/health` 端点但无定时心跳逻辑 |
| Celery Beat 扫描超时 Agent 置 offline | W1D3 | 🔧 已实现需优化 | 现有 `DeviceStatusChecker` 用 APScheduler 每30秒 ThreadPoolExecutor 并发检测，功能等价但未用 Celery |
| 前端 Agent 列表页 | W1D4 | 🔧 已实现需优化 | 现有 `DeviceManage` 页面展示 IP/名称/状态/版本/心跳时间，但缺少 CPU/内存/OS/内核信息展示和 10s 轮询 |
| 联调验证 | W1D5 | ✅ 已实现 | 基本链路已通：Server 检测 Agent → 状态更新 → 前端展示 |

**小结**：Agent 管理核心链路已通，但架构模式不同（Server 主动轮询 vs 规划的 Agent 主动心跳），且 Agent 主机信息字段缺失。

---

### 功能2 FIO 测试

| 子任务 | 排期 | 状态 | 说明 |
|--------|------|------|------|
| Task 数据模型 | W2D1 | 🔧 已实现需优化 | 现有 `Task` 模型含 device_id/device_ip/device_path/config(JSON)/status/result(JSON)/fault_type 等，字段覆盖更广（含 fault_type、retention_policy、data_window），但缺少 `agent_id`（用 device_id 替代） |
| 创建任务接口 `POST /api/task/create` | W2D1 | ✅ 已实现 | `POST /api/tasks` 支持引导式和原生命令两种模式，含 FioConfigValidator 校验 |
| FIO Job 文件生成（Jinja2 模板渲染） | W2D2 | ❌ 未实现 | 现有实现是 Server 将 config JSON 直接 POST 给 Agent `/fio/start`，由 Agent 自行拼装 fio 命令；未使用 Jinja2 模板 |
| Agent 轮询取任务 `GET /api/task/poll` | W2D3 | ❌ 未实现 | 现有架构是 Server 主动推送给 Agent（`POST /fio/start`），非 Agent 轮询模式 |
| Agent 执行 FIO 并解析 JSON 结果 | W2D3 | 🔧 已实现需优化 | Agent 执行 FIO 并定时上报 trend 数据到 Server ingest 接口，任务完成后 flush 最终结果；但 Agent 侧代码不在当前仓库中 |
| 结果上传接口 `POST /api/task/<id>/result` | W2D4 | 🔧 已实现需优化 | 现有 `POST /api/internal/ingest/flush-task` 由 Agent 调用上报最终结果；FIO trend 数据通过 `POST /api/internal/ingest/fio-trend` 持续上报 |
| 前端任务创建表单 + 任务列表页 | W2D5 | ✅ 已实现 | `TaskCreateModal` 支持引导式（含7种预设模板+9个高级配置Tab）和原生命令两种模式；`TaskList` 页含状态筛选/搜索/分页 |
| 端到端联调 | W3D1 | ✅ 已实现 | 完整链路已通：前端创建 → Server 下发 Agent → Agent 执行上报 → 结果回显 |

**小结**：FIO 测试核心链路完整且实现质量高于规划（引导式+原生命令双模式、7种预设模板、27个 FIO 参数定义），但架构为 Server 推送模式而非规划中的 Agent 轮询模式。

---

### 功能3 Dashboard

| 子任务 | 排期 | 状态 | 说明 |
|--------|------|------|------|
| Dashboard 聚合接口 `GET /api/dashboard/summary` | W3D2 | ❌ 未实现 | 现无此聚合接口；Dashboard 页各卡片分别调用 `GET /api/tasks`、`GET /api/devices` 等已有接口拼装数据 |
| 统计卡片（Agent在线数 / 平均CPU / 平均MEM） | W3D3 | 🔧 已实现需优化 | 现有卡片：总任务数/运行中/成功/失败/设备在线数，但 **CPU/MEM 平均值未实现**（需新增 Agent 主机信息采集） |
| 最近任务 IOPS + Latency 双折线图 | W3D4 | ❌ 未实现 | 现有"全局IOPS趋势"图 **使用硬编码占位数据**，未接入真实 API；无 Latency 趋势图 |
| 5秒自动刷新 | W3D5 | ❌ 未实现 | Dashboard 页未设置自动轮询 |

**小结**：Dashboard 框架已有但数据不真实，是当前产品最明显的体验缺陷之一。

---

### 功能4 AI 报告

| 子任务 | 排期 | 状态 | 说明 |
|--------|------|------|------|
| AI 调用模块（ai_client.py） | W4D1 | ✅ 已实现 | `AnalysisService` 使用 OpenAI Compatible API，支持 DeepSeek/Qwen 等模型切换（通过 `AI_BASE_URL` + `AI_MODEL` 环境变量） |
| 触发生成接口 `POST /api/task/<id>/ai_report` | W4D2 | ✅ 已实现 | `POST /api/tasks/<id>/ai-analysis`，异步执行（daemon thread），返回 202 |
| 查询报告接口 `GET /api/task/<id>/ai_report` | W4D2 | ✅ 已实现 | `GET /api/tasks/<id>/ai-analysis`，含轮询 status |
| AI 数据模型（ai_report / ai_status 字段） | W4D2 | 🔧 已实现需优化 | 现有独立 `AiAnalysis` 表（id/task_id/status/report/summary/error/data_window_start/end/input_manifest等），比规划更规范，但非 task 表内扩展字段 |
| Prompt 模板（简版 200 字结论） | W4D2 | 🔧 已实现需优化 | 现有 system_prompt + user_prompt_template 远超规划复杂度：5维度分析框架（FIO/主机/磁盘/趋势/综合评价），7节 Markdown 输出格式，含时序压缩+统计摘要，但 Prompt 为英文（system/user）+中文输出混搭，可统一 |
| 前端 AI 报告按钮 + 展示区 | W4D3 | ✅ 已实现 | `AiAnalysisPanel` 组件：支持 scope 复选框、时间窗口配置、自动轮询、Markdown 渲染、性能评级标签、导出 .md |
| 异常处理（超时/失败 fallback） | W4D4 | ✅ 已实现 | AnalysisService 含完整 try/except + 状态回滚 + error 字段记录 |
| V1 整体联调 + Demo | W4D5 | ✅ 已实现 | `verify_integration.py` 集成测试覆盖完整流程 |

**小结**：AI 报告是 V1 中完成度最高的模块，实现质量超出规划。独立 AiAnalysis 表、结构化摘要提取、时间窗口配置、Markdown 报告渲染均为加分项。

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
| group_task 数据模型 | W6D3 | ❌ 未实现 | 无 group_task 表 |
| Task 扩展 group_task_id 字段 | W6D3 | ❌ 未实现 | — |
| 创建多盘任务接口（自动拆分子任务） | W6D3 | ❌ 未实现 | — |
| Celery chord 并发调度 + 聚合 | W6D4 | ❌ 未实现 | 当前无 Celery，使用 APScheduler + threading |
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
| Agent nvme_identify 封装 | W11 | 🔧 已实现需优化 | `AgentExecutor.get_nvme_id_ctrl()` 已实现 `nvme id-ctrl` 调用；`get_nvme_id_ns()` 已实现 `nvme id-ns` 调用；但仅为数据透传，无校验规则引擎 |
| Server 校验规则引擎 | W11 | ❌ 未实现 | 无 VID/SN/MN/FR/MDTS/NN 等字段的格式/范围校验逻辑 |
| 前端验证结果表格（字段/值/规则/Pass/Fail） | W11 | ❌ 未实现 | 现有 `NvmeDetailModal` 仅展示原始 key-value 数据，无校验结果标注 |

---

### 功能2 Namespace 验证

| 子任务 | 排期 | 状态 | 说明 |
|--------|------|------|------|
| Agent nvme_id_ns 封装 | W12 | 🔧 已实现需优化 | 已有 `get_nvme_id_ns()`，但仅透传数据，无 nsze/ncap/nuse/flbas/lbafs 校验 |
| Server namespace 校验规则 | W12 | ❌ 未实现 | — |
| 前端 namespace tab | W12 | ✅ 已实现 | `NvmeListTab` 中 `id-ns` 按钮可打开 `NvmeDetailModal`，含 LBAF 格式表描述 |

---

### 功能3 SMART 验证

| 子任务 | 排期 | 状态 | 说明 |
|--------|------|------|------|
| Agent nvme_smart_log 封装 | W13 | 🔧 已实现需优化 | `AgentExecutor.get_smart()` 已实现；`IngestService.ingest_nvme_smart()` 已实现含归一化+有界整数强制转换；`NvmeService` 含5维度健康评分+6条告警规则，但无 SNIA 规范级的 SMART Pass/Fail 校验 |
| SMART 校验规则（含阈值判定） | W13 | 🔧 已实现需优化 | 现有6条告警规则（critical_warning≠0 / media_errors>0 / percentage_used>80% / temperature>70°C），与规划基本吻合，但缺少 `num_err_log_entries` 和 `unsafe_shutdowns` 的记录逻辑，也无结构化 Pass/Fail 输出格式 |
| 前端 SMART 状态卡片 + 温度/寿命进度条 | W13 | ✅ 已实现 | `BasicInfoTab` 含 `HealthScoreGauge`（ECharts 仪表盘）+ 子分数进度条；`SmartMonitorTab` 含 CriticalAlertList + 历史趋势图 |

---

### 功能4 Error Log 验证

| 子任务 | 排期 | 状态 | 说明 |
|--------|------|------|------|
| Agent error-log 读取 | W14 | 🔧 已实现需优化 | `AgentExecutor.get_nvme_error_log()` 已实现读取；但无主动触发错误+验证增加的流程 |
| 主动触发错误 + 验证增加 | W14 | ❌ 未实现 | 现仅为被动展示 error log 内容，无「读基准→触发→验证」三步流程 |
| 前端对比展示（触发前/后条数/是否符合预期） | W14 | ❌ 未实现 | `NvmeDetailModal` 中 error-log 类型仅展示原始数据表格 |

---

### 功能5 Feature 验证

| 子任务 | 排期 | 状态 | 说明 |
|--------|------|------|------|
| Agent nvme_get_feature 封装 | W15 | ❌ 未实现 | `AgentExecutor` 无 `get-feature` 相关方法 |
| Server feature 校验规则 | W15 | ❌ 未实现 | — |
| 前端 Feature 验证结果表格 | W15 | ❌ 未实现 | — |

---

### 功能6 Firmware Slot 验证

| 子任务 | 排期 | 状态 | 说明 |
|--------|------|------|------|
| Agent nvme_fw_log 封装 | W16 | ❌ 未实现 | `AgentExecutor` 无 `fw-log` 相关方法 |
| Server fw slot 校验规则 | W16 | ❌ 未实现 | — |
| 前端固件槽可视化（7槽 + active标注） | W16 | ❌ 未实现 | — |

---

## V3 企业级稳定性验证（第17~22周）

### 功能1 Long Run（72小时压力测试）

| 子任务 | 排期 | 状态 | 说明 |
|--------|------|------|------|
| long_run_task / long_run_sample 数据模型 | W17 | ❌ 未实现 | — |
| Celery 周期采样任务（5分钟一次） | W17 | ❌ 未实现 | — |
| 异常检测逻辑 + 告警记录 | W18 | ❌ 未实现 | — |
| 前端实时趋势图（IOPS/温度/媒体错误） | W19 | ❌ 未实现 | — |
| 72小时汇总报告生成 | W20D1 | ❌ 未实现 | — |

--- Data Verify（静默数据损坏检测）

| 子任务 | 排期 | 状态 | 说明 |
|--------|------|------|------|
| verify 模式 fio 模板 | W20D2 | 🚧 部分实现 | FIO 参数定义中已有 `verify`（MD5/CRC32/CRC64/SHA256）和 `verify_fatal` 参数，但无专用 verify 模式模板和 verify_errors 解析逻辑 |
| Agent 执行 + verify_errors 解析 | W20D2 | ❌ 未实现 | — |
| 前端结果展示（PASS/FAIL + 错误详情） | W20D3 | ❌ 未实现 | — |

---

### 功能3 Power Cycle 验证

| 子任务 | 排期 | 状态 | 说明 |
|--------|------|------|------|
| power_cycle_test 数据模型 | W20D4 | ❌ 未实现 | — |
| 写数据 → 触发 reboot → 等待恢复 | W20D4 | ❌ 未实现 | — |
| 恢复后自动数据校验 + 设备检查 | W20D5 | ❌ 未实现 | — |
| 前端 Power Cycle 状态时间线 | W21D1 | ❌ 未实现 | — |

---

### 功能4 Hot Plug 验证

| 子任务 | 排期 | 状态 | 说明 |
|--------|------|------|------|
| 手工 Hot Plug 流程（向导式+状态确认） | W21D2~3 | ❌ 未实现 | — |
| 验证逻辑（nvme list / id-ns / smart-log） | W21D4 | ❌ 未实现 | — |
| 前端 Hot Plug 测试向导 + 结果报告 | W21D5 | ❌ 未实现 | — |

---

### 功能5 Mixed Workload 验证

| 子任务 | 排期 | 状态 | 说明 |
|--------|------|------|------|
| 模板管理（预置4种 + 自定义） | W22D1 | 🔧 已实现需优化 | 现有7种预设模板（randread-latency/randwrite-pressure/seqread-throughput/seqwrite-throughput/mixed-7030/steady-state/custom），覆盖了 MySQL OLTP (mixed-7030) 和稳态测试 (steady-state)，但缺少 Ceph OSD / VM Storage / OLAP 专用模板 |
| 前端 Workload 选择页 + 运行结果展示 | W22D2 | ✅ 已实现 | `TaskCreateModal` 引导式模式中可直接选择模板 |
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
| 数据聚合层（SMART + error_log + long_run 汇总） | 持续 | 🚧 部分实现 | `AnalysisService._build_context()` 已实现 FIO trend + host/disk monitor 聚合，但缺少 SMART 历史数据和 Error Log 聚合 |
| 根因分析 Prompt 封装 | 持续 | ❌ 未实现 | — |
| 前端设备诊断页（一键触发 + 结果展示） | 持续 | ❌ 未实现 | — |

---

## 全局统计

| 类别 | 数量 |
|------|------|
| ✅ 已实现 | 10 |
| 🔧 已实现需优化 | 17 |
| 🚧 部分实现 | 4 |
| ❌ 未实现 | 52 |
| 总任务项 | 83 |

---

## 甘特图（文本版）

```
         W1  W2  W3  W4  W5  W6  W7  W8  W9  W10 W11 W12 W13 W14 W15 W16 W17 W18 W19 W20 W21 W22
V1       ████████████████
  Agent  ████
  FIO        ████████
  Dashboard          ████
  AI Report              ████

V2                           ████████████████████████
  基线管理                   ████
  回归测试                       ████
  多盘并发                           ████
  SNIA 标准                              █████
  固件验证                                    █████

V2.5                                                          ████████████████████
  Identify                                                     ████
  Namespace                                                        ████
  SMART验证                                                            ████
  Error Log                                                                ████
  Feature                                                                     ████
  FW Slot                                                                         ████

V3                                                                               ████████████████████
  Long Run                                                                       ████████
  Data Verify                                                                            ██
  Power Cycle                                                                              ██
  Hot Plug                                                                                    ████
  Mixed Workload                                                                                  ███

V4                                                                                                   ▓▓▓▓▓▓▓▓▓▓▓▓
  AI 回归分析                                                                                        ▓▓▓▓
  AI 根因分析                                                                                            ▓▓▓▓

图例: █ = 规划排期  ▓ = 持续演进  已实现部分用绿色覆盖
```

---

## 按优先级排序的待办清单

### 紧急（影响产品可用性）

| # | 任务 | 来源 | 工作量估算 |
|---|------|------|-----------|
| 1 | Dashboard 接入真实数据，替换硬编码占位 | V1-功能3 | 2天 |
| 2 | Dashboard 增加5s自动刷新 | V1-功能3 | 0.5天 |
| 3 | Dashboard 增加 CPU/MEM 平均值卡片 | V1-功能3 | 1天（依赖Agent主机信息采集） |
| 4 | Agent 心跳/主机信息上报字段补全（hostname/os/kernel/cpu/mem） | V1-功能1 | 1天 |

### 重要（V2 前置依赖）

| # | 任务 | 来源 | 工作量估算 |
|---|------|------|-----------|
| 5 | Agent `nvme get-feature` 封装 | V2.5-功能5 | 1天 |
| 6 | Agent `nvme fw-log` 封装 | V2.5-功能6 | 1天 |
| 7 | NVMe 协议校验规则引擎（可配置 Pass/Fail 判定） | V2.5-通用 | 3天 |
| 8 | 结构化校验结果输出格式统一 | V2.5-通用 | 1天 |
| 9 | FIO verify 模式专用模板 + verify_errors 解析 | V3-功能2 | 2天 |
| 10 | SMART 校验增加 `num_err_log_entries` 和 `unsafe_shutdowns` | V2.5-功能3 | 1天 |

### 增强（已有模块的迭代优化）

| # | 任务 | 来源 | 工作量估算 |
|---|------|------|-----------|
| 11 | AI Prompt 语言统一（全中文或全英文） | V1-功能4 | 0.5天 |
| 12 | AnalysisService 增加 SMART 历史 + Error Log 聚合 | V4-功能2 | 2天 |
| 13 | Agent 架构统一：评估是否从 Server-pull 切换为 Agent-push 心跳模式 | V1-功能1 | 3天（架构改造） |
| 14 | 补充 Ceph OSD / VM Storage / OLAP 预设模板 | V3-功能5 | 1天 |
| 15 | testConnection 硬编码密码 `123456` 移除 | 安全 | 0.5天 |
| 16 | 前端 taskStore 与 React Query 去重 | 前端 | 1天 |
| 17 | useWebSocket hook 启用或移除 | 前端 | 0.5天 |
