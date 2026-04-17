# Backend 模块说明

Backend 是平台控制面，负责设备管理、任务编排、数据持久化、AI 分析与生命周期治理，对 Frontend 暴露统一 REST API。

## 1. 架构说明

### 1.1 分层架构

```text
API Layer (app/api)
    -> Service Layer (app/services)
        -> Executor Layer (app/executors)
            -> Agent HTTP API
        -> Model Layer (app/models, MySQL)
```

### 1.2 目录结构

```text
backend/
├── run.py
├── init_mysql.sql
└── app/
    ├── api/            路由入口与参数接收
    ├── services/       业务编排与规则处理
    ├── executors/      执行器抽象（当前主要是 AgentExecutor）
    ├── models/         数据模型（任务、设备、趋势、监控、分析、数据记录）
    ├── schemas/        请求参数校验
    └── utils/          响应与通用工具
```

## 2. 业务逻辑说明

### 2.1 设备管理逻辑

- 新增设备后自动探测 Agent 状态
- 设备列表查询时可刷新在线状态与最后心跳
- 支持设备信息更新、删除、连通性测试

### 2.2 任务编排逻辑

1. 接收任务创建请求并做参数校验
2. 生成统一任务模型并落库
3. 通过 `AgentExecutor` 调用目标设备 Agent 启动 fio
4. 周期刷新任务状态并落库趋势数据
5. 支持任务停止、重试与详情回放

### 2.3 监控与分析逻辑

- 监控服务聚合主机与磁盘指标，为前端提供窗口查询
- AI 分析按任务时间窗聚合 fio 与监控上下文生成报告
- 当分析结果不存在时，接口返回 `idle` 状态，便于前端统一处理

### 2.4 数据生命周期逻辑

- 查询：支持按类型、状态、设备、任务、时间窗口过滤
- 管理：支持手动归档、压缩、删除与下载打包
- 自动化：提供归档与清理触发接口，便于运维任务编排

## 3. API 说明

所有接口统一前缀为 `/api`。

### 3.1 任务接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/tasks` | 任务列表（分页、状态、关键词过滤） |
| POST | `/api/tasks` | 创建任务 |
| GET | `/api/tasks/<task_id>` | 任务详情 |
| GET | `/api/tasks/<task_id>/status` | 任务状态 |
| GET | `/api/tasks/<task_id>/trend` | 任务趋势（`start/end`） |
| POST | `/api/tasks/<task_id>/stop` | 停止任务 |
| POST | `/api/tasks/<task_id>/retry` | 重试任务 |
| DELETE | `/api/tasks/<task_id>` | 删除任务 |

### 3.2 设备接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/devices` | 设备列表 |
| POST | `/api/devices` | 新增设备 |
| PUT | `/api/devices/<device_id>` | 更新设备 |
| DELETE | `/api/devices/<device_id>` | 删除设备 |
| GET | `/api/devices/<device_id>/info` | 设备详情 |
| POST | `/api/devices/test-connection` | 连接测试 |
| GET | `/api/devices/<device_id>/agent-status` | Agent 状态 |

### 3.3 监控接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/monitor/hosts/<host>/metrics` | 主机指标 |
| GET | `/api/monitor/hosts/<host>/disks` | 磁盘列表 |
| GET | `/api/monitor/hosts/<host>/disks/<disk>/metrics` | 磁盘指标 |
| GET | `/api/monitor/hosts/<host>/summary` | 主机概览 |

### 3.4 AI 分析接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/tasks/<task_id>/ai-analysis` | 发起分析 |
| GET | `/api/tasks/<task_id>/ai-analysis` | 获取最新分析 |
| GET | `/api/tasks/<task_id>/ai-analysis/history` | 获取历史分析 |

### 3.5 数据管理接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/data` | 数据列表 |
| GET | `/api/data/overview` | 存储概览 |
| POST | `/api/data/download` | 下载打包 |
| POST | `/api/data/archive` | 手动归档 |
| POST | `/api/data/delete` | 手动删除 |
| POST | `/api/data/auto-archive-and-cleanup` | 触发自动归档与清理 |
| POST | `/api/data/compress` | 触发压缩 |
| POST | `/api/data/cleanup` | 触发清理 |

## 4. 配置与启动

### 4.1 关键环境变量

- `MYSQL_HOST`、`MYSQL_PORT`、`MYSQL_USER`、`MYSQL_PASSWORD`、`MYSQL_DATABASE`
- `APP_HOST`、`APP_PORT`
- `AI_API_KEY`、`AI_BASE_URL`、`AI_MODEL`
- `MONITOR_RETENTION_DAYS`

### 4.2 启动命令

```bash
cd backend
pip install -r requirements.txt
python run.py
```
