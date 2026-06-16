# V1 基础测试平台 — 详细实施与编码规范

> 本文档基于 `SSD_Engine_Plan.md` 和 `product-roadmap-schedule.md` 的差距分析，给出 V1 阶段（4周）的具体编码实现方案。
> 目标：**端到端跑通一次 FIO 测试并生成 AI 报告**，同时在开发前统一后端/前端/Agent 三层的规范。

---

## 一、差距分析总结 功能 | 当前状态 | 差距 | 决策 |
|------|---------|------|------|
| Agent 心跳 | Server 主动轮询（30s APScheduler） | 缺 hostname/os/kernel/cpu/mem 字段 | **保留 Server-pull 架构**，扩充 Agent `/health` 返回主机信息 |
| Agent 列表页 | DeviceManage 页已有，缺主机指标 | CPU/MEM 未采集、无 10s 轮询 | Agent 采集信息扩展，前端加轮询+主机指标列 |
| FIO 测试 | Server-push 模式已完整跑通 | 无 Jinja2 模板（Agent 自行拼命令） | **保留 Server-push**，不做 Agent-pull 改造 |
| Dashboard | 框架已有，统计卡片和设备状态已用真实数据 | IOPS趋势图硬编码假数据、无 CPU/MEM 卡片、无 5s 自动刷新 | 替换图表硬编码 + 新增 CPU/MEM 卡片 + 5s 轮询 |
| AI 报告 | 完成度最高，超规划 | 已完成（system_prompt + user_prompt 均为中文） | 无需改动 |

---

## 二、架构决策

### 2 保留 Server-pull 而非 Agent-push

**原因：**
1. 现有架构已稳定跑通完整链路（Server → Agent HTTP → 执行 → Ingest 回传）
2. 改为 Agent-push 心跳需要 Agent 侧定时器、重连、认证，改动大且收益低
3. APScheduler + ThreadPoolExecutor 已实现等价功能

**改造方向：**
- **不新增** `POST /api/agent/heartbeat` 接口
- **扩展** Agent `/health` 端点返回主机信息（hostname, os, kernel, cpu_usage, memory_usage）
- **扩充** `Device` 模型字段以存储这些信息
- Server 的 `DeviceStatusChecker` 已每 30s 探测一次，在探测时顺便拉取 `/health` 拿到主机指标

### 2.2 保留 Server-push FIO 任务下发

现有 `POST /fio/start` 已工作，不做 Agent-poll 改造。

### 2.3 Dashboard 聚合 API

新增 `GET /api/dashboard/summary`，一次请求返回所有 Dashboard 需要的数据，避免前端发 3~4 个请求拼装。

---

## 三、数据库模型变更

### 3.1 Device 表扩展字段

```sql
ALTER TABLE devices ADD COLUMN hostname VARCHAR(64) DEFAULT NULL;
ALTER TABLE devices ADD COLUMN os_version VARCHAR(128) DEFAULT NULL;
ALTER TABLE devices ADD COLUMN kernel_version VARCHAR(128) DEFAULT NULL;
ALTER TABLE devices ADD COLUMN cpu_usage FLOAT DEFAULT NULL;
ALTER TABLE devices ADD COLUMN memory_usage FLOAT DEFAULT NULL;
```

### 3.2 Task 表 — 无需变更

现有字段已覆盖规划需求（`device_id` 等价 `agent_id`，`config/result` 为 JSON）。

### 3.3 不新增 `agent` 表

Device 表即为 Agent 表，保持统一。

---

## 四、后端编码规范与实现方案

### 4.1 通用编码规范

| 规范 | 说明 |
|------|------|
| Python 版本 | 3.12+ |
| 类型注解 | 所有函数必须有参数和返回值类型注解 |
| docstring | 不写，靠函数名和类型注解自解释 |
| 异常处理 | Service 层 catch 后转为 `ApiError`，API 层不再 catch |
| 日志 | 使用 `get_logger(__name__)`，关键操作（创建/删除/下发）记录 info，异常记录 error |
| DB 会话 | HTTP 调用前必须用 `db_released()` 释放连接 |
| JSON 字段 | 仅用于 FIO config / result 等灵活结构，业务实体用独立列 |
| 时间 | 全部使用 `datetime.utcnow` 存储，展示层由 `to_beijing_iso` 转换 |

### 4.2 模型变更 (`backend/app/models/device.py`)

```python
# 新增字段
hostname = db.Column(db.String(64), nullable=True)
os_version = db.Column(db.String(128), nullable=True)
kernel_version = db.Column(db.String(128), nullable=True)
cpu_usage = db.Column(db.Float, nullable=True)
memory_usage = db.Column(db.Float, nullable=True)
```

`to_dict()` 方法新增这些字段的输出，并增加 `include_disks` 参数控制是否输出磁盘详情（列表 API 默认不输出 disks 避免 N+1 问题，详情 API 通过 `get_info` 单独获取）：

```python
def to_dict(self, include_disks: bool = False) -> dict:
    result = {
        'id': self.id,
        'ip': self.ip,
        'name': self.name,
        'agent_status': self.agent_status,
        'agent_version': self.agent_version or '',
        'agent_port': self.agent_port,
        'last_heartbeat': to_beijing_iso(self.last_heartbeat, assume_utc=True),
        'hostname': self.hostname,
        'os_version': self.os_version,
        'kernel_version': self.kernel_version,
        'cpu_usage': self.cpu_usage,
        'memory_usage': self.memory_usage,
        'created_at': to_beijing_iso(self.created_at, assume_utc=True),
        'updated_at': to_beijing_iso(self.updated_at, assume_utc=True),
        # disks 键始终存在，保持向后兼容（现有前端 Device 类型中 disks 为必填字段）
        'disks': [d.to_dict() for d in getattr(self, 'disks', [])] if include_disks else [],
    }
    return result
```

> 新增字段通过 `init_mysql.sql` 的 `add_column_if_missing` 存储过程追加，与现有增量迁移模式一致。

### 4.3 AgentExecutor 扩展 (`backend/app/executors/agent_executor.py`)

不新增 `get_host_info()` 方法。现有 `get_health()` 已调用 `GET /health` 并返回原始 JSON，Agent `/health` 端点扩展后，`get_health()` 返回的 dict 自然包含 hostname/os_version/kernel_version/cpu_usage/memory_usage 字段。所有消费方直接调用 `get_health()` 即可，无需新增方法。

V2.5 预留方法新增：

```python
def get_nvme_feature(self, device: str, fid: str = '0x06') -> dict[str, Any]:
    response = self.session.get(
        f'{self.agent_url}/nvme/{device}/get-feature',
        params={'fid': fid}, timeout=15,
    )
    response.raise_for_status()
    return response.json()

def get_nvme_fw_log(self, device: str) -> dict[str, Any]:
    response = self.session.get(
        f'{self.agent_url}/nvme/{device}/fw-log', timeout=15,
    )
    response.raise_for_status()
    return response.json()
```

### 4.4 DeviceStatusChecker 改造 (`backend/app/services/device_status_checker.py`)

现有逻辑：探测 Agent → 更新 status/version/heartbeat

改造：探测 Agent 时调用已有 `agent.get_health()`，从返回 dict 中提取主机信息写入 Device 表。保持两段式 commit 模式（先 commit 释放连接 → 并发 HTTP → 再 commit 写入），批量并发场景不适用 `db_released()` 上下文管理器。

```python
def _check_single_device(ip: str, agent_port: int) -> dict:
    agent = AgentExecutor(f'http://{ip}:{agent_port}')
    try:
        health = agent.get_health()  # 直接调用，成功即在线，避免 test_connection+get_health 重复请求同一 /health
        return {
            'status': 'online',
            'version': health.get('version', ''),
            'hostname': health.get('hostname'),
            'os_version': health.get('os_version'),
            'kernel_version': health.get('kernel_version'),
            'cpu_usage': health.get('cpu_usage'),
            'memory_usage': health.get('memory_usage'),
        }
    except Exception:
        return {'status': 'offline', 'version': ''}
    finally:
        agent.close()
```

`check_all_agents()` 中更新 Device 记录时扩展写入：

```python
for device_id, result in results.items():
    device = Device.query.get(device_id)
    if device is None:
        continue
    device.agent_status = result['status']
    device.agent_version = result['version']
    if result['status'] == 'online':
        device.last_heartbeat = datetime.utcnow()
        # 主机静态信息仅在线时更新，离线不清空（hostname/os/kernel 不因离线而消失）
        device.hostname = result.get('hostname')
        device.os_version = result.get('os_version')
        device.kernel_version = result.get('kernel_version')
        # 实时指标在线时刷新，离线时清空（值已无意义，避免显示过期数据）
        device.cpu_usage = result.get('cpu_usage')
        device.memory_usage = result.get('memory_usage')
    else:
        device.cpu_usage = None
        device.memory_usage = None

db.session.commit()
```

### 4.5 DeviceService.get_agent_status 扩展 (`backend/app/services/device_service.py`)

现有 `get_agent_status` 仅更新 `agent_status`/`agent_version`/`last_heartbeat`，用户新增设备后需等 30s 下一个 `check_all_agents` 周期才能看到主机信息。扩展为在线时也写入主机字段，与 DeviceStatusChecker 逻辑一致：

```python
def get_agent_status(self, device_id: int) -> dict:
    device = self.get(device_id)
    agent = self.get_agent(device)
    with db_released():
        online = agent.test_connection()
        health = agent.get_health() if online else {}
    try:
        device.agent_status = 'online' if online else 'offline'
        device.agent_version = health.get('version', '') if online else ''
        if online:
            device.last_heartbeat = datetime.utcnow()
            device.hostname = health.get('hostname')
            device.os_version = health.get('os_version')
            device.kernel_version = health.get('kernel_version')
            device.cpu_usage = health.get('cpu_usage')
            device.memory_usage = health.get('memory_usage')
        else:
            device.cpu_usage = None
            device.memory_usage = None
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    finally:
        agent.close()
    return {'status': device.agent_status, 'version': device.agent_version or ''}
```

### 4.6 新增 Dashboard API (`backend/app/api/dashboard.py`)

```python
@api_bp.get('/dashboard/summary')
def dashboard_summary():
    return success_response(DashboardService.get_summary())
```

### 4.7 新增 DashboardService (`backend/app/services/dashboard_service.py`)

> **数据粒度说明**：`chart_data` 为任务级趋势（每个已完成任务一个数据点），展示平台历史 IOPS/Latency 走势。
> 与任务详情页的 FIO 秒级趋势图（`FioTrendData`，1 秒一个点）是**不同粒度**的数据，请勿混淆。

```python
import time

_cache: dict[str, tuple[float, dict]] = {}
CACHE_TTL = 5  # 秒，与前端 refetchInterval 对齐，避免多用户高频查 DB


class DashboardService:
    @staticmethod
    def get_summary() -> dict:
        now = time.time()
        cached = _cache.get('summary')
        if cached and now - cached[0] < CACHE_TTL:
            return cached[1]

        # 1. Agent 统计
        total = Device.query.count()
        online = Device.query.filter_by(agent_status='online').count()

        # 2. CPU/MEM 平均值（仅 online Agent）
        online_devices = Device.query.filter_by(agent_status='online').all()
        cpu_values = [d.cpu_usage for d in online_devices if d.cpu_usage is not None]
        mem_values = [d.memory_usage for d in online_devices if d.memory_usage is not None]
        avg_cpu = round(sum(cpu_values) / len(cpu_values), 1) if cpu_values else None
        avg_memory = round(sum(mem_values) / len(mem_values), 1) if mem_values else None

        # 3. 任务统计
        total_tasks = Task.query.count()
        running_tasks = Task.query.filter_by(status=TaskStatus.RUNNING).count()
        success_tasks = Task.query.filter_by(status=TaskStatus.SUCCESS).count()
        failed_tasks = Task.query.filter_by(status=TaskStatus.FAILED).count()

        # 4. 最近 30 条已完成任务（图表用 30 条，表格取前 10 条）
        MAX_RECENT_CHART = 30
        MAX_RECENT_TABLE = 10
        recent = Task.query.filter(
            Task.status.in_([TaskStatus.SUCCESS, TaskStatus.FAILED])
        ).order_by(Task.created_at.desc()).limit(MAX_RECENT_CHART).all()

        # Python 层过滤：确保 result 包含 iops（排除纯 error result），
        # 避免 MySQL JSON 列 isnot(None) 在 JSON null 与 SQL NULL 上的歧义
        recent = [t for t in recent if t.result and 'iops' in t.result]

        recent_tasks = []
        for t in recent[:MAX_RECENT_TABLE]:
            r = t.result or {}
            lat = r.get('latency') or {}
            # bandwidth 单位：Agent 返回 KiB/s，转为 MiB/s
            bw_kib = r.get('bandwidth')
            bw_mib = round(bw_kib / 1024, 2) if bw_kib else None
            recent_tasks.append({
                'id': t.id,
                'name': t.name,
                'status': t.status,
                'iops': r.get('iops'),
                'bw_mib': bw_mib,
                'lat_mean_us': lat.get('mean'),
                'lat_max_us': lat.get('max'),
                'created_at': to_beijing_iso(t.created_at, assume_utc=True),
            })

        # 5. 图表数据（按时间正序，过滤掉无 finished_at 的任务）
        # chart_data 为任务级趋势（每个已完成任务一个数据点），
        # 展示平台历史 IOPS/Latency 走势，与任务详情页的 FIO 秒级趋势图是不同粒度
        chart_data = []
        for t in reversed([t for t in recent if t.finished_at is not None]):
            r = t.result or {}
            lat = r.get('latency') or {}
            iops = r.get('iops')
            lat_mean_us = lat.get('mean')
            # 微秒 → 毫秒
            lat_ms = round(lat_mean_us / 1000, 3) if lat_mean_us else None
            chart_data.append({
                'time': to_beijing_iso(t.finished_at, assume_utc=True),
                'iops': iops,
                'lat_ms': lat_ms,
            })

        summary = {
            'agents': {'total': total, 'online': online},
            'avg_cpu': avg_cpu,
            'avg_memory': avg_memory,
            'tasks': {
                'total': total_tasks,
                'running': running_tasks,
                'success': success_tasks,
                'failed': failed_tasks,
            },
            'recent_tasks': recent_tasks,
            'chart_data': chart_data,
        }

        _cache['summary'] = (now, summary)
        return summary
```

### 4.8 AI Prompt — 无需改动

`backend/app/prompts/system_prompt.md` 和 `user_prompt_template.md` 已是全中文，差距分析表原标注有误，此任务项移除。

### 4.9 移除硬编码密码

后端 `backend/app/schemas/device.py` 中 `user` 和 `password` 为必填字段（`Field(...)`），但后端 `test_connection` 实际仅检测 Agent HTTP 可达性，`user`/`password` 被直接 `del` 丢弃。为与实际行为对齐，改为可选字段：

```python
class DeviceTestConnectionRequest(BaseModel):
    ip: str = Field(min_length=1, max_length=50)
    user: str | None = Field(default=None, max_length=64)
    password: str | None = Field(default=None, max_length=255)
    agent_port: int = Field(default=8080, ge=1, le=65535)
```

前端两处也需修复：

1. `frontend/src/api/device.ts` — 删除默认密码逻辑：
```typescript
testConnection: (params: { ip: string; user: string; password: string }) => {
    // 删除: password: params.password || '123456'
    return request.post<unknown, { success: boolean; message: string }>('/devices/test-connection', params);
},
```

2. `frontend/src/pages/DeviceDetail/BasicInfoTab.tsx` — 测试连接不再硬编码凭据：
```typescript
// 原代码: testMutation.mutate({ ip: deviceInfo.ip, user: 'root', password: '' })
// 后端 test_connection 已忽略 user/password（仅测 Agent HTTP），因此：
testMutation.mutate({
  ip: deviceInfo.ip,
  user: '',      // 后端会忽略
  password: '',  // 后端会忽略
});
```

---

## 五、Agent 编码规范与实现方案

### 5.1 通用编码规范

| 规范 | 说明 |
|------|------|
| Python 版本 | 3.12+ |
| 类型注解 | 所有函数必须有 |
| docstring | 不写 |
| 日志 | 使用 `get_logger(__name__)` |
| 命令执行 | 统一通过 `run_command()` 函数，timeout 默认 300s |
| 设备路径 | 所有设备路径必须带 `/dev/` 前缀，统一使用 `_normalize_smart_device_path()` |
| HTTP 客户端 | Agent 内部使用 `urllib.request`（无外部依赖），对 Backend 的 Ingest 调用走 `BackendIngestClient` |
| 错误处理 | 子进程执行失败不抛异常，返回空 dict / error 字段 |

### 5.2 `/health` 端点扩展 (`agent/agent_server.py`)

现有 `/health` 仅返回 `{status, version}`。扩展为同时返回主机信息，并在 JSON 输出中对 collector 原始字段名做一次映射简化（与 7.2.2 字段映射表对齐）：

每个 collector 调用需 try/except 保护，避免因 `/proc` 缺失或 psutil 异常导致 `/health` 返回 500，进而使 Server 误判 Agent 离线：

```python
@app.get('/health')
def health():
    try:
        system = system_collector.collect()
    except Exception:
        system = {}
    try:
        cpu = cpu_collector.collect()
    except Exception:
        cpu = {}
    try:
        memory = memory_collector.collect()
    except Exception:
        memory = {}
    return jsonify({
        'status': 'healthy',
        'version': Config.VERSION,
        'hostname': system.get('hostname', ''),
        'os_version': system.get('os_version', ''),
        'kernel_version': system.get('kernel_version', ''),
        'cpu_usage': cpu.get('cpu_usage_percent'),
        'memory_usage': memory.get('mem_usage_percent'),
    })
```

这样 Server 的 `DeviceStatusChecker` 每 30s 调用 `/health` 时自然拿到主机指标，无需额外请求。

### 5.3 新增 `/nvme/<device>/get-feature` 端点（V2.5 预留，V1 可选）

属于 V2.5 范畴，V1 不暴露 Server API、前端不调用。如果 V1 周期有余量可提前开发，但**不作为 V1 验收项**。未测试的代码路径不应阻塞 V1 发布。

```python
@app.get('/nvme/<path:device>/get-feature')
def nvme_get_feature(device: str):
    normalized = _normalize_smart_device_path(device)
    fid = request.args.get('fid', '0x06')
    result = run_command(f'nvme get-feature {normalized} -f {fid} -o json', timeout=15)
    try:
        return jsonify(json.loads(result['stdout']))
    except (json.JSONDecodeError, KeyError):
        return jsonify({'error': result.get('stderr', 'command failed')}), 502
```

### 5.4 新增 `/nvme/<device>/fw-log` 端点（V2.5 预留，V1 可选）

```python
@app.get('/nvme/<path:device>/fw-log')
def nvme_fw_log(device: str):
    normalized = _normalize_smart_device_path(device)
    result = run_command(f'nvme fw-log {normalized} -o json', timeout=15)
    try:
        return jsonify(json.loads(result['stdout']))
    except (json.JSONDecodeError, KeyError):
        return jsonify({'error': result.get('stderr', 'command failed')}), 502
```

---

## 六、前端编码规范与实现方案

### 6.1 通用编码规范

| 规范 | 说明 |
|------|------|
| TypeScript 严格模式 | `strict: true`，禁止 `any`（除第三方库类型不足处用 `// eslint-disable-next-line`） |
| 组件风格 | 函数组件 + Hooks，不使用 class 组件 |
| 样式方案 | Ant Design 内联 `style` 属性 + 少量全局 CSS（`src/styles/`），不使用 CSS-in-JS |
| 数据获取 | 全部使用 TanStack React Query，不使用 Zustand store 缓存服务端数据 |
| 状态管理 | 仅 UI 状态用 Zustand（`uiStore`），删除 `taskStore` 中与服务端重复的数据 |
| 路由 | React Router v6，懒加载各页面 |
| API 调用 | 统一通过 `src/api/` 模块，禁止组件内直接 `axios` 调用 |
| 图表 | ECharts via `echarts-for-react`，封装为可复用组件 |
| 中文 | UI 文案全中文 |
| 无 emoji | 代码和 UI 中不使用 emoji |

### 6.2 删除 taskStore

`frontend/src/stores/taskStore.ts` 无任何消费方（零引用），直接删除文件即可，无需修改其他文件。

V1 的筛选状态由 TaskList 页面本地 `statusFilter` state 管理，如未来需持久化再迁移到 URL search params。

### 6.3 useWebSocket hook 处理

当前 `useWebSocket.ts` 未被任何组件使用。

**决策：** V1 不使用 WebSocket，保持 HTTP 轮询。删除 `useWebSocket.ts`。

### 6.3.1 修复 NvmeListTab `smart-log` 类型未映射

`NvmeListTab.tsx` 中 modal 类型包含 `'smart-log'`，但 `useNvme.ts` 的 `useNvmeDetail` hook 的 `queryFnMap` 仅有 `id-ctrl`/`id-ns`/`error-log`，缺少 `smart-log` 映射。用户点击 SMART-LOG 按钮后 query 永远不会触发（`enabled: false`），modal 无数据。

**修复方案**（二选一）：

1. 在 `useNvmeDetail` 中补充 `smart-log` 类型和映射：
```typescript
type NvmeDetailType = 'id-ctrl' | 'id-ns' | 'smart-log' | 'error-log' | null;
const queryFnMap: Record<Exclude<NvmeDetailType, null>, (...) => Promise<...>> = {
  'id-ctrl': (deviceId, diskName) => nvmeApi.getIdCtrl(deviceId, diskName),
  'id-ns':   (deviceId, diskName) => nvmeApi.getIdNs(deviceId, diskName),
  'smart-log': (deviceId, diskName) => smartApi.getLatest(deviceId),  // 复用 SMART API
  'error-log': (deviceId, diskName) => nvmeApi.getErrorLog(deviceId, diskName),
};
```

2. 如果 `NvmeDetailModal` 已通过 `useSmartLatest` 独立处理 smart-log（当前实现方式），则从 `NvmeListTab` 的类型联合中移除 `'smart-log'`，避免类型不匹配的混淆路径。

**推荐方案 1**，统一数据获取入口，减少组件内部隐式依赖。

### 6.4 新增 Dashboard API 模块 (`frontend/src/api/dashboard.ts`)

```typescript
import request from '@/utils/request';

export interface DashboardSummary {
  agents: { total: number; online: number };
  avg_cpu: number | null;
  avg_memory: number | null;
  tasks: { total: number; running: number; success: number; failed: number };
  recent_tasks: RecentTask[];
  chart_data: ChartDataPoint[];
}

export interface RecentTask {
  id: number;
  name: string;
  status: string;
  iops: number | null;
  bw_mib: number | null;     // MiB/s（后端已从 KiB/s 转换）
  lat_mean_us: number | null; // 微秒（Agent 原始单位）
  lat_max_us: number | null;  // 微秒
  created_at: string;
}

export interface ChartDataPoint {
  time: string;
  iops: number | null;
  lat_ms: number | null;
}

export const dashboardApi = {
  summary: () => request.get<DashboardSummary>('/dashboard/summary'),
};
```

### 6.5 新增 Dashboard Hook (`frontend/src/hooks/useDashboard.ts`)

```typescript
import { useQuery } from '@tanstack/react-query';
import { dashboardApi } from '@/api/dashboard';

export const useDashboardSummary = () =>
  useQuery({
    queryKey: ['dashboard', 'summary'],
    queryFn: () => dashboardApi.summary(),
    refetchInterval: 5000,  // 5秒自动刷新
  });
```

### 6.6 Dashboard 页面改造 (`frontend/src/pages/Dashboard/index.tsx`)

**替换所有内容为真实数据：**

1. **统计卡片**：任务总数/运行中/成功/失败/设备在线 — 从 `summary.tasks` + `summary.agents` 获取
2. **新增卡片**：平均 CPU、平均 MEM — 从 `summary.avg_cpu` / `summary.avg_memory` 获取，值为 `null` 时显示 `--`
3. **最近任务表**：使用 `summary.recent_tasks` 数据（API 已限制 10 条）
4. **IOPS + Latency 双折线图**：使用 `summary.chart_data` 数据（API 返回 30 条，按时间正序），X 轴为 `time`，双 Y 轴分别对应 IOPS 和 Latency(ms)
5. **设备节点状态**：保留，但从现有 `deviceApi.list()` 获取（此部分不需要聚合 API）
6. **5秒自动刷新**：通过 `useDashboardSummary` hook 的 `refetchInterval: 5000` 实现
7. **图表空状态**：当 `chart_data` 为空数组时，用 `<Empty description="暂无已完成的测试任务" />` 替代图表

**图表数据映射：**

```typescript
// chart_data 已由后端按时间正序返回，直接使用
const trendOption = {
  tooltip: { trigger: 'axis' as const },
  xAxis: { type: 'category' as const, data: (summary.chart_data || []).map(d => d.time) },
  yAxis: [
    { type: 'value' as const, name: 'IOPS', position: 'left' as const },
    { type: 'value' as const, name: 'Latency(ms)', position: 'right' as const },
  ],
  series: [
    {
      name: 'IOPS',
      type: 'line',
      smooth: true,
      data: (summary.chart_data || []).map(d => d.iops),
      yAxisIndex: 0,
      areaStyle: { opacity: 0.1 },
    },
    {
      name: 'Latency(ms)',
      type: 'line',
      smooth: true,
      data: (summary.chart_data || []).map(d => d.lat_ms),
      yAxisIndex: 1,
    },
  ],
  grid: { top: 40, bottom: 30, left: 60, right: 60 },
};
```

### 6.8 DeviceManage 页面增强

新增列：主机名(hostname)、操作系统(os_version)、内核(kernel_version)、CPU%(cpu_usage)、MEM%(memory_usage)。

当值为 `null`/空时显示 `--`。

当前 DeviceManage 页面仅设 `refetchOnMount: 'always'`，无 `refetchInterval`。新增主机信息列后应增加 `refetchInterval: 30000`（与 Server 30s 更新周期对齐），使用户无需手动刷新即可看到最新主机状态。

### 6.7.1 DeviceDetail BasicInfoTab 主机信息字段布局

在现有 Descriptions 组件中，状态行之后新增以下行：

| 标签 | 字段 | 空值展示 |
|------|------|---------|
| 主机名 | hostname | -- |
| 操作系统 | os_version | -- |
| 内核版本 | kernel_version | -- |
| CPU 使用率 | cpu_usage | cpu_usage !== null ? `${cpu_usage}%` : '--' |
| 内存使用率 | memory_usage | memory_usage !== null ? `${memory_usage}%` : '--' |

CPU/MEM 值带 `%` 后缀，离线时显示 `--`。

### 6.8 Device 类型扩展 (`frontend/src/types/device.ts`)

```typescript
export interface Device {
  id: number;
  ip: string;
  name: string;
  agent_status: 'online' | 'offline';
  agent_version: string;
  agent_port: number;
  last_heartbeat: string;
  hostname?: string | null;
  os_version?: string | null;
  kernel_version?: string | null;
  cpu_usage?: number | null;
  memory_usage?: number | null;
  disks?: DeviceDisk[] | string[]; // 列表API可能为空，详情API返回完整
  created_at: string;
  updated_at: string;
}
```

---

## 七、三端对齐 — API 契约总表

### 7.1 Agent → Server（Ingest 内部接口，保持不变）

| Agent 调用 | Server 端点 | 用途 |
|-----------|------------|------|
| `POST /api/internal/ingest/fio-trend` | 已有 | FIO 趋势数据上报 |
| `POST /api/internal/ingest/disk-monitor` | 已有 | 磁盘监控数据上报 |
| `POST /api/internal/ingest/host-monitor` | 已有 | 主机监控数据上报 |
| `POST /api/internal/ingest/nvme-smart` | 已有 | NVMe SMART 数据上报 |
| `POST /api/internal/ingest/flush-task` | 已有 | 任务完成 flush |

### 7.2 Server → Agent（HTTP 请求，现有+新增）

| Server 调用 | Agent 端点 | 变更 |
|------------|-----------|------|
| `GET /health` | **扩展返回字段** | 新增 hostname/os/kernel/cpu/memory |
| `GET /monitor/host` | 不变 | |
| `GET /monitor/disks` | 不变 | |
| `GET /monitor/disk/<name>` | 不变 | |
| `GET /smart/<device>` | 不变 | |
| `GET /nvme/<device>/id-ctrl` | 不变 | |
| `GET /nvme/<device>/id-ns` | 不变 | |
| `GET /nvme/<device>/error-log` | 不变 | |
| `POST /fio/start` | 不变 | |
| `GET /fio/status/<task_id>` | 不变 | |
| `POST /fio/stop/<task_id>` | 不变 | |
| `GET /fio/trend/<task_id>` | 不变 | |
| `GET /nvme/<device>/get-feature` | **新增** | V2.5 预留（V1 可选开发，不作为验收项） |
| `GET /nvme/<device>/fw-log` | **新增** | V2.5 预留（V1 可选开发，不作为验收项） |

### 7.2.1 V2.5 预留端点说明

`/nvme/<device>/get-feature` 和 `/nvme/<device>/fw-log` 仅在 Agent 侧和 AgentExecutor 侧预留。
V1 不暴露 Server API 路由，前端不新增对应 API 模块。
V1 周期有余量可提前开发，但**不作为 V1 验收项**——未测试的代码路径不应阻塞 V1 发布。
待 V2.5 规划时再补齐 Server → 前端链路。

### 7.2.2 `/health` 字段映射表

| Collector 原始字段 | Agent JSON 输出 | 后端读取 | DB 列名 |
|---|---|---|---|
| SystemCollector: `hostname` | `hostname` | `health.get('hostname')` | `hostname` |
| SystemCollector: `os_version` | `os_version` | `health.get('os_version')` | `os_version` |
| SystemCollector: `kernel_version` | `kernel_version` | `health.get('kernel_version')` | `kernel_version` |
| CpuCollector: `cpu_usage_percent` | `cpu_usage` | `health.get('cpu_usage')` | `cpu_usage` |
| MemoryCollector: `mem_usage_percent` | `memory_usage` | `health.get('memory_usage')` | `memory_usage` |

Agent 端在 `/health` handler 中需做一次字段名映射（collector 原始名 → 简化名），见 5.2 节代码。

> **带宽单位说明**：Agent `_parse_result` 返回的 `bandwidth` 字段单位为 **KiB/s**（fio 原生输出），
> 后端 DashboardService 转换为 **MiB/s** 后输出为 `bw_mib` 字段（`bandwidth / 1024`），
> 前端显示标签为"带宽(MiB/s)"。

### 7.3 前端 → Server（API 接口）

| 前端调用 | Server 端点 | 变更 |
|---------|-----------|------|
| `GET /api/devices` | 返回字段扩展 | 新增 hostname/os/kernel/cpu/memory |
| `GET /api/tasks` | 不变 | |
| `POST /api/tasks` | 不变 | |
| `GET /api/tasks/:id` | 不变 | |
| `GET /api/tasks/:id/trend` | 不变 | |
| `POST /api/tasks/:id/ai-analysis` | 不变 | |
| `GET /api/tasks/:id/ai-analysis` | 不变 | |
| **`GET /api/dashboard/summary`** | **新增** | 一次返回所有 Dashboard 数据（bw_mib=MiB/s, lat_mean_us=微秒） |
| `GET /api/monitor/hosts/:host/metrics` | 不变 | |
| `GET /api/devices/:id/smart/latest` | 不变 | |
| `GET /api/data` | 不变 | |

---

## 八、开发排期（4 周）

### Week 1: Agent 扩展 + 后端模型 + Dashboard API

| 日 | 任务 | 涉及文件 |
|----|------|---------|
| D1 | Agent `/health` 端点扩展，返回主机信息（含 try/except 保护） | `agent/agent_server.py` |
| D1 | 后端 Device 模型新增字段 + `to_dict()` 始终包含 `disks` 键 | `backend/app/models/device.py` |
| D1 | 后端 `init_mysql.sql` 新增 ALTER 语句 | `backend/init_mysql.sql` |
| D2 | DeviceStatusChecker 改造，写入主机指标（仅在线时写主机信息，离线清空 cpu/mem） | `backend/app/services/device_status_checker.py` |
| D2 | DeviceService.get_agent_status 扩展，新增设备即时获取主机信息 | `backend/app/services/device_service.py` |
| D3 | 新增 DashboardService（字段映射与 Agent _parse_result 对齐） | `backend/app/services/dashboard_service.py` |
| D3 | 新增 Dashboard API 路由 | `backend/app/api/dashboard.py` |
| D3 | 在 `__init__.py` 注册 dashboard 蓝图路由 | `backend/app/api/__init__.py` |
| D4 | 前端新增 `dashboard.ts` API 模块 | `frontend/src/api/dashboard.ts` |
| D4 | 前端新增 `useDashboard.ts` hook | `frontend/src/hooks/useDashboard.ts` |
| D5 | 联调：Agent 启动 → Server 30s 内拿到主机信息 → Device 模型更新 | 全链路 |

### Week 2: Dashboard 页面改造 + DeviceManage 增强

| 日 | 任务 | 涉及文件 |
|----|------|---------|
| D1 | Dashboard 统计卡片替换为真实数据 | `frontend/src/pages/Dashboard/index.tsx` |
| D1 | 新增 CPU/MEM 平均值卡片 | 同上 |
| D2 | IOPS + Latency 双折线图替换硬编码数据 | 同上 |
| D2 | 5 秒自动刷新验证 | 同上 |
| D3 | Device 类型扩展 | `frontend/src/types/device.ts` |
| D3 | DeviceManage 表格新增主机信息列 + refetchInterval: 30000 | `frontend/src/pages/DeviceManage/index.tsx` |
| D4 | DeviceDetail BasicInfoTab 展示主机信息 | `frontend/src/pages/DeviceDetail/BasicInfoTab.tsx` |
| D5 | 删除 `taskStore` 中冗余数据、删除 `useWebSocket.ts` | stores / hooks |
| D5 | 修复 NvmeListTab `smart-log` 类型未映射到 useNvmeDetail | `frontend/src/hooks/useNvme.ts`, `frontend/src/pages/DeviceDetail/NvmeListTab.tsx` |

### Week 3: 安全修复 + Schema 对齐 + 回归

| 日 | 任务 | 涉及文件 |
|----|------|---------|
| D1 | 移除前端 testConnection 硬编码密码 | `frontend/src/api/device.ts`, `frontend/src/pages/DeviceDetail/BasicInfoTab.tsx D1 | 后端 Schema `user`/`password` 改为可选字段 | `backend/app/schemas/device.py` |
| D1 | （可选）Agent 新增 `/nvme/<device>/get-feature` 端点 | `agent/agent_server.py` |
| D2 | （可选）Agent 新增 `/nvme/<device>/fw-log` 端点 | `agent/agent_server.py` |
| D2 | （可选）AgentExecutor 新增 `get_nvme_feature()` 和 `get_nvme_fw_log()` | `backend/app/executors/agent_executor.py` |
| D3 | 回归测试：完整链路验证 | 全部 |
| D4 | Bug 修复 + 边界情况处理 | 全部 |
| D5 | 文档收尾 + V1 Demo 准备 | 文档 |

### Week 4: 集成测试 + Demo 准备

| 日 | 任务 | 涉及文件 |
|----|------|---------|
| D1 | 更新 `verify_integration.py` 覆盖新功能 | `backend/verify_integration.py` |
| D2 | E2E 测试：创建设备 → 心跳识别 → 创建 FIO 任务 → AI 报告 | 全链路 |
| D3 | Dashboard 数据准确性验证（与 DB 直查对比） | 前后端 |
| D4 | 性能验证：10 台 Agent 同时在线，Dashboard 5s 刷新无卡顿 | 全链路 |
| D5 | V1 Demo 录制 + 文档收尾 | 文档 |

---

## 九、文件变更清单

### 后端新增文件

| 文件路径 | 说明 |
|---------|------|
| `backend/app/api/dashboard.py` | Dashboard API 路由 |
| `backend/app/services/dashboard_service.py` | Dashboard 聚合业务逻辑 |

### 后端修改文件

| 文件路径 | 变更内容 |
|---------|---------|
| `backend/app/models/device.py` | 新增 hostname/os_version/kernel_version/cpu_usage/memory_usage 字段 + `to_dict()` 始终包含 `disks` 键 |
| `backend/app/executors/agent_executor.py` | 不新增 `get_host_info()`（复用 `get_health()`）；可选新增 `get_nvme_feature()`, `get_nvme_fw_log()` 方法 |
| `backend/app/services/device_status_checker.py` | 探测 Agent 时直接调用 `get_health()`（去掉重复 `test_connection`）；仅在线时写主机信息，离线清空 cpu/mem |
| `backend/app/services/device_service.py` | `get_agent_status` 扩展：在线时提取 hostname_version/cpu_usage/memory_usage 写入 Device |
| `backend/app/api/__init__.py` | 注册 dashboard 路由 |
| `backend/app/schemas/device.py` | `DeviceTestConnectionRequest.user`/`password` 改为可选字段（`default=None`） |
| `backend/init_mysql.sql` | 新增 5 条 `add_column_if_missing` 调用添加 Device 表主机信息字段 |
| `backend/verify_integration.py` | 新增 Dashboard API 和主机信息测试 |

### Agent 修改文件

| 文件路径 | 变更内容 |
|---------|---------|
| `agent/agent_server.py` | `/health` 端点扩展返回主机信息（含 try/except 保护）；可选新增 `/nvme/<device>/get-feature` 和 `/nvme/<device>/fw-log` 端点 |

### 前端新增文件

| 文件路径 | 说明 |
|---------|------|
| `frontend/src/api/dashboard.ts` | Dashboard API 模块 |
| `frontend/src/hooks/useDashboard.ts` | Dashboard React Query hook |

### 前端修改文件

| 文件路径 | 变更内容 |
|---------|---------|
| `frontend/src/pages/Dashboard/index.tsx` | 全面改造：真实数据 + CPU/MEM 卡片 + 双折线图（含空状态） + 5s 刷新 |
| `frontend/src/pages/DeviceManage/index.tsx` | 新增 hostname/os/kernel/cpu/memory 列，新增 refetchInterval: 30000 |
| `frontend/src/pages/DeviceDetail/BasicInfoTab.tsx` | 展示主机信息（见 6.7.1）+ 移除硬编码密码 |
| `frontend/src/types/device.ts` | Device 类型新增主机信息字段 |
| `frontend/src/api/device.ts` | 删除 `testConnection` 中的 `password || '123456'` 默认值逻辑 |
| `frontend/src/api/index.ts` | 导出 dashboardApi |
| `frontend/src/hooks/useNvme.ts` | `useNvmeDetail` type 参数增加 `'smart-log'`，`queryFnMap` 增加 `smart-log` 映射 |
| `frontend/src/pages/DeviceDetail/NvmeListTab.tsx` | modal 类型联合与 `useNvmeDetail` 对齐 |

### 前端删除文件

| 文件路径 | 原因 |
|---------|------|
| `frontend/src/hooks/useWebSocket.ts` | V1 不使用 WebSocket |
| `frontend/src/stores/taskStore.ts` | 无任何消费方，直接删除 |

---

## 十、测试验收标准

| # | 验收项 | 标准 |
|---|--------|------|
| 1 | Agent `/health` 扩展 | 返回 hostname/os/kernel/cpu_usage/memory_usage；collector 异常时返回空默认值，不返回 500 |
| 2 | Server Agent 状态探测 | 30s 内新 Agent 上线后 Device 表所有字段更新；离线时 hostname/os/kernel 不被清空 |
| 3 | 新增设备即时探测 | 调用 `create_device` 后立即获取主机信息，无需等 30s |
| 4 | Dashboard 聚合 API | 一次请求返回 agents/tasks/recent_tasks，avg_cpu/avg_memory 有值；bw_mib 为 MiB/s，lat_mean_us 为微秒 |
| 5 | Dashboard 自动刷新 | 5s 内页面数据刷新，无明显闪烁 |
| 6 | Dashboard 图表 | IOPS/Latency 折线图显示真实任务数据（任务级趋势），非硬编码；无 finished_at 的任务不出现在图表 |
| 7 | DeviceManage 主机信息 | 表格展示 hostname/os/kernel/cpu/mem，离线 Agent 静态信息保留、CPU/MEM 显示 `--` |
| 8 | NvmeListTab SMART-LOG | 点击 SMART-LOG 按钮 modal 正常加载数据，不再因 type 未映射而静默失败 |
| 9 | AI 报告 | 已是中文（无需改动），验证输出格式不变 |
| 10 | 安全 | 前端 `device.ts` 无默认密码逻辑，`BasicInfoTab.tsx` 测试连接不硬编码凭据；后端 Schema user/password 为可选 |
| 11 | 端到端 | 创建设备 → 即时识别主机信息 → 创建 FIO 任务 → 执行完成 → AI 报告生成 → Dashboard 展示 |

---

## 十一、不在 V1 范围内的内容

以下功能明确推迟到后续版本：

| 功能 | 版本 | 原因 |
|------|------|------|
| 基线管理 | V2 | 需要独立 baseline 表 + CRUD |
| 回归测试 | V2 | 依赖基线管理 |
| 多盘并发 | V2 | 需要 group_task 表 + Celery chord |
| SNIA 标准测试 | V2 | 复杂任务链 + 稳态判定 |
| 固件升级验证 | V2 | 向导式流程 + 前后对比 |
| NVMe 协议校验规则引擎 | V2.5 | 需要可配置 Pass/Fail 引擎 |
| Long Run / Power Cycle / Hot Plug | V3 | 稳定性测试 |
| AI 回归/根因分析 | V4 | 依赖 V2/V3 数据积累 |
| RBAC / 多租户 | 不做 | 规划明确排除 |
| WebSocket 实时推送 | 不做 | V1 用轮询足够 |
