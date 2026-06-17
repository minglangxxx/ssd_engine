# Backend

Backend 是 SSD Engine 的控制面，负责设备管理、任务编排、监控与 SMART 数据存储、AI 分析、数据生命周期管理，并对前端暴露统一的 /api 接口。

## 目录结构

```text
backend/
├── run.py                  应用启动入口
├── init_mysql.sql          数据库初始化脚本
├── verify_integration.py   集成验证脚本
├── app/
│   ├── __init__.py         应用工厂与定时任务启动
│   ├── api/                REST 路由（14 个模块）
│   │   ├── __init__.py     Blueprint 注册与错误处理
│   │   ├── task.py         任务接口
│   │   ├── device.py       设备接口
│   │   ├── monitor.py      监控接口
│   │   ├── nvme.py         NVMe SMART 与校验接口
│   │   ├── analysis.py     AI 分析接口
│   │   ├── data.py         数据治理接口
│   │   ├── dashboard.py    仪表盘接口
│   │   ├── baseline.py     基线管理接口
│   │   ├── regression.py   回归测试接口
│   │   ├── fw_test.py      固件升级测试接口
│   │   ├── snia_task.py    SNIA 测试接口
│   │   ├── group_task.py   多盘并发任务组接口
│   │   └── internal_ingest.py  Agent 数据上报接口
│   ├── config.py           环境变量配置
│   ├── executors/          AgentExecutor 等执行器
│   ├── models/             SQLAlchemy 模型（15 张表）
│   ├── prompts/            AI 分析提示词
│   │   ├── system_prompt.md
│   │   └── user_prompt_template.md
│   ├── schemas/            Pydantic 请求校验
│   ├── rules/              NVMe 校验规则（YAML）
│   │   ├── identify_rules.yaml
│   │   ├── namespace_rules.yaml
│   │   ├── smart_rules.yaml
│   │   ├── feature_rules.yaml
│   │   └── fw_slot_rules.yaml
│   ├── services/           核心业务服务（13 个）
│   │   ├── task_service.py
│   │   ├── device_service.py
│   │   ├── monitor_service.py
│   │   ├── nvme_service.py
│   │   ├── nvme_validation_service.py
│   │   ├── analysis_service.py
│   │   ├── ingest_service.py
│   │   ├── data_lifecycle.py
│   │   ├── device_status_checker.py
│   │   ├── baseline_service.py
│   │   ├── regression_service.py
│   │   ├── fw_upgrade_service.py
│   │   ├── snia_service.py
│   │   └── group_task_service.py
│   ├── utils/              响应、日志、时间处理
│   └── workloads/          工作负载定义
└── requirements.txt
```

## 应用结构

### Flask 应用工厂

app/__init__.py 中的 create_app 会完成以下工作：

- 加载配置
- 初始化日志
- 初始化 SQLAlchemy 和 Flask-Migrate
- 注册 /api 蓝图和全局错误处理
- 执行 db.create_all()
- 启动 APScheduler 定时任务

### 定时任务

Backend 会启动一个 Asia/Shanghai 时区的后台调度器：

- **每天 02:00**：执行数据生命周期任务（自动归档超期 active 数据、清理超过保留期的数据）
- **定期检查**：Agent 心跳状态检查

默认保留策略由 MONITOR_RETENTION_DAYS 和 NVME_SMART_RETENTION_DAYS 控制。

## 核心服务

### DeviceService

- 设备新增、更新、删除
- Agent 状态刷新
- 设备信息和磁盘列表查询
- 按设备记录中的 agent_port 创建 AgentExecutor

### TaskService

- 创建任务（支持引导模式和原生命令模式）
- 刷新运行状态
- 停止任务与重试任务
- 聚合任务详情和趋势

### MonitorService

- 主机监控从数据库读取
- 磁盘列表和主机摘要通过 Agent 实时获取
- 磁盘监控优先从数据库读取，无窗口参数且数据库无样本时回退到 Agent 实时接口

### IngestService

- 接收 Agent 上报的 FIO 趋势
- 接收主机监控、磁盘监控和 NVMe SMART 样本
- 更新数据窗口和 data_records 元数据
- 接收 Agent 心跳，更新设备在线状态
- **并发控制**：使用有界乐观锁重试（最多 5 次），避免并发写入导致计数膨胀
- DataRecord 表使用 version 字段实现 CAS 更新

### NvmeService

- SMART 数据采集与存储
- NVMe 设备列表（id-ctrl/id-ns）
- NVMe 命令执行（error-log/get-feature/fw-log）
- **健康评分算法**：5 维度 100 分制评分
  - 温度（满分 30）：≤50°C 得满分，50-80°C 线性衰减，>80°C 得 0
  - 磨损度（满分 25）：25 × (1 - percentage_used/100)
  - 介质错误（满分 25）：无错误得满分，有错误得 0
  - 临界告警（满分 15）：无告警得满分，有告警得 0
  - 备用空间（满分 10）：按 available_spare 比例计算
- **告警规则**（6 条）：
  - critical_warning ≠ 0 → critical
  - media_errors > 0 → critical
  - percentage_used > 95% → critical
  - percentage_used > 80% → warning
  - temperature > 80°C → critical
  - temperature > 70°C → warning
- 健康等级划分：excellent (≥85) / good (≥70) / normal (≥50) / poor (<50)

### NvmeValidationService

- 基于 YAML 规则引擎的 NVMe 设备合规性校验
- 支持 6 种校验类型：identify / namespace / smart / error_log / feature / fw_slot
- 支持 12 种规则操作：not_empty / not_zero / gte / lte / range / regex / in_set / len_lte / len_gte / increased / format
- 规则定义在 `app/rules/` 目录下的 YAML 文件中
- 校验结果：PASS / PARTIAL / FAIL

### AnalysisService

- 读取 prompts 目录中的系统提示词和用户提示模板
- 聚合任务、FIO、主机监控、磁盘监控上下文
- 调用 OpenAI 兼容接口生成分析报告
- 采用异步线程提交，接口立即返回 analyzing 状态
- **时序数据压缩**：最多保留 120 个采样点，控制 LLM 上下文长度

### BaselineService

- 从成功任务创建基线（提取 FIO 配置和结果）
- 基线列表、详情查询
- 删除时检查回归引用约束

### RegressionService

- 对比任务结果与基线的 4 个指标：IOPS / BW / lat_mean / lat_p99
- 计算差异百分比，基于阈值表判定 PASS / WARNING / FAIL
- 阈值：IOPS/BW 低于 -5% 警告 / -10% 失败；延迟高于 +10% / +20% 失败

### FwUpgradeService

- 端到端固件升级验证自动化
- 流程：采集基线 → 等待升级 → 升级后测试 → 回归分析 → 生成报告
- 支持固件版本采集（fw_before / fw_after）

### SniaService

- SNIA 标准 SSD 性能测试
- 三阶段自动流水线：Precondition → IOPS Test → Steady State
- Phase 1：顺序写 128k 预处理
- Phase 2：6 种块大小 × 4 种 pattern = 24 种组合 FIO 测试
- Phase 3：多轮 4k randwrite，检测 IOPS 收敛（最近 5 轮最大偏差 < 10%）
- 通过 threading.Thread 在后台执行，支持 abort 中断

### GroupTaskService

- 多盘并发任务组管理
- 一次操作选择多台设备并发执行相同 FIO 配置
- 为每台设备创建子任务（Task with is_sub_task=True）
- 所有子任务完成后自动聚合统计：IOPS / BW / 延迟的 max / min / avg
- 状态管理：running → done（全部成功）/ partial（部分成功）/ failed

### DataLifecycleService

- 数据列表、概览、下载
- 手动归档、压缩、删除
- 自动归档与自动清理
- 三阶段数据管理：Active → Archived → Compressed
- SHA256 校验和验证数据完整性

## 数据模型概览

init_mysql.sql 维护的核心表包括：

| 表名 | 说明 |
|------|------|
| devices | 设备信息（IP/名称/Agent状态/心跳） |
| tasks | FIO 测试任务（配置/状态/结果/子任务关联） |
| fio_trend_data | FIO 趋势数据 |
| host_monitor_data | 主机监控数据 |
| disk_monitor_data | 磁盘监控汇总 |
| disk_monitor_samples | 磁盘监控样本（细粒度指标） |
| nvme_smart_data | NVMe SMART 数据 |
| ai_analyses | AI 分析报告 |
| data_records | 数据记录元数据（active/archived/compressed） |
| baselines | 性能基线 |
| regression_results | 回归测试结果 |
| group_tasks | 多盘并发任务组 |
| snia_tasks | SNIA 测试任务 |
| fw_upgrade_tests | 固件升级测试 |
| nvme_tests | NVMe 校验测试记录 |

## API 分组

所有业务接口前缀均为 /api。

### 健康检查

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/health | 服务健康检查 |

### 任务接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/tasks | 任务列表 |
| POST | /api/tasks | 创建任务 |
| GET | /api/tasks/<int:task_id> | 任务详情 |
| GET | /api/tasks/<int:task_id>/status | 任务状态 |
| GET | /api/tasks/<int:task_id>/raw | 任务原始输出 |
| DELETE | /api/tasks/<int:task_id> | 删除任务 |
| GET | /api/tasks/<int:task_id>/trend | 获取趋势 |
| POST | /api/tasks/<int:task_id>/stop | 停止任务 |
| POST | /api/tasks/<int:task_id>/retry | 重试任务 |

### 设备接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/devices | 设备列表 |
| POST | /api/devices | 新增设备 |
| PUT | /api/devices/<int:device_id> | 更新设备 |
| DELETE | /api/devices/<int:device_id> | 删除设备 |
| GET | /api/devices/<int:device_id>/info | 获取设备详情与磁盘信息 |
| POST | /api/devices/test-connection | 测试 Agent 连通性 |
| GET | /api/devices/<int:device_id>/agent-status | 刷新并读取 Agent 状态 |

### 监控接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/monitor/hosts/<host>/metrics | 主机监控历史 |
| GET | /api/monitor/hosts/<host>/disks | 设备磁盘列表 |
| GET | /api/monitor/hosts/<host>/disks/<disk>/metrics | 磁盘监控数据 |
| GET | /api/monitor/hosts/<host>/summary | 主机概览 |

### SMART 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/devices/<int:device_id>/smart/latest | 最新 SMART |
| GET | /api/devices/<int:device_id>/smart/history | SMART 历史 |
| GET | /api/devices/<int:device_id>/smart/health-score | 健康评分 |
| GET | /api/devices/<int:device_id>/smart/alerts | SMART 告警 |

### NVMe 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/devices/<int:device_id>/nvme/list | NVMe 设备列表 |
| GET | /api/devices/<int:device_id>/nvme/<disk>/id-ctrl | NVMe identify controller |
| GET | /api/devices/<int:device_id>/nvme/<disk>/id-ns | NVMe identify namespace |
| GET | /api/devices/<int:device_id>/nvme/<disk>/error-log | NVMe 错误日志 |
| GET | /api/devices/<int:device_id>/nvme/<disk>/get-feature | NVMe feature 读取 |
| GET | /api/devices/<int:device_id>/nvme/<disk>/fw-log | NVMe 固件日志 |
| POST | /api/devices/<int:device_id>/nvme/validate | 发起 NVMe 校验测试 |
| GET | /api/nvme-tests/<test_id> | 获取 NVMe 校验结果 |
| GET | /api/devices/<int:device_id>/nvme-tests | NVMe 校验列表 |

### AI 分析接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/tasks/<int:task_id>/ai-analysis | 提交异步分析任务 |
| GET | /api/tasks/<int:task_id>/ai-analysis | 获取最新分析结果 |
| GET | /api/tasks/<int:task_id>/ai-analysis/history | 获取历史分析 |

### 仪表盘接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/dashboard/summary | 仪表盘汇总（设备/任务/趋势） |

### 数据治理接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/data | 数据记录列表 |
| GET | /api/data/overview | 数据概览 |
| POST | /api/data/download | 下载数据 |
| POST | /api/data/archive | 归档数据 |
| POST | /api/data/delete | 删除数据 |
| POST | /api/data/auto-archive-and-cleanup | 触发自动归档和清理 |
| POST | /api/data/compress | 压缩数据 |
| POST | /api/data/cleanup | 立即清理 |

### 基线管理接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/baselines | 创建基线 |
| GET | /api/baselines | 基线列表 |
| GET | /api/baselines/<int:baseline_id> | 基线详情 |
| DELETE | /api/baselines/<int:baseline_id> | 删除基线 |

### 回归测试接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/regressions | 执行回归测试 |
| GET | /api/regressions | 回归列表 |
| GET | /api/regressions/<int:regression_id> | 回归详情 |

### 固件升级测试接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/fw-tests | 创建固件测试 |
| GET | /api/fw-tests | 固件测试列表 |
| GET | /api/fw-tests/<int:test_id> | 固件测试详情 |
| POST | /api/fw-tests/<int:test_id>/confirm-upgrade | 确认已升级 |
| POST | /api/fw-tests/<int:test_id>/abort | 终止固件测试 |
| GET | /api/fw-tests/<int:test_id>/report | 固件测试报告 |

### SNIA 测试接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/snia-tasks | 创建 SNIA 测试 |
| GET | /api/snia-tasks | SNIA 任务列表 |
| GET | /api/snia-tasks/<int:task_id> | SNIA 任务详情 |
| POST | /api/snia-tasks/<int:task_id>/abort | 终止 SNIA 任务 |
| GET | /api/snia-tasks/<int:task_id>/report | SNIA 报告 |

### 多盘并发任务组接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/group-tasks | 创建任务组 |
| GET | /api/group-tasks | 任务组列表 |
| GET | /api/group-tasks/<int:group_id> | 任务组详情 |
| DELETE | /api/group-tasks/<int:group_id> | 删除任务组 |

### 内部 ingest 接口

这些接口由 Agent 使用，不面向前端：

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/internal/ingest/fio-trend | FIO 趋势上报 |
| POST | /api/internal/ingest/disk-monitor | 磁盘监控上报 |
| POST | /api/internal/ingest/host-monitor | 主机监控上报 |
| POST | /api/internal/ingest/nvme-smart | NVMe SMART 上报 |
| POST | /api/internal/ingest/flush-task | 任务状态刷新 |
| POST | /api/internal/ingest/heartbeat | Agent 心跳上报 |

## 配置

app/config.py 支持通过 .env 或系统环境变量加载配置。

常用变量如下：

| 变量 | 说明 |
|------|------|
| FLASK_DEBUG | Flask 调试开关 |
| HOST / PORT | run.py 启动时实际使用的监听地址和端口 |
| DATABASE_URL | 完整数据库连接串，优先级高于 MYSQL_* |
| MYSQL_HOST / MYSQL_PORT / MYSQL_USER / MYSQL_PASSWORD / MYSQL_DATABASE | MySQL 拆分配置 |
| AI_API_KEY | AI 服务密钥 |
| AI_BASE_URL | OpenAI 兼容服务地址 |
| AI_MODEL | 模型名 |
| AI_ANALYSIS_MAX_AGE_DAYS | 分析结果缓存年龄 |
| MONITOR_RETENTION_DAYS | 监控数据保留天数 |
| NVME_SMART_RETENTION_DAYS | SMART 数据保留天数 |
| DATA_ARCHIVE_RETENTION_DAYS | 归档数据保留天数 |
| DATA_COMPRESS_RETENTION_DAYS | 压缩数据保留天数 |

## 本地启动

```bash
cd backend
pip install -r requirements.txt
python run.py
```

默认服务地址为 0.0.0.0:5000。

## 数据库初始化

首次运行前请先执行 init_mysql.sql。该脚本不仅初始化数据库，还包含一组 add_column_if_missing 和 add_index_if_missing 过程，用于兼容增量演进。

## 集成验证

仓库提供 verify_integration.py，用于本地模拟 Agent 并验证设备、任务、趋势、监控、AI 分析等关键流程。

```bash
cd backend
python verify_integration.py
```
