# Agent 模块说明

Agent 是部署在被测设备上的轻量服务，负责执行 fio、采集主机/磁盘监控与 SMART 信息，并向 Backend 提供 HTTP 接口。

## 1. 架构说明

### 1.1 模块结构

```text
agent/
├── agent_server.py               服务入口与路由
├── config.py                     环境变量与配置
├── ingest_client.py              批量上报客户端
├── collectors/                   采集层
│   ├── cpu_collector.py
│   ├── memory_collector.py
│   ├── disk_collector.py
│   ├── network_collector.py
│   ├── system_collector.py
│   └── smart_collector.py
└── executor/
    └── fio_runner.py             fio 任务执行与趋势采集
```

### 1.2 运行架构

- HTTP 接口层：对外提供健康检查、任务执行、监控查询
- 任务执行层：`FioRunner` 负责任务生命周期与趋势解析
- 监控采集层：各 Collector 每秒采样一次系统与磁盘指标
- 缓冲与上报层：Ring Buffer 保存短期历史，`ingest_client` 批量推送 Backend

## 2. 业务逻辑说明

### 2.1 fio 任务执行链路

1. Backend 调用 `POST /fio/start`
2. Agent 创建任务上下文并启动 fio 子进程
3. 任务运行中持续解析趋势数据
4. Backend 或用户调用 `POST /fio/stop/<task_id>` 停止任务
5. 通过 `GET /fio/status/<task_id>` 与 `GET /fio/trend/<task_id>` 获取状态与趋势

### 2.2 监控采集链路

1. 后台线程每秒采集 CPU、内存、网络、系统、磁盘指标
2. 数据写入内存 Ring Buffer（用于历史查询）
3. 按配置批量上报至 Backend 持久化

### 2.3 设计要点

- Agent 靠近设备，降低采集与执行延迟
- 与平台通过 HTTP 解耦，便于横向扩展多节点
- 采集与执行分线程运行，降低互相阻塞风险

## 3. API 说明

### 3.1 基础接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| POST | `/execute` | 执行通用命令（调试用途） |

### 3.2 FIO 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/fio/start` | 启动任务（`task_id`, `device`, `config`） |
| GET | `/fio/status/<task_id>` | 查询任务状态 |
| GET | `/fio/trend/<task_id>` | 查询任务趋势（支持 `start/end`） |
| POST | `/fio/stop/<task_id>` | 停止任务 |

### 3.3 监控接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/monitor/host` | 主机实时快照 |
| GET | `/monitor/host/history` | 主机历史指标 |
| GET | `/monitor/disks` | 磁盘列表 |
| GET | `/monitor/disk/<disk_name>` | 单盘实时指标 |
| GET | `/monitor/disk/<disk_name>/history` | 单盘历史指标 |

### 3.4 SMART 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/smart/<device>` | NVMe SMART 信息 |

## 4. 配置与启动

### 4.1 依赖要求

- Python 3.10+
- Linux 环境
- fio（必需）
- nvme-cli（建议）

### 4.2 关键环境变量

- `AGENT_HOST`、`AGENT_PORT`
- `BACKEND_URL`
- `AGENT_DEVICE_IP`
- `INGEST_TIMEOUT_SECONDS`
- `FIO_INGEST_INTERVAL_SECONDS`
- `DISK_INGEST_INTERVAL_SECONDS`
- `INGEST_BATCH_SIZE`

### 4.3 启动命令

```bash
cd agent
pip install -r requirements.txt
python agent_server.py
```
