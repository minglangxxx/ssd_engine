# SSD 测试平台 - Backend

Flask REST API 服务端，为 SSD 性能测试平台提供任务管理、设备管理、实时监控、AI 分析和数据生命周期管理能力。

## 技术栈

| 类别 | 技术 | 版本 |
|------|------|------|
| Web 框架 | Flask | 3.1 |
| ORM | Flask-SQLAlchemy | 3.1 |
| 数据库迁移 | Flask-Migrate | 4.1 |
| 数据库 | MySQL (PyMySQL) | 8.x |
| 参数校验 | Pydantic | 2.x |
| 定时任务 | APScheduler | 3.10 |
| AI 集成 | OpenAI SDK | 1.x |
| SSH | Paramiko | 3.x |
| HTTP 客户端 | Requests | 2.x |

## 项目结构

```
backend/
├── run.py                  # 启动入口
├── requirements.txt        # Python 依赖
├── .env.example            # 环境变量示例
├── init_mysql.sql          # 数据库初始化脚本
├── start_backend.ps1       # Windows 一键启动脚本
├── verify_integration.py   # 集成验证脚本
│
└── app/
    ├── __init__.py         # Flask 应用工厂 (create_app)
    ├── config.py           # 配置管理 (从 .env 加载)
    ├── extensions.py       # 扩展初始化 (db, migrate)
    │
    ├── api/                # API 路由层
    │   ├── task.py         # 任务 CRUD、趋势、停止、重试
    │   ├── device.py       # 设备 CRUD、连接测试、Agent 状态
    │   ├── monitor.py      # 主机/磁盘实时监控
    │   ├── analysis.py     # AI 智能分析
    │   └── data.py         # 数据生命周期管理
    │
    ├── services/           # 业务逻辑层
    │   ├── task_service.py       # 任务调度与执行
    │   ├── device_service.py     # 设备与 Agent 管理
    │   ├── monitor_service.py    # 监控数据代理
    │   ├── analysis_service.py   # AI 大模型分析
    │   └── data_lifecycle.py     # 数据归档/压缩/删除
    │
    ├── executors/          # 执行器抽象层
    │   ├── base.py         # Executor 基类 + CommandResult
    │   ├── agent_executor.py   # Agent HTTP 执行器
    │   └── __init__.py     # 执行器工厂
    │
    ├── models/             # SQLAlchemy 数据模型
    │   ├── task.py         # 测试任务
    │   ├── device.py       # 设备节点
    │   ├── fio_trend.py    # FIO 趋势数据
    │   ├── monitor_data.py # 监控数据快照
    │   ├── analysis.py     # AI 分析结果
    │   └── data_record.py  # 数据记录 (生命周期)
    │
    ├── schemas/            # Pydantic 请求/响应模式
    ├── workloads/          # FIO 工作负载封装
    └── utils/              # 日志、响应助手等工具
```

## 环境要求

- Python 3.12+
- MySQL 8.x
- Agent 已部署在目标设备节点上（见 [agent/README.md](../agent/README.md)）

## 快速开始

### 1. 初始化数据库

使用有权限的 MySQL 账号执行：

```sql
SOURCE init_mysql.sql;
```

或手动执行：

```sql
CREATE DATABASE IF NOT EXISTS ssd_engine CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'ssd_engine'@'%' IDENTIFIED BY 'change_me';
GRANT ALL PRIVILEGES ON ssd_engine.* TO 'ssd_engine'@'%';
FLUSH PRIVILEGES;
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件，配置以下关键项：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `MYSQL_HOST` | MySQL 地址 | `127.0.0.1` |
| `MYSQL_PORT` | MySQL 端口 | `3306` |
| `MYSQL_USER` | MySQL 用户名 | `root` |
| `MYSQL_PASSWORD` | MySQL 密码 | - |
| `MYSQL_DATABASE` | 数据库名 | `ssd_engine` |
| `APP_HOST` | 监听地址 | `0.0.0.0` |
| `APP_PORT` | 监听端口 | `5000` |
| `AI_API_KEY` | AI 大模型 API Key | - |
| `AI_BASE_URL` | AI API 地址 | `https://api.openai.com/v1` |
| `AI_MODEL` | AI 模型名称 | `gpt-4.1` |
| `LOG_LEVEL` | 日志级别 | `INFO` |

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 启动服务

**方式一**：直接运行

```bash
python run.py
```

**方式二**：使用 PowerShell 脚本（Windows）

```powershell
./start_backend.ps1
```

**方式三**：使用 Gunicorn（生产环境，Linux）

```bash
gunicorn -w 4 -b 0.0.0.0:5000 run:app
```

服务启动后访问 `http://localhost:5000/api/health` 验证。

## API 接口

所有接口前缀为 `/api`，返回格式统一为：

```json
{"success": true, "data": ...}
```

### 任务管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/tasks` | 任务列表（支持 `status`/`keyword` 过滤，分页） |
| POST | `/api/tasks` | 创建任务 |
| GET | `/api/tasks/:id` | 任务详情 |
| GET | `/api/tasks/:id/status` | 任务状态 |
| GET | `/api/tasks/:id/trend` | FIO 实时趋势数据（`start`/`end` 过滤） |
| POST | `/api/tasks/:id/stop` | 停止任务 |
| POST | `/api/tasks/:id/retry` | 重试任务 |
| DELETE | `/api/tasks/:id` | 删除任务 |

### 设备管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/devices` | 设备列表 |
| POST | `/api/devices` | 添加设备 |
| PUT | `/api/devices/:id` | 更新设备 |
| DELETE | `/api/devices/:id` | 删除设备 |
| GET | `/api/devices/:id/info` | 设备详细信息 |
| GET | `/api/devices/:id/agent-status` | Agent 在线状态 |
| POST | `/api/devices/test-connection` | 测试连接 |

### 实时监控

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/monitor/hosts/:host/metrics` | 主机监控（快照 / 历史） |
| GET | `/api/monitor/hosts/:host/summary` | 主机概览 |
| GET | `/api/monitor/hosts/:host/disks` | 磁盘列表 |
| GET | `/api/monitor/hosts/:host/disks/:disk/metrics` | 磁盘监控 |

### AI 分析

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/tasks/:id/ai-analysis` | 触发 AI 分析 |
| GET | `/api/tasks/:id/ai-analysis` | 获取最新分析结果 |
| GET | `/api/tasks/:id/ai-analysis/history` | 分析历史 |

### 数据管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/data` | 数据记录列表（支持 `data_type`/`status`/`device_ip` 过滤） |
| GET | `/api/data/overview` | 存储概览统计 |
| POST | `/api/data/download` | 打包下载（传 `ids` 数组） |
| POST | `/api/data/archive` | 手动归档 |
| POST | `/api/data/delete` | 手动删除 |

## 数据生命周期

| 阶段 | 时间 | 状态 | 存储 |
|------|------|------|------|
| 活跃 | 0-7 天 | `active` | 原始 JSON，可直接查询 |
| 归档 | 8-30 天 | `archived` | 原始 JSON，可查询 |
| 压缩 | 31-60 天 | `compressed` | `.tar.gz`，可下载 |
| 删除 | >60 天 | - | 自动清除 |

定时任务每天凌晨 2:00 自动执行。

## 核心架构

```
Frontend ──API──► Backend (Flask) ──HTTP──► Agent (设备节点)
                      │                        │
                  MySQL DB               FIO / 系统监控
                      │
                  AI 大模型
```

- **Executor 抽象层**：`AgentExecutor` 通过 HTTP 调用远端 Agent，`base.py` 定义统一接口
- **Service 层**：业务逻辑封装，独立于 API 框架
- **Model 层**：SQLAlchemy ORM 映射，`create_all()` 自动建表

## API Base URL

Frontend should call `http://<backend-host>:5000/api`.

## Notes

- Task creation immediately triggers `Agent /fio/start`.
- Task list and detail requests will refresh runtime status from the Agent when possible.
- Agent is expected to run on Linux and expose port `8080` by default.
