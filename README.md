# SSD Engine

SSD Engine 是一个面向 SSD 性能测试、设备监控和结果分析的一体化平台。项目由前端 Web、后端 API 和部署在设备节点上的 Agent 三部分组成，核心目标是把 FIO 测试执行、设备状态采集、趋势数据留存和 AI 分析串成一条可追踪的完整链路。

## 项目摘要

- 面向 SSD 或 NVMe 设备的 FIO 测试平台
- 支持设备接入、任务编排、实时趋势、历史监控和 AI 分析
- 前后端分离，执行链路统一通过 Agent HTTP 下发
- 同时支持引导式任务配置和原生 fio 标准命令

## 快速导航

- 想先跑起来：看“快速开始”
- 想看系统组成：看“系统架构”和“模块说明”
- 想部署：看“部署建议”
- 想验证功能：看“开发与验证”
- 想继续深入：看“进一步阅读”

## 核心能力

- 基于 FIO 发起 SSD 性能测试，支持常规引导式配置和原生 fio 标准命令输入
- 通过 Agent 在设备节点执行测试任务，并实时回传任务状态与趋势数据
- 采集主机和磁盘维度监控数据，包括 CPU、内存、磁盘繁忙度、延迟等指标
- 提供设备管理、任务管理、监控看板、数据管理和 AI 分析页面
- 在任务结束后，按 fio 执行时间窗口聚合 FIO 指标与主机/磁盘监控数据生成 AI 分析报告

## 系统架构

```text
Frontend (React + Vite)
        |
        | HTTP / REST
        v
Backend (Flask API + MySQL)
        |
        | HTTP / Agent API
        v
Agent (部署在设备节点)
        |
        +-- 执行 fio
        +-- 采集主机监控
        +-- 采集磁盘监控
        +-- 采集 SMART 信息
```

## 页面预览

当前仓库还没有统一整理的截图资源，建议后续统一补到 docs/screenshots 目录。可直接参考 docs/screenshots/README.md 中的命名约定和补充清单。根 README 先预留展示位：

### 仪表盘

截图占位：任务概览、设备状态、全局趋势图

### 任务创建

截图占位：引导配置模式、原生命令模式、模板和摘要区

### 任务详情

截图占位：FIO 趋势图、结果摘要、AI 分析报告

### 设备与监控

截图占位：设备管理页、主机监控页、磁盘监控页

## 仓库结构

```text
ssd_engine/
├── agent/                  设备节点 Agent，负责执行 fio 和采集监控
├── backend/                Flask 后端，负责 API、任务编排、数据存储、AI 分析
├── frontend/               React 前端，负责页面展示和交互
├── 后端详细设计文档.md      后端设计说明
├── 前端详细设计文档.md      前端设计说明
└── 架构待优化项.md          当前架构问题与待优化方向
```

## 模块说明

### frontend

前端基于 React 18、TypeScript、Ant Design、React Query 和 ECharts，主要包含以下页面：

- 仪表盘
- 任务管理与任务详情
- 主机监控与磁盘监控
- 设备管理
- 数据管理
- AI 分析面板

当前任务创建支持两种模式：

- 引导配置：通过模板和常用参数快速创建任务
- 原生命令：直接输入标准 fio CLI，由后端解析并统一下发

### backend

后端基于 Flask，负责：

- 设备管理与 Agent 状态刷新
- 测试任务创建、状态同步、停止和重试
- FIO 趋势数据保存与查询
- 主机与磁盘监控代理访问
- AI 分析上下文拼装与结果保存
- 数据生命周期管理

后端当前通过 Agent HTTP 接口驱动设备节点，不依赖任务维度 SSH 信息执行 fio。

### agent

Agent 部署在被测设备节点，负责：

- 暴露健康检查与执行接口
- 启动和停止 fio 任务
- 输出 fio 趋势数据
- 周期采集主机和磁盘历史监控
- 采集 NVMe SMART 信息

Agent 适合部署在 Linux 设备节点，要求主机已安装 fio，建议安装 nvme-cli 以便采集 SMART 数据。

## 为什么这样设计

- 前端只负责交互和可视化，不直接接触设备执行细节
- 后端负责任务模型、校验、状态聚合和 AI 分析上下文拼装
- Agent 靠近设备节点，适合执行 fio、读取系统指标和提供低延迟监控接口
- 这种拆分可以把设备现场能力、平台控制面和展示层解耦，便于扩展多节点和多任务场景

## 典型流程

### 1. 设备接入

1. 在设备节点启动 Agent
2. 在前端设备管理页添加设备 IP 和 Agent 端口
3. 后端通过 Agent 健康接口刷新在线状态、最后心跳和设备磁盘列表

### 2. 创建并执行测试任务

1. 在前端任务列表中创建任务
2. 选择设备节点和目标磁盘
3. 使用引导配置或原生命令指定 FIO 参数
4. 后端校验配置后调用 Agent 的 fio 启动接口
5. Agent 执行测试并持续上报趋势数据

### 3. 查看结果与分析

1. 前端任务详情页读取任务状态和 fio 趋势
2. 触发 AI 分析后，后端按任务实际执行时间窗口抓取 FIO、主机和磁盘历史数据
3. AI 分析结果写入数据库，前端展示 Markdown 报告和摘要指标

## 环境要求

### 通用

- Git
- Node.js 18+
- Python 3.10+

### backend

- MySQL 8.x
- 可访问 OpenAI 兼容接口的网络环境，如果需要 AI 分析

### agent

- Linux 设备节点
- fio
- nvme-cli，可选但推荐

## 快速开始

推荐启动顺序：Agent -> Backend -> Frontend。

### 1. 启动 Agent

```bash
cd agent
pip install -r requirements.txt
python agent_server.py
```

默认监听地址：

- AGENT_HOST=0.0.0.0
- AGENT_PORT=8080

健康检查示例：

```bash
curl http://127.0.0.1:8080/health
```

### 2. 启动 Backend

先初始化数据库。仓库内提供了 backend/init_mysql.sql 可直接建库。

随后安装依赖并启动：

```bash
cd backend
pip install -r requirements.txt
python run.py
```

常用环境变量包括：

- MYSQL_HOST
- MYSQL_PORT
- MYSQL_USER
- MYSQL_PASSWORD
- MYSQL_DATABASE
- AI_API_KEY
- AI_BASE_URL
- AI_MODEL

后端默认监听 5000 端口，接口前缀为 /api。

### 3. 启动 Frontend

```bash
cd frontend
npm install
npm run dev
```

开发模式下，前端会把 /api 代理到本地后端。

生产构建命令：

```bash
npm run build
```

## 部署建议

### 最小部署

适合单机联调或小规模验证：

1. 在设备节点部署并启动 Agent
2. 在服务端部署 Backend 和 MySQL
3. 在同机或独立前端主机部署 Frontend 静态资源

### 推荐拓扑

- Frontend：Nginx 托管静态文件
- Backend：Gunicorn 或等价 WSGI 方式运行 Flask
- Database：MySQL 独立实例
- Agent：每个被测设备节点独立运行一个实例

### Backend 生产启动示例

```bash
cd backend
gunicorn -w 4 -b 0.0.0.0:5000 run:app
```

### Frontend 部署示例

```bash
cd frontend
npm install
npm run build
```

将 dist 目录交给 Nginx 托管，并把 /api 反向代理到 Backend。

### Agent 部署建议

- 建议使用 systemd 托管
- 建议以具备块设备访问能力的账号运行
- 若需要读取 SMART，确保 nvme-cli 可用
- 若使用容器部署，通常需要额外设备权限

### 端口建议

- Frontend：3000，开发环境
- Backend：5000
- Agent：8080，默认值，可按设备独立修改
- MySQL：3306

## 关键接口

### Backend API

- GET /api/devices
- POST /api/devices
- GET /api/tasks
- POST /api/tasks
- GET /api/tasks/:id
- GET /api/tasks/:id/trend
- POST /api/tasks/:id/ai-analysis
- GET /api/tasks/:id/ai-analysis
- GET /api/monitor/hosts/:host/metrics
- GET /api/monitor/hosts/:host/disks/:disk/metrics

### Agent API

- GET /health
- POST /fio/start
- GET /fio/status/:task_id
- GET /fio/trend/:task_id
- POST /fio/stop/:task_id
- GET /monitor/host/history
- GET /monitor/disks
- GET /monitor/disk/:disk_name/history
- GET /smart/:device

## 当前实现特点

- AI 分析接口在任务存在但还没有分析结果时返回 idle 状态，而不是 404
- AI 分析支持前后时间窗配置，会围绕 fio 实际执行区间抓取监控历史
- 设备列表在进入页面时会刷新 Agent 状态和最后心跳时间
- 主机监控和磁盘监控页面默认选中最近新增的设备节点
- 任务创建已移除任务维度 SSH 字段，执行链路统一走 Agent HTTP
- 原生 fio 命令会先在后端解析和校验，再落入统一任务模型执行

## 开发与验证

### 常用本地启动命令

```bash
# terminal 1
cd agent
python agent_server.py

# terminal 2
cd backend
python run.py

# terminal 3
cd frontend
npm run dev
```

### 后端集成验证

```bash
cd backend
python verify_integration.py
```

该脚本会验证：

- 设备接入与 Agent 状态刷新
- 任务创建、状态流转、停止与重试
- FIO 趋势读取
- AI 分析上下文拼装
- 原生 fio 命令任务创建

### 前端构建验证

```bash
cd frontend
npm run build
```

## 进一步阅读

- agent/README.md
- backend/README.md
- frontend/README.md
- 后端详细设计文档.md
- 前端详细设计文档.md
- 架构待优化项.md

## 适用场景

本项目适合以下场景：

- SSD 或 NVMe 设备性能验证
- FIO 压测结果留存与趋势追踪
- 测试窗口内系统资源变化分析
- 基于测试结果和监控数据生成自动化分析报告