# SSD Engine V2 需求详设文档

> 版本：v2.0 | 日期：2026-06-16 | 分支：feature_v2

---

## 0. 架构边界与设计原则

### 0.1 不可变层（平台层 + 契约层）

以下由 V1 已验证且被全局依赖，V2 不可变更：

| 维度 | 现有方案 | 边界理由 |
|------|---------|---------|
| 任务调度 | APScheduler + threading | 被所有定时任务依赖，引入 Celery 需新增 Redis + 重构调度层 |
| Agent 通信 | Agent-Push（数据）+ Server-Push（命令） | 全系统通信方向已固化，改造需重写 Agent 端 |
| 设备标识 | Device.id + device_ip | 全局外键依赖，改标识方案需全表迁移 |
| FIO 执行 | FioRunner._build_command() | 端唯一执行路径，改模板渲染需重部署 Agent |
| 延迟单位 | 微秒（us） | 前后端 + DB 全链路约定，改单位需全量数据修正 |
| 前端选型 | React + Ant Design + React Query + Zustand | 被全部页面依赖，换框架代价等于重写前端 |
| API 风格 | Blueprint `api_bp`，prefix `/api`，JSON | 被全部前端调用方依赖，改风格需重写 API 层 |

### 0.2 可变层（接口层 + 实现层）

V2 各模块内部的**设计理念和模式**可以自由选择，只要不违反 0.1 的不可变约束：

| 层级 | 定义 | 改动爆炸半径 | V2 策略 |
|------|------|-------------|---------|
| 实现层 | 模块内部逻辑（编排方式、算法、状态流转） | 仅影响该模块自身 | **大胆尝试新理念** |
| 接口层 | 同模块内 Service 间调用方式 | 影响调用侧 Service | 可调整，改调用方即可 |
| 契约层 | API 路径 + 请求/响应 schema、DB 表结构 | 影响跨模块消费者 | 保守确认后再定 |
| 平台层 | 技术选型、通信方向、全局约定 | 影响全系统 | 不可变 |

**依赖方向规则**：只能从上层指向下层（实现→接口→契约→平台），不能反向。

**正例**（允许）：
- SNIA 用状态机代替线性 thread → 仅改 SniaService 内部（实现层）
- 回归比对拆为独立 RuleEngine class → 仅改 RegressionService 内部（实现层）
- 多盘并发用事件订阅代替侵入式回调 → 改协作接口（接口层），仅影响 GroupTaskService

**反例**（禁止）：
- IngestService 反向调用 GroupTaskService → 实现层反向依赖接口层
- Agent 新增 WebSocket 通道 → 实现层反向依赖平台层
- 改 Device 表主键类型 → 契约层改动影响全系统外键

### 0.3 新方案走不通的兜底策略

V2 五个模块均为**新增模块**，有独立表、独立 Service、独立路由、独立前端页面，互不干扰。

| 走不通的场景 | 兜底方式 | 恢复周期 |
|-------------|---------|---------|
| 模块内新设计走不通（如状态机太复杂） | 退回原方案，重写该 Service 内部，其他模块不受影响 | 1-2 天 模块间协作模式走不通（如多盘聚合回调太耦合） | 改协作接口，受影响方仅调用侧 Service | 1-2 天 |
| 契约层走不通（如 detail JSON schema 设计失误） | 改表 + 迁移数据，需清测试数据重建，受影响方仅该模块 | 2-3 天 |
| 整个模块方向错误 | 删除该模块全部代码（表/Service/路由/页面），V1 及其他 V2 模块不受影响 | 0 天（删除即恢复） |

**核心安全网**：最坏情况是删掉该V1 已有功能和其他 V2 模块零影响。

**实操建议**：在实现层大胆尝试新理念，在契约层保守确认，在平台层不动。

---

## 1. 基线管理

### 1.1 需求拆分

| 编号 | 最小需求 | 优先级 |
|------|---------|--------|
| BL-1 | 创建基线（从已完成 Task 创建） | P0 |
| BL-2 | 基线列表查询 | P0 |
| BL-3 | 基线详情查询 | P0 |
| BL-4 | 基线删除 | P0 |
| BL-5 | 前端 Task 详情页「设为基线」操作入口 | P0 |
| BL-6 | 前端基线管理独立页面 | P0 |

### 1.2 BL-1：创建基线

#### 使用场景

用户在 Task 详情页或任务列表页，选定一个 `status=SUCCESS` 的任务，点击「设为基线」，填写设备型号和固件版本，系统自动从该任务的 config + result 创建一条基线记录。基线作为后续回归比对的参照物。

#### 后端设计

**数据模型**

```sql
CREATE TABLE baseline (
  id           INT PRIMARY KEY AUTO_INCREMENT,
  name         VARCHAR(128) NOT NULL,
  device_model VARCHAR(128),
  firmware     VARCHAR(64),
  fio_config   JSON NOT NULL,          -- 来源 task.config
  result       JSON NOT NULL,          -- 来源 task.result（含 iops/bw/latency）
  source_task_id INT NOT NULL,         -- 来源任务ID，便于溯源
  device_ip    VARCHAR(50) NOT NULL,   -- 来源任务 device_ip
  device_path  VARCHAR(255) NOT NULL,  -- 来源任务 device_path
  created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
  created_by   VARCHAR(64) DEFAULT 'system'
);
```

**API**

```
POST /api/baselines
```

请求体：
```json
{
  "task_id": 12,
  "name": "NVMe-A100 初始基线",
  "device_model": "Samsung 980 Pro",
  "firmware": "5B2QGXA7"
}
```

响应体（201）：
```json
{
  "id": 1,
  "name": "NVMe-A100 初始基线",
  "device_model": "Samsung 980 Pro",
  "firmware": "5B2QGXA7",
  "fio_config": { "rw": "randread", "bs": "4k", "iodepth": 32, "runtime": 300 },
  "result": {
    "iops": 850000, "bandwidth": 3276,
    "latency": { "mean": 150, "min": 80, "max": 1200 }
  },
  "source_task_id": 12,
  "device_ip": "192.168.1.10",
  "device_path": "/dev/nvme0n1",
  "created_at": "2026-06-16T10:00:00+08:00",
  "created_by": "system"
}
```

**后端逻辑步骤**

1. 校验 task_id 对应的 Task 存在且 status == SUCCESS
2. 读取 task.config / task.result / task.device_ip / task.device_path
3. 构建 Baseline 记录并写入 DB
4. 返回新建的 baseline 对象

**伪代码**

```python
class BaselineService:
    @staticmethod
    def create(data: dict) -> Baseline:
        task = Task.query.get(data['task_id'])
        if not task or task.status != TaskStatus.SUCCESS:
            raise ApiError('VALIDATION_ERROR', '只能从成功任务创建基线', 400)
        baseline = Baseline(
            name=data['name'],
            device_model=data.get('device_model'),
            firmware=data.get('firmware'),
            fio_config=task.config,
            result=task.result,
            source_task_id=task.id,
            device_ip=task.device_ip,
            device_path=task.device_path,
        )
        db.session.add(baseline)
        db.session.commit()
        return baseline
```

#### 前端设计

在 `TaskDetail` 页面结果卡片区域，添加 Ant Design `Button`：「设为基线」。点击弹出 `Modal`，表单字段：名称（必填）、设备型号（选填）、固件版本（选填），确认后调用 `POST /api/baselines`。

#### 联调校验

- 前端提交 `task_id`（int）→ 后端 `BaselineService.create(data)` 接收 `dict` 含 `task_id` 键
- 后端返回的 `fio_config` / `result` 结构与 Task.to_dict() 中的 config / result 一致（JSON）
- 前端通过 `task_id` 回溯到 `TaskDetail` 页的链接：`/tasks/${baseline.source_task_id}`

---

### 1.3 BL-2：基线列表查询

#### 使用场景

用户打开基线管理页面，查看所有已创建的基线，按创建时间倒序，支持按名称搜索和设备型号筛选。

#### 后端设计

**API**

```
GET /api/baselines?keyword=NVMe&device_model=Samsung&page=1&page_size=10
```

响应体：
```json
{
  "items": [
    {
      "id": 1, "name": "NVMe-A100 初始基线",
      "device_model": "Samsung 980 Pro", "firmware": "5B2QGXA7",
      "result": { "iops": 850000, "bandwidth": 3276, "latency": { "mean": 150 } },
      "device_ip": "192.168.1.10", "source_task_id": 12,
      "created_at": "2026-06-16T10:00:00+08:00"
    }
  ],
  "total": 3
}
```

**伪代码**

```python
class BaselineService:
    @staticmethod
    def list(keyword=None, device_model=None, page=1, page_size=10) -> dict:
        query = Baseline.query
        if keyword:
            query = query.filter(Baseline.name.like(f'%{keyword}%'))
        if device_model:
            query = query.filter_by(device_model=device_model)
        pagination = query.order_by(Baseline.created_at.desc()).paginate(page=page, per_page=page_size)
        return {'items': [b.to_dict() for b in pagination.items], 'total': pagination.total}
```

#### 前端设计

新增 `BaselineList` 页面（路由 `/baselines`），Ant Design `Table` 列：名称、设备型号、固件版本、IOPS、带宽(MB/s)、平均延迟(us)、来源任务ID、创建时间、操作（查看/删除）。

---

### 1.4 BL-3：基线详情查询

**API**: `GET /api/baselines/<int:id>`

响应体同 BL-1 返回结构，含完整 `fio_config` 和 `result`。

前端：在 `BaselineList` 点击「查看」跳转 `BaselineDetail` 页面，展示完整配置和结果详情。

### 1.5 BL-4：基线删除

**API**: `DELETE /api/baselines/<int:id>`

返回 204 无 body。校验无正在进行的回归测试引用此基线（若有关联 `regression_result` 且状态非 done/failed，则拒绝删除，返回 409）。

### 1.6 BL-5 & BL-6：前端页面

已在 BL-1 和 BL-2 中描述。路由配置：

```typescript
// App.tsx 新增
<Route path="/baselines" element={<BaselineList />} />
<Route path="/baselines/:id" element={<BaselineDetail />} />
```

侧边栏新增菜单项「基线管理」，key `/baselines`。

---

## 2. 回归测试

### 2.1 需求拆分

| 编号 | 最小需求 | 优先级 |
|------|---------|--------|
| RG-1 | 执行回归比对（选定 Task + Baseline → 计算 diff） | P0 |
| RG-2 | 阈值判定（PASS / WARNING / FAIL） | P0 |
| RG-3 | 回归结果详情查询 | P0 |
| RG-4 | 回归历史列表 | P0 |
| RG-5 | 前端三列对比表 | P0 |
| RG-6 | 前端历史回归趋势图 | P1 |

### 2.2 RG-1：执行回归比对

#### 使用场景

用户选择一个已完成的 Task 和一条 Baseline（fio_config 的 rw/bs/iodepth 须匹配），系统计算各项指标的百分比差异，写入回归结果表。

#### 后端设计

**数据模型**

```sql
CREATE TABLE regression_result (
  id           INT PRIMARY KEY AUTO_INCREMENT,
  task_id      INT NOT NULL,
  baseline_id  INT NOT NULL,
  iops_diff    FLOAT,           -- 百分比，如 -8.2 表示下降8.2%
  bw_diff      FLOAT,
  lat_mean_diff FLOAT,
  lat_p99_diff FLOAT,
  verdict      VARCHAR(10) NOT NULL,  -- PASS / WARNING / FAIL
  detail       JSON,            -- 完整的逐指标对比明细
  created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

detail 字段结构：
```json
{
  "metrics": [
    {
      "name": "iops", "unit": "",
      "baseline": 850000, "current": 780000,
      "diff_pct": -8.24, "verdict": "WARNING"
    },
    {
      "name": "bandwidth", "unit": "MB/s",
      "baseline": 3276, "current": 3126,
      "diff_pct": -4.60, "verdict": "PASS"
    },
    {
      "name": "lat_mean", "unit": "us",
      "baseline": 150, "current": 175,
      "diff_pct": 16.67, "verdict": "FAIL"
    }
  ]
}
```

**API**

```
POST /api/regressions
```

请求体：
```json
{
  "task_id": 15,
  "baseline_id": 1
}
```

响应体（201）：
```json
{
  "id": 1,
  "task_id": 15,
  "baseline_id": 1,
  "iops_diff": -8.24,
  "bw_diff": -4.60,
  "lat_mean_diff": 16.67,
  "lat_p99_diff": null,
  "verdict": "FAIL",
  "detail": { "metrics": [...] },
  "created_at": "2026-06-16T11:00:00+08:00"
}
```

**后端逻辑步骤**

1. 校验 Task 存在且 status=SUCCESS
2. 校验 Baseline 存在
3. 校验 fio_config 中 rw / bs / iodevice 匹配（宽松匹配，仅校验 rw 和 bs）
4. 逐一计算 diff 百分比
5. 应用阈值规则取最严 verdict
6. 写入 regression_result 表

**伪代码**

```python
THRESHOLD_TABLE = {
    'iops':    {'warning': -5,  'fail': -10},    # 下降百分比
    'bw':      {'warning': -5,  'fail': -10},
    'lat_mean': {'warning': 10, 'fail': 20},     # 上升百分比
    'lat_p99':  {'warning': 15, 'fail': 30},
}

def calc_diff_pct(baseline_val, current_val, metric_name):
    if metric_name.startswith('lat'):
        return (current_val - baseline_val) / baseline_val * 100if baseline_val else 0
    return (current_val - baseline_val) / baseline_val * 100 if baseline_val else 0

def judge_metric(diff_pct, metric_name):
    thresholds = THRESHOLD_TABLE[metric_name]
    if metric_name.startswith('lat'):
        if diff_pct > thresholds['fail']: return 'FAIL'
        if diff_pct > thresholds['warning']: return 'WARNING'
        return 'PASS'
    else:
        if diff_pct < thresholds['fail']: return 'FAIL'
        if diff_pct < thresholds['warning']: return 'WARNING'
        return 'PASS'

class RegressionService:
    @staticmethod
    def run(data: dict) -> RegressionResult:
        task = Task.query.get(data['task_id'])
        baseline = Baseline.query.get(data['baseline_id'])
        if not task or task.status != TaskStatus.SUCCESS:
            raise ApiError('VALIDATION_ERROR', '任务未完成，无法回归', 400)
        if not baseline:
            raise ApiError('NOT_FOUND', '基线不存在', 404)

        # 提取结果指标
        cur_result = task.result or {}
        base_result = baseline.result or {}

        metrics_spec = [
            ('iops',     base_result.get('iops'),     cur_result.get('iops')),
            ('bw',       base_result.get('bandwidth'), cur_result.get('bandwidth')),
            ('lat_mean', base_result.get('latency', {}).get('mean'),
                         cur_result.get('latency', {}).get('mean')),
            ('lat_p99',  base_result.get('latency', {}).get('p99'),
                         cur_result.get('latency', {}).get('p99')),
        ]

        detail_metrics = []
        worst_verdict = 'PASS'
        for name, base_val, cur_val in metrics_spec:
            if base_val is None or cur_val is None:
                continue
            diff_pct = round(calc_diff_pct(base_val, cur_val, name), 2)
            v = judge_metric(diff_pct, name)
            if v == 'FAIL': worst_verdict = 'FAIL'
            elif v == 'WARNING' and worst_verdict != 'FAIL': worst_verdict = 'WARNING'
            detail_metrics.append({
                'name': name, 'baseline': base_val, 'current': cur_val,
                'diff_pct': diff_pct, 'verdict': v,
                'unit': 'us' if 'lat' in name else ('MB/s' if name == 'bw' else '')
            })

        result = RegressionResult(
            task_id=task.id, baseline_id=baseline.id,
            iops_diff=next((m['diff_pct'] for m in detail_metrics if m['name']=='iops'), None),
            bw_diff=next((m['diff_pct'] for m in detail_metrics if m['name']=='bw'), None),
            lat_mean_diff=next((m['diff_pct'] for m in detail_metrics if m['name']=='lat_mean'), None),
            lat_p99_diff=next((m['diff_pct'] for m in detail_metrics if m['name']=='lat_p99'), None),
            verdict=worst_verdict,
            detail={'metrics': detail_metrics},
        )
        db.session.add(result)
        db.session.commit()
        return result
```

#### 前端设计

在 Task 详情页结果区域添加「回归比对」按钮，点击弹出 Modal：选择基线（下拉列表 `GET /api/baselines`），确认后调用 `POST /api/regressions`，成功后跳转至回归结果页。

#### 联调校验

- 请求体 `task_id` / `baseline_id` 均为 int → 后端直接以 int 做 `query.get()`
- 返回的 `detail.metrics[].baseline` / `current` 数值类型与 Task.result / Baseline.result 中的 iops / bandwidth / latency.mean 一致（均为 float/int）
- `lat_p99`：当前 Task.result 中缺失此字段（仅存在于 FioTrendData），需在 BL-1 创建基线时从 trend 数据取最后一个点的 lat_p99 存入 baseline.result；或在 regression 计算时若 p99 缺失则跳过该指标

**p99 缺失问题方案选择**

| 方案 | 优点 | 缺点 |
|------|------|------|
| A: Task.result 增加 lat_p99 字段 | 一劳永逸，后续功能均可使用 | 需改动 Agent FioRunner._parse_result() |
| B: 回归时从 FioTrendData 取最后一点的 lat_p99 | 不改动 Agent | 数据可能不精确（trend 点是中间值） |

**最佳实践：方案 A** — 修改 Agent 端 `_parse_result()` 在最终结果中增加 `lat_p99` 和 `raw_json` 字段，使 Task.result 结构完整。这是最小改动且后续 SNIA、固件升级均需用 p99。

---

### 2.3 RG-2：阈值判定

已在 RG-1 伪代码中实现。判定规则表：

| 指标 | WARNING | FAIL | 方向 |
|------|---------|------|------|
| IOPS | 下降 >5% | 下降 >10% | 越高越好 |
| 带宽 | 下降 >5% | 下降 >10% | 越高越好 |
| 平均延迟 | 上升 >10% | 上升 >20% | 越低越好 |
| P99 延迟 | 上升 >15% | 上升 >30% | 越低越好 |

总体 verdict 取所有指标中最严重的一个：FAIL > WARNING > PASS。

### 2.4 RG-3 & RG-4：回归查询

**API**

```
GET /api/regressions/<int:id>       → 单条回归结果详情
GET /api/regressions?page=1&page_size=10&verdict=FAIL  → 回归历史列表
```

列表响应体：
```json
{
  "items": [
    {
    "id": 1, "task_id": 15, "baseline_id": 1,
      "verdict": "FAIL", "iops_diff": -8.24,
      "created_at": "2026-06-16T11:00:00+08:00"
    }
  ],
  "total": 5
}
```

### 2.5 RG-5：前端三列对比表

在回归详情页展示 Ant Design `Table`，列定义：

| 列名 | 数据路径 | 渲染 |
|------|---------|------|
| 指标 | `detail.metrics[].name` | 中文名映射 |
| 基线值 | `detail.metrics[].baseline` | 数值 + 单位 |
| 当前值 | `detail.metrics[].current` | 数值 + 单位 |
| 差异 | `detail.metrics[].diff_pct` | 百分比 + Tag(PASS绿/WARNING黄/FAIL红) |

### 2.6 RG-6：历史回归趋势图

ECharts 折线图：X 轴 = 创建时间，Y 轴 = IOPS Diff% / Latency Diff%，数据源 `GET /api/regressions` 按 baseline_id 分组。

---

## 3. 多盘并发测试

### 3.1 需求拆分

| 编号 | 最小需求 | 优先级 |
|------|---------|--------|
| GT-1 | 创建组任务（选择多 Agent + 统一 FIO 配置） | P0 |
| GT-2 | 自动拆分子任务并并行下发至各 Agent | P0 |
| GT-3 | 子任务完成自动聚合（Max/Min/Avg） | P0 |
| GT-4 | 组任务状态管理 | P0 |
| GT-5 | 前端多盘配置页 | P0 |
| GT-6 | 前端汇总结果展示（Max/Min/Avg 卡片） | P0 |
| GT-7 | 各子任务详情钻取 | P1 |

### 3.2 GT-1 & GT-2 & GT-3：组任务完整流程

#### 使用场景

用户需要同时向 3 台测试机的 NVMe SSD 下发相同的 FIO 负载，模拟企业多盘场景。前端选择多台设备和统一 FIO 配置 → Server 创建一个 GroupTask 父任务 → 自动为每台设备创建子 Task → 各 Agent 并行执行 → 所有子任务完成后自动聚合 Max/Min/Avg → 更新 GroupTask 状态为 done。

#### 后端设计

**数据模型**

```sql
CREATE TABLE group_task (
  id          INT PRIMARY KEY AUTO_INCREMENT,
  name        VARCHAR(128) NOT NULL,
  fio_config  JSON NOT NULL,
  status      VARCHAR(20) DEFAULT 'pending',   -- pending/running/done/failed/partial
  summary     JSON,          -- { "iops_max":..., "iops_min":..., "iops_avg":..., ... }
  total_count INT DEFAULT 0,       -- 子任务总数
  done_count  INT DEFAULT 0,       -- 已完成子任务数
  created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Task 表扩展字段
ALTER TABLE tasks ADD COLUMN group_task_id INT NULL;
ALTER TABLE tasks ADD COLUMN is_sub_task BOOLEAN DEFAULT FALSE;
```

**API**

```
POST /api/group-tasks                 → 创建组任务
GET  /api/group-tasks                  → 组任务列表
GET  /api/group-tasks/<int:id>         → 组任务详情（含子任务列表 + summary）
DELETE /api/group-tasks/<int:id>       → 删除组任务及其子任务
```

创建请求体：
```json
{
  "name": "3盘 4K RandRead 并发测试",
  "device_ids": [1, 2, 3],
  "fio_config": {
    "rw": "randread", "bs": "4k", "iodepth": 32, "runtime": 300
  }
}
```

创建响应体（202）：
```json
{
  "id": 1,
  "name": "3盘 4K RandRead 并发测试",
  "fio_config": { "rw": "randread", "bs": "4k", "iodepth": 32, "runtime": 300 },
  "status": "pending",
  "total_count": 3,
  "done_count": 0,
  "summary": null,
  "sub_tasks": [
    { "id": 101, "device_ip": "192.168.1.10", "device_path": "/dev/nvme0n1", "status": "PENDING" },
    { "id": 102, "device_ip": "192.168.1.11", "device_path": "/dev/nvme0n1", "status": "PENDING" },
    { "id": 103, "device_ip": "192.168.1.12", "device_path": "/dev/nvme0n1", "status": "PENDING" }
  ],
  "created_at": "2026-06-16T12:00:00+08:00"
}
```

**后端逻辑步骤**

1. 校验所有 device_ids 对应 Device 存在且 agent_status=online
2. 创建 GroupTask 记录
3. 遍历每个 device_id，创建子 Task（设置 group_task_id, is_sub_task=True），同时通过 AgentExecutor.fio_start() 下发到各 Agent
4. 每个子任务启动成功后，更新 GroupTask.status = running
5. 子任务完成时（通过 IngestService.flush_task 回调），检查同组所有子任务状态，若全部完成则聚合 summary 并更新 GroupTask.status

**并行下发伪代码**

```python
class GroupTaskService:
    @staticmethod
    def create(data: dict) -> GroupTask:
        device_ids = data['device_ids']
        devices = Device.query.filter(Device.id.in_(device_ids)).all()
        if len(devices) != len(device_ids):
            raise ApiError('NOT_FOUND', '部分设备不存在', 404)
        offline = [d.ip for d in devices if d.agent_status != 'online']
        if offline:
            raise ApiError('VALIDATION_ERROR', f'设备离线: {offline}', 400)

        group = GroupTask(
            name=data['name'],
            fio_config=data['fio_config'],
            total_count=len(devices),
        )
        db.session.add(group)
        db.session.flush()

        config = FioConfigValidator.apply_defaults(data['fio_config'])
        for device in devices:
            task = Task(
                name=f"{data['name']} - {device.ip}",
                device_id=device.id,
                device_ip=device.ip,
                device_path=data.get('device_path', '/dev/nvme0n1'),
                config=config,
                fault_type='none',
                group_task_id=group.id,
                is_sub_task=True,
            )
            db.session.add(task)
            db.session.flush()
            # 在独立线程中启动各子任务
            t = threading.Thread(
                target=GroupTaskService._start_sub_task,
                args=(task.id, device.id),
                daemon=True,
            )
            t.start()

        group.status = 'running'
        db.session.commit()
        return group

    @staticmethod
    def _start_sub_task(task_id: int, device_id: int):
        with db.app_context():
            task = Task.query.get(task_id)
            device = Device.query.get(device_id)
            try:
                TaskService._start_task(task, device)
            except Exception:
                task = Task.query.get(task_id)
                task.status = TaskStatus.FAILED
                task.result = {'error': 'Agent 启动失败'}
                db.session.commit()

    @staticmethod
    def try_aggregate(group_task_id: int):
        """由 IngestService.flush_task 在子任务完成时调用"""
        group = GroupTask.query.get(group_task_id)
        sub_tasks = Task.query.filter_by(group_task_id=group_task_id).all()
        done_count = sum(1 for t in sub_tasks if t.status in {TaskStatus.SUCCESS, TaskStatus.FAILED})
        group.done_count = done_count

        if done_count < group.total_count:
            db.session.commit()
            return

        success_tasks = [t for t in sub_tasks if t.status == TaskStatus.SUCCESS]
        if not success_tasks:
            group.status = 'failed'
            db.session.commit()
            return

        iops_list = [t.result['iops'] for t in success_tasks if t.result and 'iops' in t.result]
        bw_list = [t.result['bandwidth'] for t in success_tasks if t.result and 'bandwidth' in t.result]
        lat_list = [t.result['latency']['mean'] for t in success_tasks
                     if t.result and t.result.get('latency', {}).get('mean')]

        group.summary = {
            'iops_max': max(iops_list) if iops_list else None,
            'iops_min': min(iops_list) if iops_list else None,
            'iops_avg': round(sum(iops_list) / len(iops_list), 1) if iops_list else None,
            'bw_max': max(bw_list) if bw_list else None,
            'bw_min': min(bw_list) if bw_list else None,
            'bw_avg': round(sum(bw_list) / len(bw_list), 1) if bw_list else None,
            'lat_mean_max': max(lat_list) if lat_list else None,
            'lat_mean_min': min(lat_list) if lat_list else None,
            'lat_mean_avg': round(sum(lat_list) / len(lat_list), 1) if lat_list else None,
        }
        group.status = 'partial' if len(success_tasks) < group.total_count else 'done'
        db.session.commit()
```

#### 联调校验

- `POST /api/group-tasks` 的 `device_ids` 是 int 数组 → Device.query.filter(Device.id.in_(device_ids))
- 子任务的 `device_path` 来源：前端可传统一值（如 `/dev/nvme0n1`），也可以在创建接口中按每台设备指定（增加 `device_paths` 字典映射 `{device_id: path}`）
- `IngestService.flush_task()` 中需增加调用 `GroupTaskService.try_aggregate(task.group_task_id)` 的逻辑，当 `task.is_sub_task == True` 且 `task.group_task_id` 非空时触发

#### 前端设计

新增 `GroupTaskCreate` 组件（Modal 形式），包含：
- 任务名称 Input
- 设备多选 Checkbox Group（数据源 `GET /api/devices`，仅显示 online）
- FIO 配置：复用 `TaskCreateModal` 的引导式配置组件
- 设备路径统一配置 Input（默认 `/dev/nvme0n1`）

### 3.3 GT-5 & GT-6 & GT-7：前端页面

新增路由：
```typescript
<Route path="/group-tasks" element={<GroupTaskList />} />
<Route path="/group-tasks/:id" element={<GroupTaskDetail />} />
```

`GroupTaskList` 页面：Table 列（名称、状态、子任务进度 done/total、IOPS Avg、创建时间、操作）。

`GroupTaskDetail` 页面：
- Summary 卡片区：IOPS (Max/Min/Avg)、BW (Max/Min/Avg)、Latency Mean (Max/Min/Avg)
- 子任务列表 Table：ID、设备IP、设备路径、状态、IOPS、带宽、平均延迟、操作（查看详情→跳转 `/tasks/:id`）
- 若需回归比对，可从 GroupTask 详情页选择 Baseline 进行批量回归

---

## 4. SNIA 标准测试

### 4.1 需求拆分

| 编号 | 最小需求 | 优先级 |
|------|---------|--------|
| SN-1 | SNIA 任务创建与启动 | P0 |
| SN-2 | Precondition 预处理阶段 | P0 |
| SN-3 | IOPS Test 扫描阶段 | P0 |
| SN-4 | Steady State 稳态判定阶段 | P0 |
| SN-5 | 稳态判定算法 | P0 |
| SN-6 | 前端进度展示（阶段 + 轮次 + 实时 IOPS） | P0 |
| SN-7 | 稳态收敛可视化 | P1 |
| SN-8 | SNIA 报告导出（JSON） | P1 |

### 4.2 SN-1 ~ SN-5：SNIA 任务完整流程

#### 使用场景

用户选择一台 Agent + NVMe 设备，选择 SNIA 测试模板（预置配置），系统自动按 SNIA PTS 规范执行预处理 → IOPS 扫描 → 稳态判定三阶段流程，全程可观测。

#### 后端设计

**数据模型**

```sql
CREATE TABLE snia_task (
  id           INT PRIMARY KEY AUTO_INCREMENT,
  name         VARCHAR(128) NOT NULL,
  device_id    INT NOT NULL,
  device_ip    VARCHAR(50) NOT NULL,
  device_path  VARCHAR(255) NOT NULL,
  status       VARCHAR(20) DEFAULT 'pending',
    -- pending / preconditioning / iops_test / steady_state / done / failed / aborted
  current_phase VARCHAR(20) DEFAULT NULL,       -- precondition / iops_test / steady_state
  current_round INT DEFAULT 0,
  total_rounds  INT DEFAULT 25,
  iops_history  JSON,          -- 每轮 IOPS 值列表
  is_steady     BOOLEAN DEFAULT FALSE,
  config        JSON NOT NULL, -- SNIA 配置
  result        JSON,          -- 最终汇总结果
  error         TEXT,
  created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at    DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

config 字段默认值：
```json
{
  "precondition": { "rw": "write", "bs": "128k", "iodepth": 32, "loops": 2 },
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

**API**

```
POST /api/snia-tasks              → 创建并启动 SNIA 任务
GET  /api/snia-tasks               → SNIA 任务列表
GET  /api/snia-tasks/<int:id>      → SNIA 任务详情（含 iops_history、当前阶段等）
POST /api/snia-tasks/<int:id>/abort → 终止 SNIA 任务
GET  /api/snia-tasks/<int:id>/report → 导出 JSON 报告
```

创建请求体：
```json
{
  "name": "SNIA SSS 4K RandWrite",
  "device_id": 1,
  "device_path": "/dev/nvme0n1",
  "config": { ... }
}
```

**后端逻辑步骤（三阶段流水线）**

SNIA 任务在 Server 端以独立 daemon thread 驱动，按阶段顺序执行：

1. **创建阶段**：写入 snia_task 记录，status=pending
2. **启动流水线线程**：
   ```python
   threading.Thread(target=SniaService._run_pipeline, args=(snia_task_id,), daemon=True).start()
   ```
3. **_run_pipeline**：
   - Phase 1: Precondition — 循环 `config.precondition.loops` 次，下发 FIO 顺序写
   - Phase 2: IOPS Test — 按 `block_sizes × patterns` 组合逐一执行 FIO，记录每组结果
   - Phase 3: Steady State — 循环 `config.steady_state.rounds` 轮，每轮执行 FIO 60s，取 IOPS 存入 iops_history，每轮结束调用 is_steady_state() 判断
4. 每个子步骤通过 AgentExecutor.fio_start() → Agent 主动上报 trend → flush_task 回调
5. 每个阶段切换和每轮完成时更新 snia_task 记录

**伪代码**

```python
class SniaService:
    @staticmethod
    def create(data: dict) -> SniaTask:
        device = Device.query.get(data['device_id'])
        if not device or device.agent_status != 'online':
            raise ApiError('VALIDATION_ERROR', '设备不在线', 400)
        default_config = SniaService._default_config()
        if 'config' in data:
            default_config.update(data['config'])
        task = SniaTask(
            name=data['name'],
            device_id=device.id,
            device_ip=device.ip,
            device_path=data['device_path'],
            status='pending',
            config=default_config,
            iops_history='[]',
        )
        db.session.add(task)
        db.session.flush()
        threading.Thread(target=SniaService._run_pipeline, args=(task.id,), daemon=True).start()
        db.session.commit()
        return task

    @staticmethod
    def _run_pipeline(snia_task_id: int):
        with db.app_context():
            task = SniaTask.query.get(snia_task_id)
            agent = AgentExecutor(f'http://{task.device_ip}:'
                                  f'{Device.query.get(task.device_id).agent_port}')
            try:
                # Phase 1: Precondition
                task.status = 'preconditioning'
                task.current_phase = 'precondition'
                db.session.commit()
                for loop_i in range(task.config['precondition']['loops']):
                    fio_cfg = {
                        'rw': 'write', 'bs': '128k', 'iodepth': 32,
                        'runtime': 0, 'time_based': False,
                        'loops': 1, 'ioengine': 'libaio', 'direct': True,
                    }
                    with db_released():
                        resp = agent.fio_start(
                            f'snia_pc_{snia_task_id}_{loop_i}',
                            fio_cfg,
                            task.device_path
                        )
                    # 等待子任务完成（轮询 Task 状态）
                    SniaService._wait_sub_task(f'snia_pc_{snia_task_id}_{loop_i}')

                # Phase 2: IOPS Test
                task.status = 'iops_test'
                task.current_phase = 'iops_test'
                db.session.commit()
                iops_results = []
                for bs in task.config['iops_test']['block_sizes']:
                    for pattern in task.config['iops_test']['patterns']:
                        fio_cfg = {
                            'rw': pattern, 'bs': bs,
                            'iodepth': task.config['iops_test']['iodepth'],
                            'runtime': task.config['iops_test']['runtime'],
                            'time_based': True, 'ioengine': 'libaio', 'direct': True,
                        }
                        with db_released():
                            agent.fio_start(f'snia_iops_{snia_task_id}_{bs}_{pattern}',
                                            fio_cfg, task.device_path)
                        result = SniaService._wait_sub_task(
                            f'snia_iops_{snia_task_id}_{bs}_{pattern}')
                        if result:
                            iops_results.append({
                                'bs': bs, 'pattern': pattern,
                                'iops': result.get('iops'),
                                'bw': result.get('bandwidth')
                            })

                # Phase 3: Steady State
                task.status = 'steady_state'
                task.current_phase = 'steady_state'
                task.total_rounds = task.config['steady_state']['rounds']
                db.session.commit()
                iops_list = json.loads(task.iops_history) if task.iops_history else []
                for round_i in range(task.total_rounds):
                    task.current_round = round_i + 1
                    db.session.commit()
                    fio_cfg = {
                        'rw': task.config['steady_state']['rw'],
                        'bs': task.config['steady_state']['bs'],
                        'iodepth': task.config['steady_state']['iodepth'],
                        'runtime': task.config['steady_state']['runtime'],
                        'time_based': True, 'ioengine': 'libaio', 'direct': True,
                    }
                    with db_released():
                        agent.fio_start(f'snia_ss_{snia_task_id}_{round_i}',
                                        fio_cfg, task.device_path)
                    result = SniaService._wait_sub_task(
                        f'snia_ss_{snia_task_id}_{round_i}')
                    if result:
                        iops_list.append(result.get('iops', 0))
                    task.iops_history = json.dumps(iops_list)
                    db.session.commit()

                    if is_steady_state(iops_list,
                                       window=task.config['steady_state']['window'],
                                       threshold=task.config['steady_state']['threshold']):
                        task.is_steady = True
                        break

                # 完成
                task.status = 'done'
                task.result = {
                    'iops_test_results': iops_results,
                    'steady_state_achieved': task.is_steady,
                    'steady_state_round': task.current_round if task.is_steady else None,
                    'iops_history': iops_list
                }
                db.session.commit()

            except Exception as e:
                task = SniaTask.query.get(snia_task_id)
                task.status = 'failed'
                task.error = str(e)
                db.session.commit()

    @staticmethod
    def _wait_sub_task(task_name: str, timeout: int = 7200) -> dict | None:
        """轮询子 Task 状态直至完成，返回 result"""
        start = time.time()
        while time.time() - start < timeout:
            sub = Task.query.filter_by(name=task_name).first()
            if sub and sub.status in {TaskStatus.SUCCESS, TaskStatus.FAILED}:
                return sub.result
            time.sleep(3)
        return None


def is_steady_state(iops_history: list, window: int = 5, threshold: float = 0.1) -> bool:
    if len(iops_history) < window:
        return False
    recent = iops_history[-window:]
    avg = sum(recent) / window
    max_dev = max(abs(v - avg) / avg for v in recent)
    return max_dev < threshold
```

#### Agent 设计

SNIA 任务不需要 Agent 端新增任何代码。SNIA Pipeline 通过 `AgentExecutor.fio_start()` 下发标准 FIO 配置，Agent 按现有流程执行并上报结果。Server 端负责编排多轮 FIO 的执行顺序和状态流转。

#### 联调校验

- `AgentExecutor.fio_start(task_id, config, device)` 的 `task_id` 参数：SNIA 子任务的 task_id 需使用字符串标识（如 `snia_ss_1_5`），但现有 `Task.id` 是自增 int。方案：SNIA Pipeline 创建子 Task 记录后，用 `str(sub_task.id)` 作为 `fio_start` 的 task_id，子 Task 的 name 字段存储语义化名称（如 `snia_ss_1_round5`）
- `fio_start` 返回 `{"success": true/false}` → Pipeline 检查此标志决定是否继续
- `flush_task` 回调时 `IngestService` 中新增：如果 `task.is_sub_task` 且 `task.group_task_id` 非空，不触发聚合（这是 GroupTask 逻辑）；如果 `task.name` 以 `snia_` 开头，触发 SNIA 阶段推进（改为在 `_wait_sub_task` 中轮询检测即可，无需修改 IngestService）

### 4.3 SN-6 & SN-7 & SN-8：前端

新增路由：
```typescript
<Route path="/snia-tasks" element={<SniaTaskList />} />
<Route path="/snia-tasks/:id" element={<SniaTaskDetail />} />
```

`SniaTaskList`：Table 列（名称、设备、状态、当前阶段、当前轮次/总轮次、稳态达成、创建时间、操作）。

`SniaTaskDetail`：
- 阶段进度条：Precondition → IOPS Test → Steady State（Steps 组件，高亮当前阶段）
- 轮次进度：`current_round / total_rounds`
- 实时 IOPS 折线图：ECharts，X 轴 = 轮次，Y 轴 = IOPS，标注稳态窗口
- IOPS Test 结果表：bs × pattern 矩阵，每格显示 IOPS / BW
- 报告导出按钮：调用 `GET /api/snia-tasks/<id>/report`

---

## 5. 固件升级验证

### 5.1 需求拆分

| 编号 | 最小需求 | 优先级 |
|------|---------|--------|
| FW-1 | 固件升级测试创建与基线采集 | P0 |
| FW-2 | 用户确认固件升级完成 | P0 |
| FW-3 | 升级后测试执行 | P0 |
| FW-4 | 自动回归对比 + AI 生成升级建议 | P0 |
| FW-5 | 前端向导式三步流程 | P0 |
| FW-6 | 固件槽可视化 | P1 |

### 5.2 FW-1 ~ FW-4：固件升级验证完整流程

#### 使用场景

用户需要在固件升级前后量化性能差异。启动测试 → 系统自动运行一次 FIO 采集升级前基线 → 提示用户手动升级固件 → 用户确认升级完成 → 系统自动运行同参数 FIO → 调用回归计算逻辑 → 生成对比报告 + AI 建议。

#### 后端设计

**数据模型**

```sql
CREATE TABLE fw_upgrade_test (
  id              INT PRIMARY KEY AUTO_INCREMENT,
  name            VARCHAR(128) NOT NULL,
  device_id       INT NOT NULL,
  device_ip       VARCHAR(50) NOT NULL,
  device_path     VARCHAR(255) NOT NULL,
  fw_before       VARCHAR(64),           -- 升级前固件版本（自动从 Agent 读取）
  fw_after        VARCHAR(64),           -- 升级后固件版本（升级完成后从 Agent 读取）
  fio_config      JSON NOT NULL,
  result_before   JSON,                  -- 升级前 FIO 结果
  task_before_id  INT,                   -- 升级前子任务 ID
 result_after    JSON,                  -- 升级后 FIO 结果
  task_after_id   INT,                   -- 升级后子任务 ID
  regression_id   INT,                   -- 关联 regression_result ID
  status          VARCHAR(20) DEFAULT 'pending',
    -- pending / collecting_baseline / waiting_upgrade /
    -- testing_after / done / failed
  error           TEXT,
  created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

**API**

```
POST /api/fw-tests                        → 创建并启动（开始采集基线）
GET  /api/fw-tests                         → 测试列表
GET  /api/fw-tests/<int:id>                → 测试详情
POST /api/fw-tests/<int:id>/confirm-upgrade → 确认升级完成（触发升级后测试）
POST /api/fw-tests/<int:id>/abort          → 终止测试
GET  /api/fw-tests/<int:id>/report         → 获取对比报告
```

创建请求体：
```json
{
  "name": "Samsung 980 Pro FW升级验证",
  "device_id": 1,
  "device_path": "/dev/nvme0n1",
  "fio_config": {
    "rw": "randread", "bs": "4k", "iodepth": 32, "runtime": 300
  }
}
```

**后端逻辑步骤**

1. 创建 fw_upgrade_test 记录，status=pending
2. 通过 AgentExecutor 获取当前固件版本 `fw_before`
3. 启动基线 FIO 子任务，status=collecting_baseline
4. 子任务完成后，result_before = 子任务.result，task_before_id = 子任务.id
5. 自动从基线结果创建一条 Baseline 记录（复用基线管理模块）
6. status 变为 waiting_upgrade，等待用户确认
7. 用户调用 `confirm-upgrade`，系统读取 `fw_after`，启动升级后 FIO
8. status=testing_after，子任务完成后 result_after = 子任务.result
9. 调用 RegressionService.run() 计算 diff，关联 regression_id
10. 调用 AI 生成升级建议（复用 AnalysisService），写入 report
11. status=done

**伪代码**

```python
class FwUpgradeService:
    @staticmethod
    def create(data: dict) -> FwUpgradeTest:
        device = Device.query.get(data['device_id'])
        if not device or device.agent_status != 'online':
            raise ApiError('VALIDATION_ERROR', '设备不在线', 400)
        fw_test = FwUpgradeTest(
            name=data['name'],
            device_id=device.id,
            device_ip=device.ip,
            device_path=data['device_path'],
            fio_config=FioConfigValidator.apply_defaults(data['fio_config']),
            status='pending',
        )
        db.session.add(fw_test)
        db.session.flush()
        threading.Thread(
            target=FwUpgradeService._collect_baseline,
            args=(fw_test.id, device.id),
            daemon=True,
        ).start()
        db.session.commit()
        return fw_test

    @staticmethod
    def _collect_baseline(fw_test_id: int, device_id: int):
        with db.app_context():
            fw_test = FwUpgradeTest.query.get(fw_test_id)
            device = Device.query.get(device_id)
            agent = AgentExecutor(f'http://{device.ip}:{device.agent_port}')
            try:
                # 读取当前固件版本
                with db_released():
                    fw_info = agent.get_nvme_fw_log(data['device_path'])
                fw_before = _extract_active_fw(fw_info)
                fw_test.fw_before = fw_before
                fw_test.status = 'collecting_baseline'
                db.session.commit()

                # 启动基线 FIO
                config = fw_test.fio_config
                with db_released():
                    resp = agent.fio_start(
                        str(f'fw_baseline_{fw_test_id}'), config, fw_test.device_path)
                if not resp.get('success'):
                    raise Exception('Agent 启动基线 FIO 失败')
                result = FwUpgradeService._wait_sub_task(f'fw_baseline_{fw_test_id}')
                fw_test.result_before = result
                fw_test.status = 'waiting_upgrade'
                db.session.commit()
            except Exception as e:
                fw_test = FwUpgradeTest.query.get(fw_test_id)
                fw_test.status = 'failed'
                fw_test.error = str(e)
                db.session.commit()

    @staticmethod
    def confirm_upgrade(fw_test_id: int) -> FwUpgradeTest:
        fw_test = FwUpgradeTest.query.get(fw_test_id)
        if fw_test.status != 'waiting_upgrade':
            raise ApiError('VALIDATION_ERROR', '当前状态不支持确认升级', 400)
        device = Device.query.get(fw_test.device_id)
        agent = AgentExecutor(f'http://{device.ip}:{device.agent_port}')
        # 读取升级后固件版本
       with db_released():
            fw_info = agent.get_nvme_fw_log(fw_test.device_path)
        fw_test.fw_after = _extract_active_fw(fw_info)

        # 启动升级后 FIO
        fw_test.status = 'testing_after'
        db.session.commit()
        threading.Thread(
            target=FwUpgradeService._run_after_test,
            args=(fw_test_id, device.id),
            daemon=True,
        ).start()
        db.session.commit()
        return fw_test

    @staticmethod
    def _run_after_test(fw_test_id: int, device_id: int):
        with db.app_context():
            fw_test = FwUpgradeTest.query.get(fw_test_id)
            device = Device.query.get(device_id)
            agent = AgentExecutor(f'http://{device.ip}:{device.agent_port}')
            try:
                with db_released():
                    resp = agent.fio_start(
                        f'fw_after_{fw_test_id}', fw_test.fio_config, fw_test.device_path)
                result = FwUpgradeService._wait_sub_task(f'fw_after_{fw_test_id}')
                fw_test.result_after = result

                # 创建基线记录（复用基线管理）
                baseline = BaselineService.create({
                    'task_id': fw_test.task_before_id,
                    'name': f'FW升级前基线 - {fw_test.fw_before}',
                    'device_model': '', 'firmware': fw_test.fw_before,
                })
                # 执行回归比对
                reg = RegressionService.run({
                    'task_id': fw_test.task_after_id,
                    'baseline_id': baseline.id,
                })
                fw_test.regression_id = reg.id

                # AI 生成升级建议（可选）
                fw_test.status = 'done'
                db.session.commit()
            except Exception as e:
                fw_test = FwUpgradeTest.query.get(fw_test_id)
                fw_test.status = 'failed'
                fw_test.error = str(e)
                db.session.commit()

    def _extract_active_fw(fw_log_data: dict) -> str:
        """从 fw-log JSON 中提取当前激活固件版本"""
        afi = fw_log_data.get('afi', {})
        active_slot = afi.get('active', 0)
        if active_slot == 0:
            return ''
        frs = fw_log_data.get('frs', [])
        slot_idx = active_slot - 1  # slot 1 = frs[0]
        if 0 <= slot_idx < len(frs):
            return frs[slot_idx] or ''
        return ''
```

#### 前端设计

新增路由：
```typescript
<Route path="/fw-tests" element={<FwTestList />} />
<Route path="/fw-tests/:id" element={<FwTestDetail />} />
```

`FwTestDetail` 向导式三步流程（Ant Design `Steps`）：
- Step 1: 采集基线（自动运行，状态轮询，完成后展示 IOPS/BW/Latency 结果）
- Step 2: 等待升级（提示「请在目标设备上完成固件升级」，提供确认按钮 `POST /fw-tests/<id>/confirm-upgrade`）
- Step 3: 查看报告（展示三列对比表 + AI 升级建议，数据来自 regression_id → `GET /api/regressions/<id>`）

---

## 6. V2 前置改动（影响所有 V2 功能）

### 6.1 Task.result 增加 lat_p99 字段

**现状**：Task.result 仅含 `{iops, bandwidth, latency: {mean, min, max}}`，lat_p99 仅存在于 FioTrendData 趋势点。

**方案**：修改 Agent 端 `FioRunner._parse_result()` 从 FIO 输出 JSON 中提取 percentile 信息填充到结果中。

Agent 端改动（`fio_runner.py`）：
```python
def _parse_result(self, fio_json: dict) -> dict:
    # ... 现有提取逻辑 ...
    # 新增：从 clat_ns/lat_ns 的 percentile 节点提取 p99
    latency_node = jobs[0].get('read', {}).get('lat_ns', {}) or jobs[0].get('write', {}).get('lat_ns', {})
    if not latency_node:
        latency_node = jobs[0].get('read', {}).get('clat_ns', {}) or jobs[0].get('write', {}).get('clat_ns', {})

    percentiles = latency_node.get('percentile', {})
    lat_p99 = percentiles.get('99.000000', None)

    return {
        'iops': total_iops, 'bandwidth': total_bw,
        'read_iops': ..., 'write_iops': ...,
        'read_bw': ..., 'write_bw': ...,
        'latency': {
            'mean': lat_mean_us, 'min': lat_min_us, 'max': lat_max_us,
            'p99': round(lat_p99 / 1000, 1) if lat_p99 else None,  # ns -> us
        }
    }
```

**联调校验**：前端 `TaskResult` 接口需新增 `p99?: number | null` 字段，现有 `_parse_result` 返回结构向后兼容。

### 6.2 Task.result 增加 raw_json 字段

在 `_parse_result` 返回结构中追加 `'raw_json': json.dumps(fio_json)`，便于 SNIA 报告导出完整 FIO 输出。

### 6.3 Feature / FW Slot API 管道修复

**现状**：AgentExecutor 已有 `get_nvme_feature()` 和 `get_nvme_fw_log()`，但 NvmeService 和 nvme.py API 未暴露。

**修复**：在 `nvme_service.py` 新增方法，在 `nvme.py` 路由新增端点。

```python
# nvme_service.py
@staticmethod
def get_nvme_feature(device_id: int, disk_name: str, fid: str = '0x06') -> dict:
    agent = DeviceService.get_agent(device_id)
    with db_released():
        result = agent.get_nvme_feature(disk_name, fid)
    agent.close()
    return result

@staticmethod
def get_nvme_fw_log(device_id: int, disk_name: str) -> dict:
    agent = DeviceService.get_agent(device_id)
    with db_released():
        result = agent.get_nvme_fw_log(disk_name)
    agent.close()
    return result
```

```python
# nvme.py 路由
@nvme_bp.route('/<int:device_id>/nvme/<disk_name>/get-feature', methods=['GET'])
def get_nvme_feature(device_id, disk_name):
    fid = request.args.get('fid', '0x06')
    return jsonify(NvmeService.get_nvme_feature(device_id, disk_name, fid))

@nvme_bp.route('/<int:device_id>/nvme/<disk_name>/fw-log', methods=['GET'])
def get_nvme_fw_log(device_id, disk_name):
    return jsonify(NvmeService.get_nvme_fw_log(device_id, disk_name))
```

前端：在 `NvmeListTab` 新增 GET-FEATURE / FW-LOG 按钮，在 `NvmeDetailModal` 新增对应渲染视图。

---

## 7. API 接口汇总与契约校验

### 7.1 新增接口清单

| 接口 | Method | Path | 请求体 | 响应体 | 关联需求 |
|------|--------|------|--------|--------|---------|
| 创建基线 | POST | `/api/baselines` | `{task_id, name, device_model?, firmware?}` | Baseline 对象 (201) | BL-1 |
| 基线列表 | GET | `/api/baselines` | query: keyword, device_model, page, page_size | `{items, total}` | BL-2 |
| 基线详情 | GET | `/api/baselines/<id>` | — | Baseline 对象 | BL-3 |
| 删除基线 | DELETE | `/api/baselines/<id>` | — | 204 | BL-4 |
| 执行回归 | POST | `/api/regressions` | `{task_id, baseline_id}` | RegressionResult 对象 (201) | RG-1 |
| 回归详情 | GET | `/api/regressions/<id>` | — | RegressionResult 含 detail | RG-3 |
| 回归列表 | GET | `/api/regressions` | query: verdict, page, page_size | `{items, total}` | RG-4 |
| 创建组任务 | POST | `/api/group-tasks` | `{name, device_ids, fio_config, device_path?}` | GroupTask 含 sub_tasks (202) | GT-1 |
| 组任务列表 | GET | `/api/group-tasks` | query: status, page, page_size | `{items, total}` | GT-1 |
| 组任务详情 | GET | `/api/group-tasks/<id>` | — | GroupTask 含 summary + sub_tasks | GT-3 |
| 删除组任务 | DELETE | `/api/group-tasks/<id>` | — | 204 | — |
| 创建 SNIA 任务 | POST | `/api/snia-tasks` | `{name, device_id, device_path, config?}` | SniaTask 对象 (202) | SN-1 |
| SNIA 任务列表 | GET | `/api/snia-tasks` | query: status, page, page_size | `{items, total}` | SN-1 |
| SNIA 任务详情 | GET | `/api/snia-tasks/<id>` | — | SniaTask 含 iops_history | SN-1 |
| 终止 SNIA 任务 | POST | `/api/snia-tasks/<id>/abort` | — | SniaTask 对象 | SN-1 |
| SNIA 报告 | GET | `/api/snia-tasks/<id>/report` | — | JSON report | SN-8 |
| 创建固件测试 | POST | `/api/fw-tests` | `{name, device_id, device_path, fio_config}` | FwUpgradeTest 对象 (202) | FW-1 |
| 固件测试列表 | GET | `/api/fw-tests` | query: status, page, page_size | `{items, total}` | FW-1 |
| 固件测试详情 | GET | `/api/fw-tests/<id>` | — | FwUpgradeTest 含 results | FW-1 |
| 确认升级 | POST | `/api/fw-tests/<id>/confirm-upgrade` |— | FwUpgradeTest 对象 | FW-2 |
| 终止固件测试 | POST | `/api/fw-tests/<id>/abort` | — | FwUpgradeTest 对象 | FW-1 |
| 固件测试报告 | GET | `/api/fw-tests/<id>/report` | — | JSON report 含 AI 建议 | FW-4 |
| Get Feature | GET | `/api/devices/<id>/nvme/<disk>/get-feature` | query: fid | `{feature_id, value}` | V2.5 修复 |
| FW Log | GET | `/api/devices/<id>/nvme/<disk>/fw-log` | — | fw-log JSON | V2.5 修复 |

### 7.2 前后端字段契约校验

#### Baseline.result 与 Task.result 一致性

| 字段 | Task.result | Baseline.result | 一致性 |
|------|------------|-----------------|--------|
| iops | int/float | int/float | 一致 |
| bandwidth | float (MB/s) | float (MB/s) | 一致 |
| latency.mean | float (us) | float (us) | 一致 |
| latency.p99 | float (us) **新增** | float (us) | 需同步 |

#### Regression.detail.metrics 字段映射

| detail 字段 | 来源 | 单位 |
|-------------|------|------|
| metrics[].name=iops | result.iops | 无 |
| metrics[].name=bw | result.bandwidth | MB/s |
| metrics[].name=lat_mean | result.latency.mean | us |
| metrics[].name=lat_p99 | result.latency.p99 | us |

#### GroupTask.summary 字段映射

| summary 字段 | 来源 | 说明 |
|-------------|------|------|
| iops_max/min/avg | 各子任务 result.iops | 全部成功子任务 |
| bw_max/min/avg | 各子任务 result.bandwidth | 全部成功子任务 |
| lat_mean_max/min/avg | 各子任务 result.latency.mean | 全部成功子任务 |

#### FwUpgradeTest 与 Baseline / Regression 关联

| FW 测试字段 | 关联 | 取值路径 |
|------------|------|---------|
| fw_before | Agent GET fw-log | `_extract_active_fw(fw_log)` |
| fw_after | Agent GET fw-log | 同上，升级后再次读取 |
| result_before | Task result | 基线 FIO 子任务的 result |
| result_after | Task result | 升级后 FIO 子任务的 result |
| regression_id | RegressionResult.id | `RegressionService.run()` 创建 |

---

## 8. 新增前端类型定义

```typescript
// types/baseline.ts
export interface Baseline {
  id: number; name: string;
  device_model: string | null; firmware: string | null;
  fio_config: FioConfig; result: TaskResult;
  source_task_id: number; device_ip: string; device_path: string;
  created_at: string; created_by: string;
}

export interface BaselineCreateParams {
  task_id: number; name: string;
  device_model?: string; firmware?: string;
}

// types/regression.ts
export type RegressionVerdict = 'PASS' | 'WARNING' | 'FAIL';

export interface RegressionMetric {
  name: string; baseline: number; current: number;
  diff_pct: number; verdict: RegressionVerdict; unit: string;
}

export interface RegressionResult {
  id: number; task_id: number; baseline_id: number;
  iops_diff: number | null; bw_diff: number | null;
  lat_mean_diff: number | null; lat_p99_diff: number | null;
  verdict: RegressionVerdict;
  detail: { metrics: RegressionMetric[] };
  created_at: string;
}

// types/group-task.ts
export type GroupTaskStatus = 'pending' | 'running' | 'done' | 'failed' | 'partial';

export interface GroupTask {
  id: number; name: string; fio_config: FioConfig;
  status: GroupTaskStatus; total_count: number; done_count: number;
  summary: {
    iops_max: number | null; iops_min: number | null; iops_avg: number | null;
    bw_max: number | null; bw_min: number | null; bw_avg: number | null;
    lat_mean_max: number | null; lat_mean_min: number | null; lat_mean_avg: number | null;
  } | null;
  sub_tasks: { id: number; device_ip: string; device_path: string; status: TaskStatus }[];
  created_at: string; updated_at: string;
}

// types/snia.ts
export type SniaStatus = 'pending' | 'preconditioning' | 'iops_test' | 'steady_state' | 'done' | 'failed' | 'aborted';

export interface SniaConfig {
  precondition: { rw: string; bs: string;iodepth: number; loops: number };
  iops_test: { block_sizes: string[]; patterns: string[]; iodepth: number; runtime: number };
  steady_state: { rw: string; bs: string; iodepth: number; rounds: number; runtime: number; window: number; threshold: number };
}

export interface SniaTask {
  id: number; name: string;
  device_id: number; device_ip: string; device_path: string;
  status: SniaStatus; current_phase: string | null;
  current_round: number; total_rounds: number;
  iops_history: number[]; is_steady: boolean;
config: SniaConfig; result: any;
  error: string | null;
  created_at: string; updated_at: string;
}

// types/fw-test.ts
export type FwTestStatus = 'pending' | 'collecting_baseline' | 'waiting_upgrade' | 'testing_after' | 'done' | 'failed';

export interface FwUpgradeTest {
  id: number; name: string;
  device_id: number; device_ip: string; device_path: string;
  fw_before: string | null; fw_after: string | null;
  fio_config: FioConfig;
  result_before: TaskResult | null; result_after: TaskResult | null;
  regression_id: number | null;
  status: FwTestStatus; error: string | null;
  created_at: string; updated_at: string;
}
```

---

## 9. 新增前端 API 与 Hooks

### 9.1 API 函数

```typescript
// api/baseline.ts
export const baselineApi = {
  create: (data: BaselineCreateParams) => request.post<Baseline>('/baselines', data),
  list: (params?) => request.get<{items: Baseline[], total: number}>('/baselines', {params}),
  get: (id: number) => request.get<Baseline>(`/baselines/${id}`),
  delete: (id: number) => request.delete(`/baselines/${id}`),
};

// api/regression.ts
export const regressionApi = {
  run: (data: {task_id: number; baseline_id: number}) =>
   request.post<RegressionResult>('/regressions', data),
  get: (id: number) => request.get<RegressionResult>(`/regressions/${id}`),
  list: (params?) => request.get<{items: RegressionResult[], total: number}>('/regressions', {params}),
};

// api/group-task.ts
export const groupTaskApi = {
  create: (data: {name: string; device_ids: number[]; fio_config: Partial<FioConfig>; device_path?: string}) =>
    request.post<GroupTask>('/group-tasks', data),
  list: (params?) => request.get<{items: GroupTask[], total: number}>('/group-tasks', {params}),
  get: (id: number) => request.get<GroupTask>(`/group-tasks/${id}`),
  delete: (id: number) => request.delete(`/group-tasks/${id}`),
};

// api/snia.ts
export const sniaApi = {
  create: (data: {name: string; device_id: number; device_path: string; config?: Partial<SniaConfig>}) =>
    request.post<SniaTask>('/snia-tasks', data),
  list: (params?) => request.get<{items: SniaTask[], total: number}>('/snia-tasks', {params}),
  get: (id: number) => request.get<SniaTask>(`/snia-tasks/${id}`),
  abort: (id: number) => request.post<SniaTask>(`/snia-tasks/${id}/abort`),
  report: (id: number) => request.get(`/snia-tasks/${id}/report`),
};

// api/fw-test.ts
export const fwTestApi = {
  create: (data: {name: string; device_id: number; device_path: string; fio_config: Partial<FioConfig>}) =>
    request.post<FwUpgradeTest>('/fw-tests', data),
  list: (params?) => request.get<{items: FwUpgradeTest[], total: number}>('/fw-tests', {params}),
  get: (id: number) => request.get<FwUpgradeTest>(`/fw-tests/${id}`),
  confirmUpgrade: (id: number) => request.post<FwUpgradeTest>(`/fw-tests/${id}/confirm-upgrade`),
  abort: (id: number) => request.post<FwUpgradeTest>(`/fw-tests/${id}/abort`),
  report: (id: number) => request.get(`/fw-tests/${id}/report`),
};
```

### 9.2 React Query Hooks

```typescript
// hooks/useBaseline.ts
export const useBaselineList = (params?) => useQuery(['baselines', params], () => baselineApi.list(params));
export const useBaselineDetail = (id) => useQuery(['baseline', id], () => baselineApi.get(id), {enabled: !!id});
export const useCreateBaseline = () => useMutation({mutationFn: baselineApi.create, onSuccess: () => qc.invalidateQueries(['baselines'])});
export const useDeleteBaseline = () => useMutation({mutationFn: baselineApi.delete, onSuccess: () => qc.invalidateQueries(['baselines'])});

// hooks/useRegression.ts
export const useRegressionList = (params?) => useQuery(['regressions', params], () => regressionApi.list(params));
export const useRunRegression = () => useMutation({mutationFn: regressionApi.run, onSuccess: () => qc.invalidateQueries(['regressions'])});

// hooks/useGroupTask.ts
export const useGroupTaskList = (params?) => useQuery(['group-tasks', params], () => groupTaskApi.list(params));
export const useGroupTaskDetail = (id) => useQuery(['group-task', id], () => groupTaskApi.get(id), {enabled: !!id});

// hooks/useSniaTask.ts
export const useSniaTaskList = (params?) => useQuery(['snia-tasks', params], () => sniaApi.list(params));
export const useSniaTaskDetail = (id) => useQuery(['snia-task', id], () => sniaApi.get(id), {enabled: !!id, refetchInterval: (d) => d?.status in {'done','failed','aborted'} ? false : 3000});

// hooks/useFwTest.ts
export const useFwTestList = (params?) => useQuery(['fw-tests', params], () => fwTestApi.list(params));
export const useFwTestDetail = (id) => useQuery(['fw-test', id], () => fwTestApi.get(id), {enabled: !!id, refetchInterval: (d) => d?.status in {'done','failed'} ? false : 3000});
export const useConfirmUpgrade = () => useMutation({mutationFn: fwTestApi.confirmUpgrade, onSuccess: (_d, id) => qc.invalidateQueries(['fw-test', id])});
```

---

## 10. 侧边栏导航新增

```typescript
// Sidebar.tsx 新增菜单项
const v2MenuItems = [
  { key: '/baselines', label: '基线管理', icon: <DashboardOutlined /> },
  { key: '/regressions', label: '回归测试', icon: <SwapOutlined /> },
  { key: '/group-tasks', label: '多盘并发', icon: <ClusterOutlined /> },
  { key: '/snia-tasks', label: 'SNIA 测试', icon: <ExperimentOutlined /> },
  { key: '/fw-tests', label: '固件验证', icon: <UpgradeOutlined /> },
];
```

---

## 11. 方案对比与最佳实践选择

### 11.1 多盘并发：Celery chord vs threading + 回调

| 维度 | Celery chord（规划方案） | threading + 回调（现有方案） |
|------|----------------------|--------------------------|
| 引入依赖 | 新增 Redis + Celery | 无新依赖 |
| 复杂度 | 需配置 broker，增加运维 | 纯 Python，与现有架构一致 |
| 可靠性 | 消息持久化，断电恢复 | 线程内存态，进程丢失则丢失 |
| 扩展性 | 大规模并发优 | 当前规模（<50 并发）足够 |

**最佳实践**：沿用 threading + 回调。SSD 测试场景并发量有限（通常 <20 台设备），threading 完全够用，且与现有 APScheduler 架构一致，不引入新依赖。

### 11.2 SNIA 流水线：Celery chain vs daemon thread

| 维度 | Celery chain | daemon thread 驱动 |
|------|-------------|-------------------|
| 依赖 | 同上 | 无 |
| 状态持久化 | 天然支持 | 需通过 DB 状态恢复 |
| 断点续跑 | 支持 | 需额外实现 |

**最佳实践**：daemon thread + DB 状态。SNIA 测试虽有长耗时（数小时），但 Server 进程重启的概率极低。若需断点续跑，可在 `_run_pipeline` 入口读取 `snia_task.current_phase` + `current_round` 恢复。先实现基础方案，后续按需增加断点续跑。

### 11.3 固件升级：Agent 执行 vs 手工

| 维度 | Agent 自动执行 nvme fw-download | 用户手动升级 |
|------|-------------------------------|-------------|
| 安全风险 | 高（刷砖风险） | 低 |
| 灵活性 | 低 | 高（兼容非 NVMe 升级方式） |
| 适用场景 | 自动化 CI | 人工验证 |

**最佳实践**：V2 仅支持用户手动升级 + 确认模式。自动 `nvme fw-download/fw-activate` 作为 V3+ 增强，需增加安全确认和回滚机制。
