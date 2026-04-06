# SSD 测试平台 - Agent

部署在每个设备节点上的轻量级 HTTP 服务，负责执行 FIO 测试任务、实时采集主机和磁盘级监控数据、采集 NVMe SMART 健康信息。

## 技术栈

| 类别 | 技术 | 版本 |
|------|------|------|
| Web 框架 | Flask | 3.1 |
| 系统采集 | psutil | 7.0 |

## 项目结构

```
agent/
├── agent_server.py         # HTTP 服务入口 + 路由 + 后台采集线程
├── config.py               # 配置（HOST / PORT / VERSION）
├── requirements.txt        # Python 依赖
│
├── collectors/             # 数据采集器
│   ├── cpu_collector.py    # CPU 使用率、负载、iowait 等
│   ├── memory_collector.py # 内存/Swap 使用情况
│   ├── disk_collector.py   # 磁盘 IOPS/带宽/延迟/util/队列深度
│   ├── network_collector.py# 网络速率/丢包/TCP 连接数
│   ├── system_collector.py # 系统信息（内核、uptime、CPU 型号等）
│   └── smart_collector.py  # NVMe SMART 健康指标
│
└── executor/               # FIO 任务执行
    └── fio_runner.py       # FIO 启动/状态/趋势采集/停止
```

## 环境要求

- Python 3.10+
- Linux 系统（依赖 `/proc`、`/sys`、`lsblk` 等）
- `fio` 已安装（用于性能测试）
- `nvme-cli` 已安装（用于 SMART 采集，可选）

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动 Agent

```bash
python agent_server.py
```

默认监听 `0.0.0.0:8080`，可通过环境变量覆盖：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `AGENT_HOST` | 监听地址 | `0.0.0.0` |
| `AGENT_PORT` | 监听端口 | `8080` |
| `AGENT_VERSION` | 版本号 | `0.1.0` |

### 3. 验证

```bash
curl http://localhost:8080/health
# {"status": "healthy", "version": "0.1.0"}
```

## 生产部署

### Systemd 服务

```ini
# /etc/systemd/system/ssd-agent.service
[Unit]
Description=SSD Test Agent
After=network.target

[Service]
ExecStart=/usr/bin/python3 /opt/ssd-agent/agent_server.py
Restart=always
User=root

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now ssd-agent
```

### Docker 部署

```dockerfile
FROM python:3.11-slim
RUN apt-get update && apt-get install -y fio nvme-cli && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -r requirements.txt
EXPOSE 8080
CMD ["python", "agent_server.py"]
```

```bash
docker build -t ssd-agent .
docker run -d --privileged --network host --name ssd-agent ssd-agent
```

> `--privileged` 用于访问块设备和 SMART 信息，`--network host` 避免端口映射开销。

## HTTP API

### 通用

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查，返回 `status` 和 `version` |
| POST | `/execute` | 执行任意命令（`command`, `timeout`） |

### FIO 任务管理

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/fio/start` | 启动 FIO 任务（`task_id`, `config`, `device`） |
| GET | `/fio/status/<task_id>` | 获取任务状态（`pending`/`running`/`success`/`failed`） |
| GET | `/fio/trend/<task_id>` | 获取实时趋势数据（`start`/`end` 过滤） |
| POST | `/fio/stop/<task_id>` | 停止 FIO 任务 |

**FIO 趋势数据点格式**：

```json
{
  "timestamp": 1711958400.0,
  "iops_read": 50000,
  "iops_write": 48000,
  "iops_total": 98000,
  "bw_read": 200000,
  "bw_write": 195000,
  "bw_total": 395000,
  "lat_mean": 65.2,
  "lat_p99": 210.5,
  "lat_max": 1200.0
}
```

### 主机监控

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/monitor/host` | 当前主机快照（CPU/内存/网络/系统） |
| GET | `/monitor/host/history` | 历史数据（`start`/`end` 时间戳过滤） |

**主机快照字段**：

- **CPU**: `cpu_usage_percent`, `cpu_iowait_percent`, `load_avg_1m/5m/15m`, ...
- **内存**: `mem_total_bytes`, `mem_used_bytes`, `mem_usage_percent`, `swap_*`, ...
- **网络**: `net_rx/tx_bytes_per_sec`, `net_rx/tx_packets_per_sec`, `tcp_connections`, ...
- **系统**: `uptime_seconds`, `kernel_version`, `hostname`, `cpu_model`, ...

### 磁盘监控

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/monitor/disks` | 磁盘列表（包含未挂载的 NVMe 设备） |
| GET | `/monitor/disk/<disk_name>` | 单磁盘实时快照 |
| GET | `/monitor/disk/<disk_name>/history` | 单磁盘历史数据 |

**磁盘监控字段**：

- `disk_iops_read/write`, `disk_bw_read/write_bytes_per_sec`
- `disk_latency_read/write_ms`, `disk_await_ms`
- `disk_util_percent`, `disk_queue_depth`

### SMART 健康

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/smart/<device>` | NVMe SMART 信息（如 `/smart/nvme0`） |

**SMART 字段**：`smart_temperature`, `smart_percentage_used`, `smart_power_on_hours`, `smart_media_errors`, `smart_critical_warning`, `smart_available_spare`, ...

## 内部机制

### 后台采集

Agent 启动时会开启一个后台守护线程，**每秒采集一次**所有监控数据（CPU/内存/网络/磁盘），存入内存 Ring Buffer（默认保留最近 3600 个数据点，即 1 小时）。

### FIO 执行

- FIO 任务在独立线程中执行，支持多任务并发
- 自动加 `--output-format=json` 和 `--status-interval=1`
- 执行期间开启趋势采集线程，每秒读取 FIO 状态文件解析实时性能指标
- 趋势数据保留在内存 deque 中（最多 86400 个点）

## 与 Backend 的关系

```
Backend (Flask API) ──HTTP──► Agent (设备节点)
    │                              │
    │  AgentExecutor               │  采集器 + FIO Runner
    │  调用 Agent HTTP API         │  执行实际操作
    └──────────────────────────────┘
```

Backend 的 `AgentExecutor` 通过 HTTP 调用 Agent 的各个接口，实现远程设备管理。每个待测设备节点需要独立部署一个 Agent 实例。
