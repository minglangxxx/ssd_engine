# Backend

Backend 是 SSD Engine 的控制面，负责设备管理、任务编排、监控与 SMART 数据存储、AI 分析、数据生命周期管理，并对前端暴露统一的 /api 接口。

## 目录结构

```text
backend/
├── run.py
├── init_mysql.sql
├── verify_integration.py
├── app/
│   ├── __init__.py       应用工厂与定时任务启动
│   ├── api/              REST 路由
│   ├── config.py         环境变量配置
│   ├── executors/        AgentExecutor 等执行器
│   ├── models/           SQLAlchemy 模型
│   ├── prompts/          AI 分析提示词
│   ├── schemas/          Pydantic 请求校验
│   ├── services/         核心业务服务
│   └── utils/            响应、日志、时间处理
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

Backend 会启动一个 Asia/Shanghai 时区的后台调度器，每天 02:00 执行一次数据生命周期任务：

1. 自动归档超期 active 数据
2. 清理超过保留期的数据

默认保留策略由 MONITOR_RETENTION_DAYS 控制。

## 核心服务

### DeviceService

- 设备新增、更新、删除
- Agent 状态刷新
- 设备信息和磁盘列表查询
- 按设备记录中的 agent_port 创建 AgentExecutor

### TaskService

- 创建任务
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

### AnalysisService

- 读取 prompts 目录中的系统提示词和用户提示模板
- 聚合任务、FIO、主机监控、磁盘监控上下文
- 调用 OpenAI 兼容接口生成分析报告
- 采用异步线程提交，接口立即返回 analyzing 状态

### DataLifecycleService

- 数据列表、概览、下载
- 手动归档、压缩、删除
- 自动归档与自动清理

## 数据模型概览

init_mysql.sql 维护的核心表包括：

- tasks
- fio_trend_data
- host_monitor_data
- disk_monitor_samples
- nvme_smart_data
- ai_analyses
- data_records
- devices

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

### AI 分析接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/tasks/<int:task_id>/ai-analysis | 提交异步分析任务 |
| GET | /api/tasks/<int:task_id>/ai-analysis | 获取最新分析结果 |
| GET | /api/tasks/<int:task_id>/ai-analysis/history | 获取历史分析 |

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

### 内部 ingest 接口

这些接口由 Agent 使用，不面向前端：

- POST /api/internal/ingest/fio-trend
- POST /api/internal/ingest/disk-monitor
- POST /api/internal/ingest/host-monitor
- POST /api/internal/ingest/nvme-smart
- POST /api/internal/ingest/flush-task

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
