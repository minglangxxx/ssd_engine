# Frontend

Frontend 是 SSD Engine 的 Web 控制台，负责设备管理、任务编排、趋势查看、SMART 查看、AI 分析阅读和数据治理操作。

## 技术栈

- React 18
- TypeScript
- Vite 5
- Ant Design 5
- React Router 6
- Axios
- Zustand
- ECharts 和 echarts-for-react
- dayjs
- react-markdown
- file-saver

## 目录结构

```text
frontend/
├── index.html
├── package.json
├── vite.config.ts
└── src/
    ├── api/            对 Backend /api 的请求封装
    │   ├── task.ts     任务 API
    │   ├── device.ts   设备 API
    │   ├── monitor.ts  监控 API
    │   ├── nvme.ts     NVMe SMART API
    │   ├── analysis.ts AI 分析 API
    │   └── data.ts     数据治理 API
    ├── components/     通用组件和业务组件
    ├── hooks/          轮询、监控、任务、AI 分析等自定义 Hook
    ├── pages/          页面级模块
    │   ├── Dashboard/      仪表盘总览
    │   ├── TaskList/       任务列表
    │   ├── TaskDetail/     任务详情（状态/趋势/AI 分析）
    │   ├── DeviceManage/   设备管理
    │   ├── DeviceDetail/   设备详情（SMART/健康评分）
    │   ├── MonitorHost/    主机监控
    │   ├── MonitorDisk/    磁盘监控
    │   └── DataManage/     数据治理
    ├── stores/         Zustand 状态
    ├── styles/         全局样式
    ├── types/          前端类型定义
    ├── utils/          request 封装、下载等工具
    ├── App.tsx         路由入口
    └── main.tsx
```

## 页面路由

App.tsx 当前注册了以下页面：

| 路径 | 页面 | 功能说明 |
|------|------|----------|
| / | Dashboard | 仪表盘总览，展示设备状态、任务统计、健康概览 |
| /tasks | TaskList | FIO 任务列表，支持创建、筛选、批量操作 |
| /tasks/:id | TaskDetail | 任务详情，包含状态、趋势图表、AI 分析报告 |
| /monitor/hosts | MonitorHost | 主机监控，CPU/内存/网络实时曲线 |
| /monitor/disks | MonitorDisk | 磁盘监控，IOPS/带宽/延迟/队列深度曲线 |
| /devices | DeviceManage | 设备列表，添加/编辑/删除设备 |
| /devices/:id | DeviceDetail | 设备详情，SMART 数据、健康评分、告警 |
| /data | DataManage | 数据治理，归档/压缩/下载/清理 |

这些页面统一挂载在 AppLayout 下。

## 请求层约定

src/utils/request.ts 中统一创建 Axios 实例：

- baseURL 为 /api
- timeout 为 30000ms
- 响应拦截器统一从 response.data 返回数据
- 接口错误通过 Ant Design message 弹出提示

因此页面和 Hook 不直接拼接完整服务地址，只面向 /api 路径。

## API 模块

### 任务

| 前端方法 | 后端接口 | 说明 |
|------|------|------|
| taskApi.create | POST /api/tasks | 创建 FIO 任务 |
| taskApi.list | GET /api/tasks | 获取任务列表 |
| taskApi.get | GET /api/tasks/:id | 获取任务详情 |
| taskApi.getStatus | GET /api/tasks/:id/status | 获取任务状态 |
| taskApi.getTrend | GET /api/tasks/:id/trend | 获取 FIO 趋势数据 |
| taskApi.stop | POST /api/tasks/:id/stop | 停止任务 |
| taskApi.retry | POST /api/tasks/:id/retry | 重试任务 |
| taskApi.delete | DELETE /api/tasks/:id | 删除任务 |

### 设备

| 前端方法 | 后端接口 | 说明 |
|------|------|------|
| deviceApi.list | GET /api/devices | 获取设备列表 |
| deviceApi.add | POST /api/devices | 添加设备 |
| deviceApi.update | PUT /api/devices/:id | 更新设备信息 |
| deviceApi.delete | DELETE /api/devices/:id | 删除设备 |
| deviceApi.getInfo | GET /api/devices/:id/info | 获取设备详情与磁盘信息 |
| deviceApi.testConnection | POST /api/devices/test-connection | 测试 Agent 连通性 |
| deviceApi.getAgentStatus | GET /api/devices/:id/agent-status | 获取 Agent 状态 |

### 监控

| 前端方法 | 后端接口 | 说明 |
|------|------|------|
| monitorApi.getHostMetrics | GET /api/monitor/hosts/:host/metrics | 主机监控历史 |
| monitorApi.getDiskList | GET /api/monitor/hosts/:host/disks | 磁盘列表 |
| monitorApi.getDiskMetrics | GET /api/monitor/hosts/:host/disks/:disk/metrics | 磁盘监控数据 |
| monitorApi.getHostSummary | GET /api/monitor/hosts/:host/summary | 主机概览 |

### AI 分析

| 前端方法 | 后端接口 | 说明 |
|------|------|------|
| analysisApi.analyze | POST /api/tasks/:taskId/ai-analysis | 提交分析任务 |
| analysisApi.getResult | GET /api/tasks/:taskId/ai-analysis | 获取分析结果 |
| analysisApi.getHistory | GET /api/tasks/:taskId/ai-analysis/history | 获取历史分析 |

### 数据治理

| 前端方法 | 后端接口 | 说明 |
|------|------|------|
| dataApi.list | GET /api/data | 数据记录列表 |
| dataApi.getOverview | GET /api/data/overview | 数据概览 |
| dataApi.download | POST /api/data/download | 下载数据 |
| dataApi.archive | POST /api/data/archive | 归档数据 |
| dataApi.delete | POST /api/data/delete | 删除数据 |
| dataApi.compress | POST /api/data/compress | 压缩数据 |

### SMART

| 前端方法 | 后端接口 | 说明 |
|------|------|------|
| smartApi.getLatest | GET /api/devices/:deviceId/smart/latest | 最新 SMART 数据 |
| smartApi.getHistory | GET /api/devices/:deviceId/smart/history | SMART 历史趋势 |
| smartApi.getHealthScore | GET /api/devices/:deviceId/smart/health-score | 健康评分 |
| smartApi.getAlerts | GET /api/devices/:deviceId/smart/alerts | SMART 告警 |

## 页面功能说明

### 仪表盘（Dashboard）

- 设备总数和在线状态统计
- 任务执行状态统计（运行中/已完成/失败）
- NVMe 健康概览（各等级设备数量）
- 最近任务列表

### 任务管理

- **任务创建**：支持引导模式（表单填写参数）和原生命令模式（直接输入 FIO 命令）
- **任务详情**：实时状态、FIO 趋势图表（IOPS/带宽/延迟）、AI 分析报告
- **任务操作**：停止、重试、删除

### 设备管理

- 设备添加/编辑/删除
- Agent 连通性测试
- 设备磁盘信息查看
- NVMe SMART 数据和健康评分

### 监控中心

- **主机监控**：CPU、内存、网络使用率实时曲线
- **磁盘监控**：IOPS、带宽、延迟、队列深度、util 等指标曲线

### 数据治理

- 数据记录列表和概览
- 手动归档、压缩、下载、清理
- 自动归档和清理任务触发

## 开发模式

```bash
cd frontend
npm install
npm run dev
```

vite.config.ts 中的开发服务器配置如下：

- 本地端口：3000
- /api 代理目标：http://127.0.0.1:5000

这意味着本地开发时只需要保证 Backend 正常运行即可。

## 构建

```bash
cd frontend
npm run build
npm run preview
```

构建产物位于 dist，生产环境通常使用 Nginx 等静态服务器托管，并把 /api 反向代理到 Backend。

## Nginx 配置示例

```nginx
server {
    listen 80;
    server_name ssd-engine.example.com;

    location / {
        root /path/to/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```
