# SSD Engine 产品规划（优化版）

## 1. 项目目标

**项目定位：** SSD Engine 是一个面向 NVMe SSD 的自动化验证平台（SSD Validation Platform），重点解决 SSD 性能验证、协议验证、稳定性验证、回归验证，而非传统监控平台。

**6~12个月目标：** 完成 SSD 测试平台 + NVMe 协议验证 + 固件升级验证 + 企业级稳定性验证，达到 SSD 测试开发岗位项目要求。

---

## 2. 技术架构

| 层级 | 技术栈 |
|------|--------|
| 前端 | React, TypeScript, Ant Design, React Query, ECharts |
| 后端 | Flask, SQLAlchemy, MySQL, Redis, Celery |
| Agent | Python, fio, nvme-cli, smartctl, iostat |
| AI能力 | OpenAI Compatible API, DeepSeek, Qwen |

---

## 3. 版本规划

| 版本 | 周期 | 目标 |
|------|------|------|
| V1 | 第1~4周 | 基础测试平台（Agent管理 + FIO测试 + Dashboard + AI报告） |
| V2 | 第5~10周 | 性能验证体系（基线 + 回归 + 多盘 + SNIA + FW升级） |
| V2.5 | 第11~16周 | NVMe协议验证（Identify / SMART / Error Log / Feature） |
| V3 | 第17~22周 | 企业级稳定性验证（Long Run / Data Verify / Power Cycle） |
| V4 | 持续演进 | AI分析平台（回归分析 + 根因分析） |

总周期：6~8个月

---

## 3. 设计原则

### 原则：NVMe 磁盘监控 — 整盘级 I/O 指标，分区级空间指标

Linux 内核 `/proc/diskstats` 中分区条目缺失时间统计字段（字段12-14：进行中 I/O 数、I/O 耗时、加权 I/O 耗时），分区级别的延迟（await）、利用率（%util）、队列深度等指标**无法正确计算**。这是内核的设计选择，不是可绕过的 bug。

**规则：**
- I/O 性能指标（IOPS / 带宽 / 延迟 / 利用率 / 队列深度）→ **整盘级采集**（如 `nvme0n1`）
- 空间使用率指标 → **分区（文件系统）级采集**（如 `nvme0n1p2 → /data`）
- NVMe 分区名必须归一化为整盘名后入库，采集、存储、查询端到端一致

**Why:** 业内主流监控工具（iostat、node_exporter、Telegraf、Netdata）均遵循此设计。在分区级采集 I/O 指标会导致延迟/利用率恒为 0，数据无意义且与整盘指标重复。

**How to apply:** 所有涉及磁盘 I/O 监控的模块，`disk_name` 字段一律使用整盘名（通过 `_base_disk_name()` / `_normalize_disk_name()` 归一化）。`list_disks()` 返回的磁盘列表需对 NVMe 分区去重，同一整盘只出现一次。

---

# V1 基础测试平台（第1~4周）

目标：形成完整可运行产品，端到端跑通一次 FIO 测试并生成 AI 报告。

---

## 功能1 Agent 管理

### 目标
集中管理所有测试机器，实时掌握在线/离线状态。

### 数据模型

```sql
CREATE TABLE agent (
  id            INT PRIMARY KEY AUTO_INCREMENT,
  hostname      VARCHAR(64)  NOT NULL,
  ip            VARCHAR(32)  NOT NULL,
  os_version    VARCHAR(128),
  kernel_version VARCHAR(128),
  cpu_usage     FLOAT,
  memory_usage  FLOAT,
  status        ENUM('online','offline') DEFAULT 'offline',
  last_heartbeat DATETIME,
  created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 接口设计

```
POST /api/agent/heartbeat     # Agent 上报心跳
GET  /api/agent/list          # 前端拉取 Agent 列表
GET  /api/agent/<id>          # 查询单个 Agent 详情
```

心跳请求体：
```json
{
  "hostname": "test01",
  "ip": "192.168.1.10",
  "cpu": 12.5,
  "memory": 45.3
}
```

### 后端逻辑

1. 收到心跳 → upsert `agent` 表（`hostname` 唯一）→ 更新 `last_heartbeat = NOW()`、`status = online`
2. Celery Beat 每分钟扫描：`last_heartbeat < NOW() - 60s` → 置 `status = offline`
3. Agent 列表接口返回全部字段，前端按 status 着色（绿色 online / 红色 offline）

### 开发步骤

1. **Week 1 Day 1** — 建表，编写 `POST /api/agent/heartbeat` 接口，单元测试通过
2. **Week 1 Day 2** — 编写 Agent 侧心跳脚本（`agent_daemon.py`，每30秒 POST 一次）
3. **Week 1 Day 3** — Celery Beat 任务：扫描超时 Agent 置 offline
4. **Week 1 Day 4** — 前端 Agent 列表页（React Query 10秒轮询，表格展示 hostname / ip / status / last_heartbeat）
5. **Week 1 Day 5** — 联调：启动 Agent 脚本 → 页面变 online；停止脚本 → 60秒后变 offline

---

## 功能2 FIO 测试

### 目标
通过前端配置参数 → 下发到 Agent 执行 → 采集结果，完成一次完整性能测试闭环。

### 数据模型

```sql
CREATE TABLE task (
  id          INT PRIMARY KEY AUTO_INCREMENT,
  agent_id    INT NOT NULL,
  name        VARCHAR(128),
  fio_config  JSON NOT NULL,       -- 前端传入的配置
  status      ENUM('pending','running','done','failed') DEFAULT 'pending',
  result      JSON,                -- fio 解析后的结果
  created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
  finished_at DATETIME
);
```

### 接口设计

```
POST /api/task/create          # 创建任务
GET  /api/task/list            # 任务列表
GET  /api/task/<id>            # 任务详情 + 结果
POST /api/task/<id>/result     # Agent 上传结果
```

前端配置示例：
```json
{
  "agent_id": 1,
  "name": "4K RandRead Baseline",
  "fio_config": {
    "rw": "randread",
    "bs": "4k",
    "iodepth": 32,
    "runtime": 300,
    "numjobs": 1,
    "filename": "/dev/nvme0n1"
  }
}
```

### FIO Job 文件生成

Server 根据 `fio_config` 渲染模板：

```ini
[global]
ioengine=libaio
direct=1
rw={{ rw }}
bs={{ bs }}
iodepth={{ iodepth }}
runtime={{ runtime }}
numjobs={{ numjobs }}
time_based=1

[job1]
filename={{ filename }}
```

### Agent 执行流程

```
1. 轮询 GET /api/task/poll?agent_id=1  →  取得 pending 任务
2. 将 fio_config 写入 /tmp/fio_<task_id>.job
3. 执行：fio /tmp/fio_<task_id>.job --output-format=json > /tmp/fio_<task_id>.json
4. 解析 JSON，提取 iops / bw / lat_ns
5. POST /api/task/<id>/result 上传结果
```

结果上传体：
```json
{
  "iops": 850000,
  "bw_kbps": 3276800,
  "lat_ns_mean": 150000,
  "lat_ns_p99": 380000,
  "raw_json": "<fio 原始输出>"
}
```

### 开发步骤

1. **Week 2 Day 1** — 建 `task` 表，实现 `POST /api/task/create`（写库，状态 pending）
2. **Week 2 Day 2** — FIO 模板渲染器（Jinja2），单测：给定 config → 生成正确 job 文件
3. **Week 2 Day 3** — `task/poll` 接口 + Agent 执行脚本（调用 fio，解析 JSON）
4. **Week 2 Day 4** — `task/<id>/result` 接口（写库，状态 done）
5. **Week 2 Day 5** — 前端：任务创建表单 + 任务列表页（展示状态、IOPS、带宽、延迟）
6. **Week 3 Day 1** — 联调：点击「提交」→ Agent 执行 → 结果回显到前端

---

## 功能3 Dashboard

### 目标
一屏总览：所有 Agent 资源状态 + 最近任务结果趋势。

### 数据来源

| 卡片 | 数据来源 |
|------|---------|
| Agent 在线数 | `agent` 表 status=online count |
| CPU / MEM 平均 | `agent` 表最新 heartbeat |
| 最近任务 IOPS | `task` 表最近10条 result |
| 最近任务延迟 | `task` 表最近10条 result |

### 接口设计

```
GET /api/dashboard/summary    # 返回上述所有数据，一次请求
```

返回结构：
```json
{
  "agents": { "total": 5, "online": 4 },
  "avg_cpu": 23.5,
  "avg_memory": 41.2,
  "recent_tasks": [
    { "id": 12, "name": "4K RandRead", "iops": 850000, "lat_ns": 150000, "created_at": "..." }
  ]
}
```

### 前端实现

- React Query `useQuery`，`refetchInterval: 5000`（5秒轮询）
- ECharts 折线图：X轴 = 任务时间，Y轴 = IOPS / Latency
- Ant Design `Statistic` 卡片展示 CPU / MEM / 在线数

### 开发步骤

1. **Week 3 Day 2** — 实现 `GET /api/dashboard/summary` 聚合接口
2. **Week 3 Day 3** — 前端 Statistic 卡片布局（Agent在线数 / 平均CPU / 平均MEM）
3. **Week 3 Day 4** — ECharts 趋势图：最近10次任务的 IOPS + Latency 双折线
4. **Week 3 Day 5** — 样式打磨 + 5秒自动刷新验证

---

## 功能4 AI 报告

### 目标
测试完成后，一键调用 AI 生成自然语言测试结论，避免手写报告。

### 接口设计

```
POST /api/task/<id>/ai_report    # 触发生成，异步写库
GET  /api/task/<id>/ai_report    # 前端轮询获取结果
```

### Prompt 模板

```
你是一名 SSD 性能测试工程师。请根据以下测试结果生成专业的测试结论（200字以内，中文）。

测试配置：
- 读写模式：{rw}
- 块大小：{bs}
- 队列深度：{iodepth}
- 测试时长：{runtime}秒

测试结果：
- IOPS：{iops}
- 带宽：{bw} MB/s
- 平均延迟：{lat_ms} ms
- P99 延迟：{lat_p99_ms} ms

请判断：性能是否正常？是否存在异常？给出简要结论。
```

### 数据模型（扩展 task 表）

```sql
ALTER TABLE task ADD COLUMN ai_report TEXT;
ALTER TABLE task ADD COLUMN ai_status ENUM('none','generating','done','failed') DEFAULT 'none';
```

### 开发步骤

1. **Week 4 Day 1** — 封装 AI 调用模块（`ai_client.py`），支持 OpenAI Compatible API，可切换 DeepSeek / Qwen
2. **Week 4 Day 2** — `POST /api/task/<id>/ai_report`：读取任务结果 → 渲染 Prompt → 调用 AI → 写库
3. **Week 4 Day 3** — 前端：任务详情页增加「生成AI报告」按钮 + 报告展示区（轮询 ai_status）
4. **Week 4 Day 4** — 异常处理：AI 超时 / 调用失败时给出 fallback 提示
5. **Week 4 Day 5** — V1 整体联调 + Demo 录制

---

# V2 性能验证体系（第5~10周）

目标：形成完整的 SSD 性能验证闭环，支持基线管理、回归检测、多盘并发、SNIA 标准测试和固件升级验证。

---

## 功能1 基线管理

### 目标
保存「标准状态」下的测试结果，作为后续回归比对的参照物。

### 数据模型

```sql
CREATE TABLE baseline (
  id           INT PRIMARY KEY AUTO_INCREMENT,
  name         VARCHAR(128) NOT NULL,
  device_model VARCHAR(128),
  firmware     VARCHAR(64),
  fio_config   JSON NOT NULL,
  result       JSON NOT NULL,   -- iops / bw / lat_ns 等
  created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
  created_by   VARCHAR(64)
);
```

### 接口设计

```
POST /api/baseline/create           # 从已完成的 task 创建 baseline
GET  /api/baseline/list             # 基线列表
GET  /api/baseline/<id>             # 基线详情
DELETE /api/baseline/<id>           # 删除基线
```

创建请求体：
```json
{
  "task_id": 12,
  "name": "NVMe-A100 初始基线",
  "device_model": "Samsung 980 Pro",
  "firmware": "5B2QGXA7"
}
```

### 开发步骤

1. **Week 5 Day 1** — 建 `baseline` 表，实现 CRUD 接口
2. **Week 5 Day 2** — 前端：任务详情页增加「设为 Baseline」按钮，点击后弹出填写 device_model / firmware 的表单
3. **Week 5 Day 3** — 基线列表页（表格：名称 / 型号 / 固件 / IOPS / 创建时间）

---

## 功能2 回归测试

### 目标
运行新测试后，自动与 Baseline 对比，量化性能变化，标记 WARNING / FAIL。

### 算法

```python
def calc_diff(baseline_val, current_val):
    diff_pct = (current_val - baseline_val) / baseline_val * 100
    if diff_pct < -10:
        return "FAIL", diff_pct
    elif diff_pct < -5:
        return "WARNING", diff_pct
    else:
        return "PASS", diff_pct
```

判定规则：

| 指标 | WARNING | FAIL |
|------|---------|------|
| IOPS 下降 | >5% | >10% |
| 带宽下降 | >5% | >10% |
| 平均延迟上升 | >10% | >20% |
| P99 延迟上升 | >15% | >30% |

### 数据模型

```sql
CREATE TABLE regression_result (
  id           INT PRIMARY KEY AUTO_INCREMENT,
  task_id      INT NOT NULL,
  baseline_id  INT NOT NULL,
  iops_diff    FLOAT,
  bw_diff      FLOAT,
  lat_diff     FLOAT,
  p99_diff     FLOAT,
  verdict      ENUM('PASS','WARNING','FAIL'),
  detail       JSON,
  created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 接口设计

```
POST /api/regression/run      # 选定 task + baseline → 计算 diff，写库
GET  /api/regression/<id>     # 查看某次回归结果
GET  /api/regression/list     # 历史回归列表
```

### 前端展示

三列对比表：

| 指标 | Baseline | Current | Diff |
|------|---------|---------|------|
| IOPS | 850,000 | 780,000 | -8.2% ⚠️ |
| 带宽 (MB/s) | 3,200 | 3,050 | -4.7% ✅ |
| 平均延迟 (ms) | 0.18 | 0.21 | +16.7% ❌ |

### 开发步骤

1. **Week 5 Day 4** — 实现 `POST /api/regression/run`（diff 计算逻辑 + 写 `regression_result`）
2. **Week 5 Day 5** — 单元测试：覆盖 PASS / WARNING / FAIL 各阈值边界
3. **Week 6 Day 1** — 前端回归结果页（三列对比表，按 verdict 着色）
4. **Week 6 Day 2** — 历史回归列表页 + 趋势图（ECharts：X轴=时间，Y轴=IOPS Diff%）

---

## 功能3 多盘并发测试

### 目标
模拟企业多盘场景，同时向多个 Agent 下发任务，汇总统计结果。

### 实现方案

```
前端选择多个 Agent + fio 配置
      ↓
Server 创建一个 group_task（父任务）
      ↓
Celery 为每个 Agent 创建一个子 task
      ↓
各 Agent 并行执行
      ↓
所有子任务完成 → 聚合 Max / Min / Avg → 更新 group_task
```

### 数据模型

```sql
CREATE TABLE group_task (
  id          INT PRIMARY KEY AUTO_INCREMENT,
  name        VARCHAR(128),
  fio_config  JSON,
  status      ENUM('pending','running','done','failed') DEFAULT 'pending',
  summary     JSON,   -- { "iops_max": ..., "iops_min": ..., "iops_avg": ... }
  created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE task ADD COLUMN group_task_id INT;
```

### Celery 任务

```python
@app.task
def run_group_task(group_task_id):
    tasks = Task.query.filter_by(group_task_id=group_task_id).all()
    job = group([run_single_task.s(t.id) for t in tasks])
    chord(job)(aggregate_group_result.s(group_task_id))

@app.task
def aggregate_group_result(results, group_task_id):
    iops_list = [r['iops'] for r in results]
    summary = {
        "iops_max": max(iops_list),
        "iops_min": min(iops_list),
        "iops_avg": sum(iops_list) / len(iops_list)
    }
    GroupTask.query.get(group_task_id).update(summary=summary, status='done')
```

### 开发步骤

1. **Week 6 Day 3** — 建 `group_task` 表，实现创建接口（自动拆分子任务）
2. **Week 6 Day 4** — Celery chord 调度逻辑 + 聚合函数
3. **Week 6 Day 5** — 前端：多盘测试配置页（多选 Agent）+ 汇总结果展示（Max/Min/Avg 卡片）

---

## 功能4 SNIA 标准测试

### 目标
支持 SNIA PTS 标准测试流程，输出行业认可的 Steady State 测试报告。

### 测试流程

```
1. Precondition（预处理）
   └── 全盘顺序写 2遍，清除初始化效果
2. IOPS Test（IOPS 扫描）
   └── 128K/32K/16K/8K/4K/0.5K × RandWrite/RandRead/SeqWrite/SeqRead
3. Steady State（稳态判定）
   └── 4K RandWrite，连续执行25轮（每轮60秒）
   └── 收集每轮 IOPS，计算最近5轮波动率
   └── 波动率 < 10% → Steady State Achieved
```

### 稳态判定算法

```python
def is_steady_state(iops_history: list, window=5, threshold=0.1):
    if len(iops_history) < window:
        return False
    recent = iops_history[-window:]
    avg = sum(recent) / window
    max_dev = max(abs(v - avg) / avg for v in recent)
    return max_dev < threshold
```

### 配置文件（`snia_sss.json`）

```json
{
  "precondition": {
    "rw": "write", "bs": "128k", "iodepth": 32, "loops": 2
  },
  "iops_test": {
    "block_sizes": ["128k","32k","16k","8k","4k","512"],
    "patterns": ["randwrite","randread","write","read"],
    "iodepth": 32, "runtime": 60
  },
  "steady_state": {
    "rw": "randwrite", "bs": "4k", "iodepth": 32,
    "rounds": 25, "runtime": 60,
    "window": 5, "threshold": 0.10
  }
}
```

### 数据模型

```sql
CREATE TABLE snia_task (
  id           INT PRIMARY KEY AUTO_INCREMENT,
  agent_id     INT,
  status       ENUM('pending','preconditioning','iops_test','steady_state','done','failed'),
  current_round INT DEFAULT 0,
  iops_history JSON,
  is_steady    BOOLEAN DEFAULT FALSE,
  result       JSON,
  created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 开发步骤

1. **Week 7 Day 1** — 建 `snia_task` 表，实现启动接口
2. **Week 7 Day 2** — Celery 任务链（`precondition → iops_test → steady_state`），每阶段结束更新 status
3. **Week 7 Day 3** — 稳态判定算法实现 + 单元测试
4. **Week 7 Day 4** — 前端：进度展示（当前阶段 + 当前轮次 + 实时 IOPS 折线图）
5. **Week 7 Day 5** — 稳态收敛可视化（ECharts 标注稳态窗口）+ 测试报告导出（JSON）

---

## 功能5 固件升级验证

### 目标
量化固件升级前后的性能差异，给出明确的升级影响报告。

### 流程

```
1. 选定 Agent + 配置测试参数
2. 采集升级前 Baseline（自动运行一次 FIO）
3. 提示用户手动升级固件（或调用 nvme fw-download + fw-activate）
4. 运行同参数 FIO → 记录升级后结果
5. 调用回归计算逻辑 → 生成对比报告
```

### 数据模型

```sql
CREATE TABLE fw_upgrade_test (
  id              INT PRIMARY KEY AUTO_INCREMENT,
  agent_id        INT,
  device          VARCHAR(64),
  fw_before       VARCHAR(64),
  fw_after        VARCHAR(64),
  fio_config      JSON,
  result_before   JSON,
  result_after    JSON,
  regression_id   INT,           -- 关联 regression_result
  status          ENUM('collecting_baseline','waiting_upgrade','testing_after','done'),
  created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 接口设计

```
POST /api/fw_test/start          # 启动，开始采集升级前基线
POST /api/fw_test/<id>/upgraded  # 用户确认固件已升级，触发升级后测试
GET  /api/fw_test/<id>/report    # 获取对比报告
```

### 前端展示

| 指标 | 升级前 | 升级后 | 变化 |
|------|-------|-------|------|
| 固件版本 | 5B2QGXA7 | 5B2QGXA9 | — |
| IOPS | 850,000 | 870,000 | +2.4% ✅ |
| 带宽 (MB/s) | 3,200 | 3,280 | +2.5% ✅ |
| 平均延迟 (ms) | 0.18 | 0.17 | -5.6% ✅ |

### 开发步骤

1. **Week 8 Day 1** — 建 `fw_upgrade_test` 表，实现 `start` 接口（自动触发 FIO 采集基线）
2. **Week 8 Day 2** — `upgraded` 接口（触发升级后测试 → 完成后调用回归计算）
3. **Week 8 Day 3** — 前端向导式页面（Step 1 采集基线 → Step 2 提示升级 → Step 3 查看报告）
4. **Week 8 Day 4** — 报告页面（对比表 + AI 自动生成升级建议）
5. **Week 8 Day 5** — 联调 + 端到端测试

---

# V2.5 NVMe 协议验证（第11~16周）

目标：系统性验证 NVMe 协议合规性，输出结构化 Pass/Fail 报告。

### 通用设计约定

所有协议验证功能共用以下数据模型：

```sql
CREATE TABLE nvme_test (
  id          INT PRIMARY KEY AUTO_INCREMENT,
  agent_id    INT,
  device      VARCHAR(64),     -- 如 /dev/nvme0
  test_type   VARCHAR(64),     -- identify / namespace / smart / error_log / feature / fw_slot
  status      ENUM('pending','running','done','failed'),
  result      JSON,            -- 各字段校验结果列表
  verdict     ENUM('PASS','PARTIAL','FAIL'),
  created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

每个校验项的 result 格式：
```json
[
  { "field": "VID",  "value": "0x144D", "check": "非空且格式为0x+4位十六进制", "pass": true },
  { "field": "SN",   "value": "S4EWNX0T123456", "check": "长度<=20且无特殊字符", "pass": true },
  { "field": "FR",   "value": "", "check": "非空", "pass": false, "reason": "固件版本为空" }
]
```

---

## 功能1 Identify 验证

**Agent 命令：** `nvme id-ctrl /dev/nvme0 -o json`

**验证字段及规则：**

| 字段 | 说明 | 校验规则 |
|------|------|---------|
| vid | 厂商ID | 非0、格式 0x+4位十六进制 |
| ssvid | 子系统厂商ID | 非0 |
| sn | 序列号 | 非空、长度 ≤20、无特殊字符 |
| mn | 型号 | 非空、长度 ≤40 |
| fr | 固件版本 | 非空、长度 ≤8 |
| mdts | 最大数据传输大小 | >0 |
| nn | 命名空间数量 | ≥1 |

**开发步骤：**
1. Agent 侧：封装 `nvme_identify(device)` 函数，执行命令 + 解析 JSON
2. Server 侧：校验规则引擎（可配置，后续功能复用）
3. 前端：验证结果表格（字段 / 值 / 规则 / 通过/失败，红色高亮失败项）

---

## 功能2 Namespace 验证

**Agent 命令：** `nvme id-ns /dev/nvme0n1 -o json`

**验证字段及规则：**

| 字段 | 说明 | 校验规则 |
|------|------|---------|
| nsze | Namespace 总大小（LBA数量） | >0 |
| ncap | Namespace 容量 | >0 且 ≤ nsze |
| nuse | 已用空间 | ≥0 且 ≤ ncap |
| lbafs | LBA 格式列表 | 至少有一个 in use 的格式 |
| flbas | 当前 LBA 格式索引 | 在 lbafs 范围内 |

**开发步骤：**
1. Agent 侧：封装 `nvme_id_ns(device, ns_id)`
2. Server 侧：添加 namespace 校验规则
3. 前端：在 nvme_test 结果页新增 namespace tab

---

## 功能3 SMART 验证

**Agent 命令：** `nvme smart-log /dev/nvme0 -o json`

**验证字段及规则：**

| 字段 | 说明 | 校验规则 | 异常阈值 |
|------|------|---------|---------|
| temperature | 温度（Kelvin） | 转摄氏度：K-273 | >70°C → WARNING |
| media_errors | 媒体错误计数 | 整数 | >0 → WARNING |
| num_err_log_entries | 错误日志条数 | 整数 | >0 → 记录 |
| unsafe_shutdowns | 非安全关机次数 | 整数 | 记录，不判fail |
| percentage_used | 寿命使用百分比 | 0~100 | >80% → WARNING |
| power_on_hours | 上电时间 | ≥0 | — |
| critical_warning | 关键告警字段 | 0 = 无告警 | ≠0 → FAIL |

**开发步骤：**
1. Agent 侧：封装 `nvme_smart_log(device)`，转换 temperature 单位
2. Server 侧：添加 SMART 校验规则（含阈值判定）
3. 前端：SMART 状态卡片 + 温度/寿命进度条可视化

---

## 功能4 Error Log 验证

**验证目标：** 确认设备在触发错误后，error log 条目数量正确增加。

**Agent 执行流程：**
```
1. 读取当前 error log 条数（基准值）
   命令：nvme error-log /dev/nvme0 -o json

2. 主动触发一次无效命令（产生错误）
   方法：向不存在的 namespace 发送读请求
   命令：nvme read /dev/nvme0 -n 99 -c 1 -z 512

3. 再次读取 error log
   预期：条目数 = 基准值 + 1

4. 上报：{ before: N, after: M, increased: M > N }
```

**校验逻辑：**
```python
def verify_error_log(before_count, after_count):
    if after_count > before_count:
        return "PASS", f"错误日志正确增加：{before_count} → {after_count}"
    else:
        return "FAIL", f"错误日志未增加，可能 error log 功能异常"
```

**开发步骤：**
1. Agent 侧：实现三步流程（读基准 → 触发错误 → 验证增加）
2. Server 侧：存储 before/after/result
3. 前端：展示对比（触发前条数 / 触发后条数 / 是否符合预期）

---

## 功能5 Feature 验证

**验证目标：** 确认 Write Cache / Power State / APST 功能可读取且值合法。

**Agent 命令：**
```bash
nvme get-feature /dev/nvme0 -f 0x06  # Write Cache
nvme get-feature /dev/nvme0 -f 0x02  # Power Management
nvme get-feature /dev/nvme0 -f 0x0c  # APST
```

**校验规则：**

| Feature | FID | 校验内容 |
|---------|-----|---------|
| Write Cache | 0x06 | 命令执行成功，value 为 0 或 1 |
| Power Management | 0x02 | 命令执行成功，power state 在合法范围 |
| APST | 0x0c | 命令执行成功，返回 APST 状态表 |

**开发步骤：**
1. Agent 侧：封装 `nvme_get_feature(device, fid)`，解析返回值
2. Server 侧：添加 feature 校验规则
3. 前端：Feature 验证结果表格

---

## 功能6 Firmware Slot 验证

**验证目标：** 确认固件槽信息正确，验证 fw-log 字段合规。

**Agent 命令：** `nvme fw-log /dev/nvme0 -o json`

**验证字段：**

| 字段 | 校验规则 |
|------|---------|
| afi.active | 当前激活槽号 (1~7) |
| frs | 各槽固件版本，至少 slot1 非空 |
| frsn | 固件版本字符串格式合法 |

**开发步骤：**
1. Agent 侧：封装 `nvme_fw_log(device)`
2. Server 侧：校验 afi 和 frs 字段
3. 前端：固件槽可视化（7个槽，标注 active / 已安装 / 空）

---

# V3 企业级稳定性验证（第17~22周）

目标：模拟企业生产环境，验证 SSD 在极端条件下的可靠性。

---

## 功能1 Long Run（72小时压力测试）

### 目标
持续72小时施压，检测性能衰退、SMART 异常、设备崩溃等问题。

### 实现方案

```
Celery 定时任务（每5分钟）：
  1. 运行一轮 fio（4K RandWrite, 5分钟）
  2. 采集 SMART（temperature, media_errors, percentage_used）
  3. 写入 long_run_sample 表
  4. 检查异常（温度>70°C / 媒体错误增加）→ 记录告警
  5. 到达 72h → 生成最终报告
```

### 数据模型

```sql
CREATE TABLE long_run_task (
  id         INT PRIMARY KEY AUTO_INCREMENT,
  agent_id   INT,
  device     VARCHAR(64),
  status     ENUM('running','done','failed','aborted'),
  start_time DATETIME,
  end_time   DATETIME,
  duration_h INT DEFAULT 72
);

CREATE TABLE long_run_sample (
  id           INT PRIMARY KEY AUTO_INCREMENT,
  task_id      INT,
  sample_time  DATETIME,
  iops         FLOAT,
  bw_kbps      FLOAT,
  lat_ns_mean  FLOAT,
  temperature  FLOAT,
  media_errors INT,
  pct_used     INT
);
```

### 异常判定

```python
ALERT_RULES = [
    {"field": "temperature", "op": ">", "value": 70, "level": "WARNING"},
    {"field": "media_errors", "op": "increased", "level": "FAIL"},
    {"field": "iops", "op": "drop_pct", "threshold": 20, "level": "WARNING"},
]
```

### 开发步骤

1. **Week 17** — 建表，实现 Celery 周期采样任务（5分钟一次）
2. **Week 18** — 异常检测逻辑 + 告警记录
3. **Week 19** — 前端：实时趋势图（ECharts 时序图：IOPS / 温度 / 媒体错误）
4. **Week 20 Day 1** — 报告生成：72小时汇总（平均IOPS / 最高温度 / 异常次数 / 总结）

---

## 功能2 Data Verify（静默数据损坏检测）

### 目标
通过 fio 的数据校验模式，检测 SSD 是否存在静默数据损坏（Silent Data Corruption）。

### fio 配置

```ini
[global]
ioengine=libaio
direct=1
rw=randrw
bs=4k
iodepth=32
runtime=3600
verify=md5
verify_fatal=1
verify_dump=1

[job1]
filename=/dev/nvme0n1
```

关键参数说明：
- `verify=md5`：写入时计算 MD5，读回时校验
- `verify_fatal=1`：发现校验失败立即中止
- `verify_dump=1`：将损坏数据 dump 到文件

### 结果解析

```python
def parse_verify_result(fio_json):
    errors = fio_json["jobs"][0].get("error", 0)
    verify_errors = fio_json["jobs"][0].get("verify_errors", 0)
    return {
        "passed": verify_errors == 0,
        "verify_errors": verify_errors,
        "io_errors": errors
    }
```

### 开发步骤

1. **Week 20 Day 2** — 实现 verify 模式 fio 模板，Agent 执行 + 解析 verify_errors
2. **Week 20 Day 3** — 前端：测试配置页（可选时长）+ 结果展示（PASS / FAIL + 错误详情）

---

## 功能3 Power Cycle 验证

### 目标
验证 SSD 在断电/重启后，数据完整性和设备可恢复性。

### 第一阶段：软件模拟（`reboot`）

```
流程：
1. 向 SSD 写入测试数据（fio with verify=md5，先只写不读）
2. 记录写入的 LBA 范围和校验值
3. 执行 reboot（SSH 重启，等待 Agent 恢复心跳）
4. 重启后：读取相同 LBA，校验数据一致性
5. 重新扫描设备是否可识别（nvme list）
```

### 数据模型

```sql
CREATE TABLE power_cycle_test (
  id           INT PRIMARY KEY AUTO_INCREMENT,
  agent_id     INT,
  device       VARCHAR(64),
  cycle_count  INT DEFAULT 0,
  method       ENUM('reboot','pdu'),
  status       ENUM('writing','cycling','verifying','done','failed'),
  data_ok      BOOLEAN,
  device_ok    BOOLEAN,
  result       JSON,
  created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 开发步骤

1. **Week 20 Day 4** — 实现写数据 → 触发 reboot → 等待 Agent 上线（最长5分钟超时）
2. **Week 20 Day 5** — 上线后自动触发数据校验 + 设备恢复检查
3. **Week 21 Day 1** — 前端：Power Cycle 状态时间线（写数据 → 断电 → 恢复 → 校验）

---

## 功能4 Hot Plug 验证

### 目标
验证 SSD 热插拔后的设备恢复能力（V3 阶段以手工 + 记录为主）。

### 第一阶段：手工热插拔

```
流程：
1. 前端创建 Hot Plug 测试记录
2. 提示用户执行热拔出操作
3. 用户点击「已拔出」→ Server 验证设备是否消失（nvme list）
4. 提示用户执行热插入操作
5. 用户点击「已插入」→ Server 验证设备恢复（nvme list 重新出现）
6. 运行 Identify + SMART 确认设备状态正常
```

### 验证项

| 验证项 | 命令 | 预期 |
|--------|------|------|
| 设备恢复 | `nvme list` | 设备重新出现 |
| Namespace 完整 | `nvme id-ns` | NSZE / NCAP 不变 |
| SMART 正常 | `nvme smart-log` | 无新增媒体错误 |
| 数据一致性 | fio verify | 无数据损坏 |

### 开发步骤

1. **Week 21 Day 2~3** — 实现手工 Hot Plug 流程（向导式 + 状态确认）
2. **Week 21 Day 4** — 验证逻辑（自动调用 nvme list / id-ns / smart-log）
3. **Week 21 Day 5** — 前端：Hot Plug 测试向导 + 结果报告

---

## 功能5 Mixed Workload 验证

### 目标
模拟真实业务场景（MySQL / Ceph / VM），评估 SSD 在混合负载下的综合表现。

### 预置 fio 模板

```python
WORKLOAD_TEMPLATES = {
    "mysql_oltp": {
        "description": "MySQL OLTP 场景：70%读/30%写，4K随机",
        "rw": "randrw", "rwmixread": 70, "bs": "4k", "iodepth": 64, "numjobs": 4
    },
    "ceph_osd": {
        "description": "Ceph OSD 场景：顺序写为主，4M大块",
        "rw": "write", "bs": "4m", "iodepth": 128, "numjobs": 8
    },
    "vm_storage": {
        "description": "虚拟机存储场景：混合读写，8K块",
        "rw": "randrw", "rwmixread": 50, "bs": "8k", "iodepth": 32, "numjobs": 4
    },
    "olap_query": {
        "description": "OLAP 查询场景：顺序读，1M大块",
        "rw": "read", "bs": "1m", "iodepth": 32, "numjobs": 2
    }
}
```

### 开发步骤

1. **Week 22 Day 1** — 实现模板管理（预置4种 + 允许自定义）
2. **Week 22 Day 2** — 前端：Workload 选择页 + 运行结果展示
3. **Week 22 Day 3** — 多模板批量运行（依次执行，生成对比报告）

---

# V4 AI 分析平台（持续演进）

目标：基于历史测试数据，提供智能化分析能力，形成差异化竞争力。

---

## 功能1 AI 回归分析

**输入：** Baseline 结果 + Current 结果 + 设备信息 + 固件版本

**Prompt 核心内容：**
```
以下是 SSD 回归测试结果。请分析性能下降的可能原因，并给出排查建议。

设备：{device_model}，固件：{fw_before} → {fw_after}
IOPS 变化：{iops_before} → {iops_after}（{iops_diff}%）
延迟变化：{lat_before}ms → {lat_after}ms（{lat_diff}%）
SMART 变化：媒体错误 {media_errors_before} → {media_errors_after}

请从以下角度分析：1.固件变更影响 2.设备老化 3.测试环境变化 4.其他可能原因
```

**实现步骤：**
1. 封装回归分析 Prompt 模板（参数化）
2. 支持多轮回归历史作为上下文输入
3. 前端在回归报告页增加「AI 分析」按钮

---

## 功能2 AI 根因分析

**输入：** SMART 日志 + Error Log + FIO 结果 + Long Run 趋势

**Prompt 核心内容：**
```
以下是 SSD 设备的诊断数据，请分析可能的故障原因。

SMART 数据：
- 温度：{temperature}°C
- 媒体错误：{media_errors}
- 非安全关机：{unsafe_shutdowns}
- 寿命使用：{percentage_used}%
- critical_warning：{critical_warning}

错误日志：{error_log_summary}

性能数据：最近 IOPS 趋势 {iops_trend}

请给出：1.最可能的故障原因 2.紧急程度（低/中/高）3.建议的排查步骤
```

**实现步骤：**
1. 数据聚合层：将 SMART + error_log + long_run 数据汇总为结构化输入
2. 封装根因分析 Prompt
3. 前端：设备诊断页（一键触发 + 结果展示）

---

# 4. 不做清单

以下功能暂不开发（对 SSD 测试岗位求职价值极低）：

复杂 RBAC、WebSocket、钉钉/邮件告警、健康评分、热力图、寿命预测、多租户、微服务

---

# 5. 简历项目描述

**SSD Engine** — AI-Native SSD Validation Platform

**技术栈：** Flask + React + MySQL + Redis + Celery

**核心能力：**
- FIO 自动化测试 / SNIA 标准测试（含稳态自动收敛判断）
- 基线管理 / 自动回归分析（IOPS/带宽/延迟多维 Diff，阈值告警）
- NVMe 协议验证（Identify / Namespace / SMART / Error Log / Feature / FW Slot）
- 固件升级验证（升级前后自动 Diff 报告）
- Long Run 稳定性测试（72小时 / 5分钟周期采样）/ Data Verify 静默错误检测
- AI 根因分析（SMART + Error Log + FIO 多维输入）

支持多 Agent 分布式执行，实现 SSD 性能验证、协议验证和稳定性验证全流程自动化。
