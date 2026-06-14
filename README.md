# SSD Engine

SSD Engine 是一个围绕 SSD/NVMe 测试任务、运行态监控和结果分析构建的全栈平台。当前仓库由三部分组成：部署在设备侧的 Agent、负责编排与存储的 Backend、以及面向操作人员的 Frontend。

## 核心能力

- **FIO 任务管理**：创建、下发、停止、重试、查看详情与趋势，支持引导模式和原生命令模式
- **设备管理**：登记设备、刷新 Agent 状态、获取磁盘信息
- **监控采集**：采集主机指标（CPU/内存/网络）、磁盘指标（IOPS/带宽/延迟/队列深度）和 NVMe SMART 数据
- **NVMe 健康评估**：基于 SMART 数据计算 5 维度健康评分（温度/磨损/介质错误/临界告警/备用空间），支持 6 条告警规则
- **AI 分析**：按任务时间窗聚合 FIO、主机监控、磁盘监控数据，通过 LLM 生成结构化分析报告
- **数据治理**：查看数据概览，执行归档、压缩、下载、清理

## 当前架构

```text
Frontend (React + TypeScript + Vite + Ant Design)
        |
        | /api
        v
Backend (Flask + SQLAlchemy + MySQL)
        |
        | HTTP
        v
Agent (Flask, deployed on target host)
        |
        +-- run fio
        +-- collect host metrics (CPU/Memory/Network)
        +-- collect disk metrics (IOPS/BW/latency/util)
        +-- collect NVMe SMART
```

## 仓库结构

```text
ssd_engine/
├── agent/          设备侧服务，负责执行 fio 和采集运行态数据
│   ├── collectors/     数据采集器（CPU/内存/网络/磁盘/NVMe/SMART）
│   ├── executor/       FIO 任务执行器
│   ├── agent_server.py Agent 主服务
│   └── ingest_client.py 数据上报客户端
├── backend/        平台后端，负责设备、任务、分析、数据生命周期
│   ├── app/
│   │   ├── api/        REST API 接口
│   │   ├── services/   业务逻辑层
│   │   ├── models/     数据模型
│   │   ├── executors/  Agent 通信执行器
│   │   └── prompts/    AI 分析提示词
│   └── init_mysql.sql  数据库初始化脚本
├── frontend/       React 控制台
│   └── src/pages/      页面组件（仪表盘/任务/设备/监控/数据管理）
├── docs/           补充文档与截图目录
└── README.md
```

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | React 18, TypeScript, Vite, Ant Design |
| 后端 | Python 3.10+, Flask, SQLAlchemy, MySQL 8.x |
| 设备侧 | Python, Flask, FIO, nvme-cli, psutil |
| AI 分析 | OpenAI 兼容接口 |

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

## 默认端口

- Frontend: 3000
- Backend: 5000
- Agent: 8080
- MySQL: 3306

## 子模块文档

- agent/README.md：Agent 进程模型、接口和配置说明
- backend/README.md：后端模块、API 分组、存储与调度说明
- frontend/README.md：前端页面结构、接口映射和开发方式
