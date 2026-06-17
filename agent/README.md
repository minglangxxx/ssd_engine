# Agent

Agent 是部署在被测机器上的轻量服务。它负责四件事：执行 fio、采集主机与磁盘指标、采集 NVMe SMART、执行 NVMe 命令，并通过 HTTP 接口供 Backend 调用。

## 目录结构

```text
agent/
├── agent_server.py      Flask 服务入口，包含全部 HTTP 路由
├── config.py            从 .env 和环境变量加载配置
├── ingest_client.py     向 Backend 内部 ingest API 批量上报数据
├── logger.py            Agent 日志初始化
├── collectors/          主机、磁盘、SMART 采集器
│   ├── cpu_collector.py
│   ├── memory_collector.py
│   ├── network_collector.py
│   ├── disk_collector.py
│   ├── system_collector.py
│   ├── nvme_collector.py
│   └── smart_collector.py
├── executor/
│   └── fio_runner.py    FIO 启动、停止、状态与趋势解析
├── build.sh             Linux 下使用 PyInstaller 打包
├── .env.example         Agent 环境变量示例
└── requirements.txt
```

## 运行模型

### HTTP 服务

Agent 通过 Flask 提供接口，Backend 通过这些接口驱动任务与采集。

### 后台采集线程

agent_server.py 启动时会拉起一个守护线程，每秒采集一次：

- CPU 利用率
- 内存使用率
- 网络流量
- 系统概览（运行时间、负载）
- 磁盘运行态（IOPS、带宽、延迟、队列深度、util）

采样结果先写入内存中的 MonitorRingBuffer（默认容量 3600 秒），用于历史查询；如果配置了 BACKEND_URL，则同时批量上报到 Backend。

### 心跳上报

Agent 按 HEARTBEAT_INTERVAL_SECONDS 周期（默认 30 秒）向 Backend 发送心跳，Backend 据此判断 Agent 是否在线。

### SMART 周期采集

后台线程还会按 SMART_COLLECT_INTERVAL_SECONDS 周期扫描 NVMe 盘并采集 SMART 数据，再通过 ingest_client 推送给 Backend。

SMART 采集基于 nvme-cli 工具，采集以下指标：
- temperature（温度）
- percentage_used（磨损度）
- power_on_hours（通电时间）
- power_cycles（通电周期）
- media_errors（介质错误）
- critical_warning（临界警告）
- data_units_read / data_units_written（读写量）
- available_spare（备用空间）

**数据归一化处理**：
- uint64 溢出处理：当值为 2^64 的倍数时，自动除以 2^64
- 温度偏移处理：当温度值 > 200 且为 256 的倍数时，自动除以 256

### FIO 执行

FioRunner 负责：

- 启动 fio 子进程
- 维护任务状态（running/stopped/completed/error）
- 解析 JSON 输出，提取 IOPS、带宽、延迟（mean/P95/P99/max）等指标
- 停止任务
- 向 Backend 周期上报趋势数据

### NVMe 命令执行

NvmeCollector 支持以下 NVMe 命令：

- `id-ctrl`：读取 NVMe identify controller 信息
- `id-ns`：读取 NVMe identify namespace 信息
- `error-log`：读取 NVMe 错误日志
- `error-log-verify`：交叉验证（两次采集比对 SMART 计数器单调性 + 缓冲区一致性）
- `get-feature`：读取 NVMe feature（默认 0x06）
- `fw-log`：读取 NVMe 固件日志

### 并发控制

- MonitorRingBuffer 使用 threading.Lock 保证线程安全
- 数据上报使用批量提交，减少网络开销
- SMART 采集使用独立周期，避免与监控采集冲突

## HTTP API

### 基础接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /health | 健康检查，返回 status/version/hostname/cpu/memory |
| POST | /execute | 执行命令，主要用于调试或补充诊断 |

### FIO 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /fio/start | 启动任务，请求体包含 task_id、device、config |
| GET | /fio/status/<task_id> | 查询任务状态和结果 |
| GET | /fio/trend/<task_id> | 查询任务趋势，支持 start/end 时间过滤 |
| POST | /fio/stop/<task_id> | 停止任务 |

### 监控接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /monitor/host | 获取主机实时快照 |
| GET | /monitor/host/history | 从 RingBuffer 获取主机历史，支持时间范围查询 |
| GET | /monitor/disks | 获取当前磁盘列表 |
| GET | /monitor/disk/<disk_name> | 获取单盘实时数据 |
| GET | /monitor/disk/<disk_name>/history | 获取单盘历史数据 |

### SMART 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /smart/<path:device> | 读取指定设备路径的 SMART 信息 |

### NVMe 命令接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /nvme/<device>/id-ctrl | NVMe identify controller |
| GET | /nvme/<device>/id-ns | NVMe identify namespace |
| GET | /nvme/<device>/error-log | NVMe 错误日志 |
| GET | /nvme/<device>/get-feature | NVMe feature 读取（默认 0x06） |
| GET | /nvme/<device>/fw-log | NVMe 固件日志 |
| POST | /nvme/<device>/error-log-verify | NVMe 错误日志交叉验证（两次采集比对） |

## 配置

config.py 会先尝试读取 agent/.env，再回退到系统环境变量。

常用配置项如下：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| AGENT_HOST | 0.0.0.0 | Agent 监听地址 |
| AGENT_PORT | 8080 | Agent 监听端口 |
| AGENT_VERSION | 0.1.0 | /health 返回的版本号 |
| BACKEND_URL | 空 | Backend 地址，留空则不做数据上报 |
| AGENT_DEVICE_IP | 空 | 上报到 Backend 时使用的设备 IP，应与 devices 表一致 |
| INGEST_TIMEOUT_SECONDS | 5 | 上报请求超时 |
| FIO_INGEST_INTERVAL_SECONDS | 3 | FIO 趋势上报周期 |
| DISK_INGEST_INTERVAL_SECONDS | 3 | 磁盘监控上报周期 |
| INGEST_BATCH_SIZE | 20 | 批量上报阈值 |
| SMART_COLLECT_INTERVAL_SECONDS | 60 | SMART 采集周期 |
| SMART_INGEST_INTERVAL_SECONDS | 60 | SMART 上报周期 |
| HEARTBEAT_INTERVAL_SECONDS | 30 | 心跳上报周期 |
| MONITOR_RING_BUFFER_SIZE | 3600 | 监控数据环形缓冲区容量（秒） |

参考配置见 .env.example。

## 启动方式

```bash
cd agent
pip install -r requirements.txt
python agent_server.py
```

默认启动地址为 0.0.0.0:8080。

## 依赖说明

- Python 3.10+
- Flask
- psutil
- fio（需提前安装）
- nvme-cli（SMART 和 NVMe 命令采集需要）

如果需要在 Linux 上打包单文件可执行程序，可使用：

```bash
cd agent
chmod +x build.sh
./build.sh
```

打包脚本会调用 PyInstaller 生成 dist/ssd-agent。

## 与 Backend 的协作关系

- Backend 通过设备表中的 agent_port 访问 Agent，不应假定所有 Agent 都是 8080
- Agent 的监控和趋势上报走 Backend 的 /api/internal/ingest/* 接口
- Agent 每 30 秒向 Backend 发送心跳，Backend 据此判断 Agent 在线状态
- 如果 BACKEND_URL 未配置，Agent 仍可独立提供本地查询接口，但数据不会持久化到平台侧
- Agent 与 Backend 之间通过 HTTP 通信，Agent 作为服务端，Backend 作为客户端主动调用
