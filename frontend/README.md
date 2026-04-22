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
	├── components/     通用组件和业务组件
	├── hooks/          轮询、监控、任务、AI 分析等自定义 Hook
	├── pages/          页面级模块
	├── stores/         Zustand 状态
	├── styles/         全局样式
	├── types/          前端类型定义
	├── utils/          request 封装、下载等工具
	├── App.tsx         路由入口
	└── main.tsx
```

## 页面路由

App.tsx 当前注册了以下页面：

| 路径 | 页面 |
|------|------|
| / | Dashboard |
| /tasks | TaskList |
| /tasks/:id | TaskDetail |
| /monitor/hosts | MonitorHost |
| /monitor/disks | MonitorDisk |
| /devices | DeviceManage |
| /devices/:id | DeviceDetail |
| /data | DataManage |

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

| 前端方法 | 后端接口 |
|------|------|
| taskApi.create | POST /api/tasks |
| taskApi.list | GET /api/tasks |
| taskApi.get | GET /api/tasks/:id |
| taskApi.getStatus | GET /api/tasks/:id/status |
| taskApi.getTrend | GET /api/tasks/:id/trend |
| taskApi.stop | POST /api/tasks/:id/stop |
| taskApi.retry | POST /api/tasks/:id/retry |
| taskApi.delete | DELETE /api/tasks/:id |

### 设备

| 前端方法 | 后端接口 |
|------|------|
| deviceApi.list | GET /api/devices |
| deviceApi.add | POST /api/devices |
| deviceApi.update | PUT /api/devices/:id |
| deviceApi.delete | DELETE /api/devices/:id |
| deviceApi.getInfo | GET /api/devices/:id/info |
| deviceApi.testConnection | POST /api/devices/test-connection |
| deviceApi.getAgentStatus | GET /api/devices/:id/agent-status |

### 监控

| 前端方法 | 后端接口 |
|------|------|
| monitorApi.getHostMetrics | GET /api/monitor/hosts/:host/metrics |
| monitorApi.getDiskList | GET /api/monitor/hosts/:host/disks |
| monitorApi.getDiskMetrics | GET /api/monitor/hosts/:host/disks/:disk/metrics |
| monitorApi.getHostSummary | GET /api/monitor/hosts/:host/summary |

### AI 分析

| 前端方法 | 后端接口 |
|------|------|
| analysisApi.analyze | POST /api/tasks/:taskId/ai-analysis |
| analysisApi.getResult | GET /api/tasks/:taskId/ai-analysis |
| analysisApi.getHistory | GET /api/tasks/:taskId/ai-analysis/history |

### 数据治理

| 前端方法 | 后端接口 |
|------|------|
| dataApi.list | GET /api/data |
| dataApi.getOverview | GET /api/data/overview |
| dataApi.download | POST /api/data/download |
| dataApi.archive | POST /api/data/archive |
| dataApi.delete | POST /api/data/delete |
| dataApi.compress | POST /api/data/compress |

### SMART

| 前端方法 | 后端接口 |
|------|------|
| smartApi.getLatest | GET /api/devices/:deviceId/smart/latest |
| smartApi.getHistory | GET /api/devices/:deviceId/smart/history |
| smartApi.getHealthScore | GET /api/devices/:deviceId/smart/health-score |
| smartApi.getAlerts | GET /api/devices/:deviceId/smart/alerts |

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
