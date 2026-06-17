# SSD Engine

SSD Engine 是一个围绕 SSD/NVMe 存储设备测试、运行态监控和结果分析构建的全栈平台。当前仓库由三部分组成：部署在设备侧的 Agent、负责编排与存储的 Backend、以及面向操作人员的 Frontend。

## 核心能力

- **FIO 任务管理**：创建、下发、停止、重试、查看详情与趋势，支持引导模式和原生命令模式
- **设备管理**：登记设备、刷新 Agent 状态、获取磁盘信息
- **监控采集**：采集主机指标（CPU/内存/网络）、磁盘指标（IOPS/带宽/延迟/队列深度）和 NVMe SMART 数据
- **NVMe 健康评估**：基于 SMART 数据计算 5 维度健康评分（温度/磨损/介质错误/临界告警/备用空间），支持 6 条告警规则
- **AI 分析**：按任务时间窗聚合 FIO、主机监控、磁盘监控数据，通过 LLM 生成结构化分析报告
- **数据治理**：查看数据概览，执行归档、压缩、下载、清理
- **SNIA 测试**：三阶段自动流水线（预处理 → IOPS 扫描 → 稳态判定），符合 SNIA 规范的 SSD 性能测试
- **回归测试**：对比任务结果与基线的 IOPS/BW/延迟差异，自动判定 PASS/WARNING/FAIL
- **基线管理**：从成功任务提取 FIO 配置和结果作为性能基线
- **固件升级测试**：端到端自动化（采集基线 → 等待升级 → 升级后测试 → 回归分析）
- **NVMe 校验**：基于 YAML 规则引擎的 6 种校验类型（identify/namespace/smart/error_log/feature/fw_slot）
- **多盘并发**：一次操作选择多台设备并发执行相同 FIO 配置，自动聚合统计

## 当前架构

```text
Frontend (React 18 + TypeScript + Vite 5 + Ant Design 5)
        |
        | /api
        v
Backend (Flask 3.1 + SQLAlchemy + MySQL 8.x)
        |
        | HTTP
        v
Agent (Flask 3.1, deployed on target host)
        |
        +-- run fio
        +-- collect host metrics (CPU/Memory/Network)
        +-- collect disk metrics (IOPS/BW/latency/util)
        +-- collect NVMe SMART
        +-- collect NVMe commands (id-ctrl/id-ns/error-log)
```

## 仓库结构

```text
ssd_engine/
├── agent/              设备侧服务，负责执行 fio 和采集运行态数据
│   ├── collectors/         数据采集器（CPU/内存/网络/磁盘/NVMe/SMART/System）
│   ├── executor/           FIO 任务执行器
│   ├── agent_server.py     Agent 主服务
│   └── ingest_client.py    数据上报客户端
├── backend/            平台后端，负责设备、任务、分析、数据生命周期
│   ├── app/
│   │   ├── api/            REST API 接口（14 个路由模块）
│   │   ├── services/       业务逻辑层（13 个服务）
│   │   ├── models/         数据模型（14 张表）
│   │   ├── schemas/        请求验证（Pydantic schema）
│   │   ├── rules/          NVMe 校验规则（YAML）
│   │   ├── workloads/      FIO 配置验证
│   │   ├── executors/      Agent 通信执行器
│   │   └── prompts/        AI 分析提示词
│   └── init_mysql.sql      数据库初始化脚本
├── frontend/           React 控制台
│   └── src/pages/          页面组件（18 个页面）
├── docs/               补充文档与截图目录
└── README.md
```

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | React 18, TypeScript, Vite 5, Ant Design 5, ECharts, Zustand, React Query |
| 后端 | Python 3.10+, Flask 3.1, SQLAlchemy, Pydantic, APScheduler, pyarrow |
| 设备侧 | Python 3.10+, Flask 3.1, FIO, nvme-cli, psutil |
| AI 分析 | OpenAI 兼容接口 |
| 数据库 | MySQL 8.x |

## 页面截图

以下截图文件位于 docs/screenshots，可直接在 GitHub 或编辑器 Markdown 预览中查看。

### 仪表盘总览

![仪表盘总览](docs/screenshots/dashboard-overview.png)

### 任务创建（引导模式）

![任务创建-引导模式](docs/screenshots/task-create-guided.png)

### 任务创建（原生命令模式）

![任务创建-原生命令模式](docs/screenshots/task-create-native.png)

### 任务详情（趋势）

![任务详情-趋势](docs/screenshots/task-detail-trend.png)

### 任务详情（AI 分析）

![任务详情-AI分析](docs/screenshots/task-detail-ai-analysis.png)

### 设备管理

![设备管理](docs/screenshots/device-manage.png)

### 主机监控

![主机监控](docs/screenshots/monitor-host.png)

### 磁盘监控

![磁盘监控](docs/screenshots/monitor-disk.png)

### 数据管理

![数据管理](docs/screenshots/data-manage.png)

## 快速启动

### 1. 准备依赖

- Python 3.10+
- Node.js 18+
- MySQL 8.x
- Agent 所在机器需安装 fio 和 nvme-cli

### 2. 初始化数据库

在 MySQL 中执行 backend/init_mysql.sql。

该脚本会创建 ssd_engine 数据库、默认用户，以及任务、趋势、监控、SMART、分析和数据记录相关表结构。

### 3. 启动 Backend

```bash
cd backend
pip install -r requirements.txt
python run.py
```

Backend 默认监听 5000 端口。run.py 实际读取的是 HOST 和 PORT 环境变量；业务配置由 app/config.py 从环境变量加载。

### 4. 启动 Agent

```bash
cd agent
pip install -r requirements.txt
python agent_server.py
```

Agent 默认监听 8080 端口。若需要把采集数据写入 Backend，请在 agent 目录配置 .env，至少设置 BACKEND_URL 和 AGENT_DEVICE_IP。

可参考 agent/.env.example。

### 5. 启动 Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend 开发服务器默认监听 3000 端口，并通过 Vite 代理把 /api 转发到 http://127.0.0.1:5000。

## 推荐启动顺序

1. MySQL
2. Backend
3. Agent
4. Frontend

## 关键运行链路

### 任务执行链路

1. 前端调用 Backend 创建任务
2. Backend 通过 AgentExecutor 访问目标设备 Agent
3. Agent 启动 fio，并持续解析状态与趋势
4. Agent 定期向 Backend 上报 FIO 趋势
5. 前端在任务详情页查看状态、趋势、结果和 AI 分析

### 监控链路

1. Agent 后台线程按秒采集主机、磁盘指标
2. 主机监控与磁盘监控通过内部 ingest API 写入 Backend
3. NVMe SMART 由 Agent 周期采集并入库
4. Frontend 通过 Backend 查询监控和 SMART 数据

### AI 分析链路

1. 前端发起任务 AI 分析请求
2. Backend 异步提交分析任务并立即返回 analyzing
3. AnalysisService 聚合任务时间窗内的 FIO、主机监控、磁盘监控数据
4. 分析报告写入 ai_analyses，前端轮询获取结果

### SNIA 测试链路

1. 前端创建 SNIA 任务（指定设备、块大小、模式等）
2. SniaService 在后台线程执行三阶段流水线
3. Phase 1 Precondition：顺序写 128k 预处理
4. Phase 2 IOPS Test：6 种块大小 × 4 种 pattern = 24 种组合 FIO 测试
5. Phase 3 Steady State：多轮 4k randwrite，检测 IOPS 收敛（最近 5 轮最大偏差 < 10%）
6. 前端实时查看阶段进度、IOPS 矩阵、收敛趋势

### 回归测试链路

1. 用户选择基线和目标任务
2. RegressionService 对比 IOPS/BW/lat_mean/lat_p99 四个指标
3. 计算差异百分比，基于阈值表判定 PASS/WARNING/FAIL
4. 结果写入 regression_results，前端查看对比表和差异趋势图

### 固件升级测试链路

1. 用户创建固件测试（选择设备、基线、FIO 配置）
2. 系统自动采集当前固件版本（fw_before）
3. 执行基线 FIO 测试
4. 等待用户手动升级固件并确认
5. 系统采集新固件版本（fw_after）
6. 执行升级后 FIO 测试
7. 自动创建基线并执行回归分析
8. 生成包含回归结果的完整报告

### 多盘并发链路

1. 用户创建任务组（选择多台设备、FIO 配置）
2. GroupTaskService 为每台设备创建子任务
3. 所有子任务并发执行
4. 全部完成后自动聚合统计（IOPS/BW/延迟的 max/min/avg）
5. 前端查看任务组详情和汇总结果

## NVMe SMART 健康评分

平台基于 SMART 数据计算 5 维度健康评分（总分 100）：

| 维度 | 满分 | 评分规则 |
|------|------|----------|
| 温度 | 30 | ≤50°C 得满分，50-80°C 线性衰减，>80°C 得 0 |
| 磨损度 | 25 | 25 × (1 - percentage_used/100) |
| 介质错误 | 25 | 无错误得满分，有错误得 0 |
| 临界告警 | 15 | 无告警得满分，有告警得 0 |
| 备用空间 | 10 | 按 available_spare 比例计算 |

健康等级：excellent (≥85) / good (≥70) / normal (≥50) / poor (<50)

### 告警规则

- critical_warning ≠ 0 → critical
- media_errors > 0 → critical
- percentage_used > 95% → critical
- percentage_used > 80% → warning
- temperature > 80°C → critical
- temperature > 70°C → warning

## API 端点清单

### 任务管理

| 方法 | 端点 | 功能 |
|------|------|------|
| GET | `/api/tasks` | 任务列表（支持 status/keyword 筛选，分页） |
| POST | `/api/tasks` | 创建 FIO 任务（引导模式或原生命令模式） |
| GET | `/api/tasks/<id>` | 获取任务详情 |
| GET | `/api/tasks/<id>/status` | 获取任务运行状态 |
| GET | `/api/tasks/<id>/raw` | 获取任务原始输出 |
| DELETE | `/api/tasks/<id>` | 删除任务（级联删除趋势数据/基线/DataRecord） |
| GET | `/api/tasks/<id>/trend` | 获取任务趋势数据（支持时间范围） |
| POST | `/api/tasks/<id>/stop` | 停止运行中任务 |
| POST | `/api/tasks/<id>/retry` | 重试失败任务 |

### 设备管理

| 方法 | 端点 | 功能 |
|------|------|------|
| GET | `/api/devices` | 设备列表 |
| POST | `/api/devices` | 添加设备 |
| PUT | `/api/devices/<id>` | 更新设备（名称/端口） |
| DELETE | `/api/devices/<id>` | 删除设备 |
| GET | `/api/devices/<id>/info` | 获取设备详情含磁盘列表（实时从 Agent 获取） |
| POST | `/api/devices/test-connection` | 测试 Agent 连接 |
| GET | `/api/devices/<id>/agent-status` | 获取 Agent 缓存状态（心跳驱动） |

### 监控数据

| 方法 | 端点 | 功能 |
|------|------|------|
| GET | `/api/monitor/hosts/<host>/metrics` | 主机监控指标（支持时间范围） |
| GET | `/api/monitor/hosts/<host>/disks` | 主机磁盘列表 |
| GET | `/api/monitor/hosts/<host>/disks/<disk>/metrics` | 磁盘监控指标 |
| GET | `/api/monitor/hosts/<host>/summary` | 主机监控概览 |

### NVMe 管理

| 方法 | 端点 | 功能 |
|------|------|------|
| GET | `/api/devices/<id>/smart/latest` | 最新 SMART 快照（含健康评分和告警） |
| GET | `/api/devices/<id>/smart/history` | SMART 历史趋势 |
| GET | `/api/devices/<id>/smart/health-score` | 健康评分 |
| GET | `/api/devices/<id>/smart/alerts` | 告警列表 |
| GET | `/api/devices/<id>/nvme/list` | NVMe 设备列表（含容量/型号/序列号等） |
| GET | `/api/devices/<id>/nvme/<disk>/id-ctrl` | NVMe identify controller |
| GET | `/api/devices/<id>/nvme/<disk>/id-ns` | NVMe identify namespace |
| GET | `/api/devices/<id>/nvme/<disk>/error-log` | NVMe 错误日志 |
| GET | `/api/devices/<id>/nvme/<disk>/get-feature` | NVMe feature 获取（默认 0x06） |
| GET | `/api/devices/<id>/nvme/<disk>/fw-log` | NVMe 固件日志 |
| POST | `/api/devices/<id>/nvme/validate` | 发起 NVMe 校验测试 |
| GET | `/api/nvme-tests/<test_id>` | 获取 NVMe 校验结果 |
| GET | `/api/devices/<id>/nvme-tests` | NVMe 校验列表 |

### AI 分析

| 方法 | 端点 | 功能 |
|------|------|------|
| POST | `/api/tasks/<id>/ai-analysis` | 提交 AI 分析（异步） |
| GET | `/api/tasks/<id>/ai-analysis` | 获取最新分析结果 |
| GET | `/api/tasks/<id>/ai-analysis/history` | 分析历史 |

### 仪表盘

| 方法 | 端点 | 功能 |
|------|------|------|
| GET | `/api/dashboard/summary` | 仪表盘汇总（设备/任务/趋势） |

### 数据管理

| 方法 | 端点 | 功能 |
|------|------|------|
| GET | `/api/data` | 数据记录列表（支持多维度筛选） |
| GET | `/api/data/overview` | 数据概览（active/archived/compressed 统计） |
| POST | `/api/data/download` | 下载数据（tar.gz） |
| POST | `/api/data/archive` | 手动归档 |
| POST | `/api/data/delete` | 手动删除 |
| POST | `/api/data/auto-archive-and-cleanup` | 自动归档+清理 |
| POST | `/api/data/compress` | 数据压缩（JSON→Parquet） |
| POST | `/api/data/cleanup` | 数据清理 |

### 基线管理

| 方法 | 端点 | 功能 |
|------|------|------|
| POST | `/api/baselines` | 创建基线（从成功任务） |
| GET | `/api/baselines` | 基线列表 |
| GET | `/api/baselines/<id>` | 基线详情 |
| DELETE | `/api/baselines/<id>` | 删除基线（有回归引用时禁止） |

### 回归测试

| 方法 | 端点 | 功能 |
|------|------|------|
| POST | `/api/regressions` | 执行回归测试（对比任务结果与基线） |
| GET | `/api/regressions` | 回归列表 |
| GET | `/api/regressions/<id>` | 回归详情 |

### 固件升级测试

| 方法 | 端点 | 功能 |
|------|------|------|
| POST | `/api/fw-tests` | 创建固件测试（自动采集基线→等待升级→测试→回归） |
| GET | `/api/fw-tests` | 固件测试列表 |
| GET | `/api/fw-tests/<id>` | 固件测试详情 |
| POST | `/api/fw-tests/<id>/confirm-upgrade` | 确认已升级，开始升级后测试 |
| POST | `/api/fw-tests/<id>/abort` | 终止固件测试 |
| GET | `/api/fw-tests/<id>/report` | 固件测试报告 |

### SNIA 测试

| 方法 | 端点 | 功能 |
|------|------|------|
| POST | `/api/snia-tasks` | 创建 SNIA 测试（三阶段流水线） |
| GET | `/api/snia-tasks` | SNIA 任务列表 |
| GET | `/api/snia-tasks/<id>` | SNIA 任务详情 |
| POST | `/api/snia-tasks/<id>/abort` | 终止 SNIA 任务 |
| GET | `/api/snia-tasks/<id>/report` | SNIA 报告 |

### 多盘并发任务组

| 方法 | 端点 | 功能 |
|------|------|------|
| POST | `/api/group-tasks` | 创建任务组（多设备并发 FIO） |
| GET | `/api/group-tasks` | 任务组列表 |
| GET | `/api/group-tasks/<id>` | 任务组详情（含子任务） |
| DELETE | `/api/group-tasks/<id>` | 删除任务组 |

### 内部数据上报

| 方法 | 端点 | 功能 |
|------|------|------|
| POST | `/api/internal/ingest/fio-trend` | Agent 上报 FIO 趋势数据 |
| POST | `/api/internal/ingest/disk-monitor` | Agent 上报磁盘监控数据 |
| POST | `/api/internal/ingest/host-monitor` | Agent 上报主机监控数据 |
| POST | `/api/internal/ingest/nvme-smart` | Agent 上报 NVMe SMART 数据 |
| POST | `/api/internal/ingest/flush-task` | Agent 上报任务完成状态 |
| POST | `/api/internal/ingest/heartbeat` | Agent 心跳上报 |

## 数据库表结构

| 表名 | 用途 |
|------|------|
| `devices` | 设备登记（IP/名称/SSH/Agent状态/心跳/主机信息） |
| `tasks` | FIO 任务（配置/状态/结果/原始输出/子任务关联） |
| `fio_trend_data` | FIO 趋势采样点（IOPS/BW/延迟，按任务和时间索引） |
| `host_monitor_data` | 主机监控数据（CPU/内存/网络，JSON 存储） |
| `disk_monitor_data` | 磁盘监控汇总（JSON 存储） |
| `disk_monitor_samples` | 磁盘监控采样（细粒度指标：IOPS/BW/延迟/队列深度/利用率） |
| `nvme_smart_data` | NVMe SMART 数据（温度/磨损/错误/告警/读写量等） |
| `ai_analyses` | AI 分析报告（状态/报告文本/摘要/输入清单） |
| `data_records` | 数据生命周期元数据（active/archived/compressed 状态管理） |
| `baselines` | 性能基线（从成功任务提取的 FIO 配置和结果） |
| `regression_results` | 回归测试结果（IOPS/BW/延迟差异百分比 + PASS/WARNING/FAIL 判定） |
| `group_tasks` | 多盘并发任务组（汇总统计：max/min/avg） |
| `snia_tasks` | SNIA 测试任务（三阶段流水线状态/IOPS历史/稳态判定） |
| `fw_upgrade_tests` | 固件升级测试（升级前后结果/回归引用） |
| `nvme_tests` | NVMe 校验测试记录（6 种类型/PASS/PARTIAL/FAIL 判定） |

## SNIA 测试

SNIA（存储网络行业协会）标准 SSD 性能测试，采用三阶段自动流水线：

### Phase 1: Precondition（预处理）

- 顺序写 128k，执行 N 轮（默认 2 loops）
- 目的：使 SSD 进入稳态

### Phase 2: IOPS Test（IOPS 扫描）

- 6 种块大小 × 4 种 pattern = 24 种组合
- 块大小：4k, 8k, 16k, 32k, 64k, 128k
- Pattern：randread, randwrite, read, write
- 每种组合执行 FIO，收集 IOPS 和带宽

### Phase 3: Steady State（稳态判定）

- 执行最多 25 轮 4k randwrite
- 每轮检查 IOPS 稳态：最近 5 轮最大偏差 < 10%
- 达成稳态后停止，记录最终 IOPS

### 输出

- IOPS 测试结果矩阵（块大小 × pattern）
- 稳态收敛 IOPS 历史趋势
- SNIA 测试报告（JSON 格式）

## 回归测试

对比任务结果与基线的性能差异，自动判定是否回归。

### 对比指标

| 指标 | WARNING 阈值 | FAIL 阈值 |
|------|-------------|-----------|
| IOPS | < -5% | < -10% |
| 带宽 (BW) | < -5% | < -10% |
| 平均延迟 (lat_mean) | > +10% | > +20% |
| P99 延迟 (lat_p99) | > +15% | > +30% |

### 判定逻辑

- 所有指标在阈值内 → PASS
- 任一指标触发 WARNING → WARNING
- 任一指标触发 FAIL → FAIL

### 输出

- 三列对比表（基线值/当前值/差异%）
- 差异趋势图（含阈值线）
- 回归结果 JSON

## 基线管理

从成功的 FIO 任务中提取配置和结果作为性能基线。

### 基线内容

- FIO 配置（bs/rw/iodepth/numjobs/runtime 等）
- 测试结果（IOPS/BW/latency）
- 设备信息（型号/固件版本/序列号）

### 约束

- 仅成功的任务可创建基线
- 被回归测试引用的基线不可删除

## 固件升级测试

端到端固件升级验证自动化流程。

### 流程

1. **采集基线**：记录当前固件版本（fw_before），执行 FIO 基线测试
2. **等待升级**：用户手动升级固件
3. **确认升级**：用户在界面确认已完成升级
4. **升级后测试**：采集新固件版本（fw_after），执行 FIO 测试
5. **回归分析**：自动创建基线并对比升级前后性能差异
6. **生成报告**：包含固件版本、测试结果、回归判定的完整报告

### 输出

- 固件版本对比（fw_before vs fw_after）
- 升级前后 FIO 结果对比
- 回归判定（PASS/WARNING/FAIL）

## NVMe 校验

基于 YAML 规则引擎的 NVMe 设备合规性校验。

### 校验类型

| 类型 | 规则数 | 说明 |
|------|--------|------|
| identify | 10 | NVMe identify controller 校验（VID/SN/MN/FR/MDTS/NN 等） |
| namespace | 6 | NVMe identify namespace 校验（NSZE/NCAP/NUSE/FLBAS/LBAF 等） |
| smart | 8 | SMART 数据校验（critical_warning/温度/媒体错误/磨损度等） |
| error_log | 1 | 错误日志交叉验证（两次采集比对计数器单调性） |
| feature | 3 | NVMe feature 校验（Write Cache/Power Management/APST） |
| fw_slot | 3 | 固件槽校验（激活槽号/Slot 1 版本/槽列表） |

### 规则引擎

支持 12 种操作类型：not_empty / not_zero / gte / lte / range / regex / in_set / len_lte / len_gte / increased / format

规则定义在 `backend/app/rules/` 目录下的 YAML 文件中，支持动态参数解析。

### 输出

- 校验结果（PASS/PARTIAL/FAIL）
- 每条规则的详细判定（通过/失败/跳过）

## 多盘并发

一次操作选择多台设备并发执行相同 FIO 配置。

### 功能

- 支持为不同设备指定不同的 device_path
- 所有子任务并发执行
- 自动聚合统计：IOPS/BW/延迟的 max/min/avg

### 状态管理

- `running`：部分子任务执行中
- `done`：全部子任务成功
- `partial`：部分子任务成功，部分失败
- `failed`：全部子任务失败

### 输出

- 每台设备的子任务详情
- 汇总统计（max/min/avg）

## 数据生命周期

三阶段数据管理模型：

### 阶段

1. **Active**：MySQL 热表存储，支持实时查询
2. **Archived**：导出为 JSON 文件，更新过期时间
3. **Compressed**：JSON → Parquet 格式压缩（使用 pyarrow + snappy）

### 自动策略

| 数据类型 | 保留天数 | 说明 |
|----------|----------|------|
| 监控数据 | 7 天 | 自动归档 |
| SMART 数据 | 90 天 | 自动归档 |
| 归档数据 | 30 天 | 自动压缩 |
| 压缩数据 | 90 天 | 自动清理 |

### 功能

- 手动归档/压缩/下载/清理
- 自动归档+清理（定时任务）
- SHA256 校验和验证数据完整性
- 保护 ACTIVE 状态的数据窗口

## 默认端口

- Frontend: 3000
- Backend: 5000
- Agent: 8080
- MySQL: 3306

## 子模块文档

- agent/README.md：Agent 进程模型、接口和配置说明
- backend/README.md：后端模块、API 分组、存储与调度说明
- frontend/README.md：前端页面结构、接口映射和开发方式
