# SSD 测试平台 - 前端

SSD 性能测试与监控一体化平台前端，基于 React 18 + TypeScript + Vite 构建。

## 系统架构

```
┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│   前端 Web   │◄──API──►│   后端 Flask  │◄──HTTP──►│    Agent     │
│   React      │         │   Server     │         │  (设备节点)   │
└──────────────┘         └──────┬───────┘         └──────────────┘
                               │                         │
                        ┌──────┴───────┐          ┌──────┴───────┐
                        │   MySQL DB   │          │   FIO / 系统  │
                        └──────────────┘          │   监控采集    │
                               │                  └──────────────┘
                        ┌──────┴───────┐
                        │   AI 大模型   │
                        └──────────────┘
```

## 功能模块

| 模块 | 说明 |
|------|------|
| 仪表盘 | 任务统计概览、最近任务列表、设备节点状态、全局 IOPS 趋势 |
| 任务管理 | 创建/查看/删除 FIO 测试任务，支持完整 FIO 参数配置、故障注入 |
| 任务详情 | FIO 性能趋势图（IOPS/带宽/延迟）、测试结果汇总、SMART 信息、AI 智能分析 |
| 主机监控 | CPU/内存/网络/系统信息实时监控，支持时间窗口选择 |
| 磁盘监控 | IOPS/带宽/延迟/队列深度/%util/SMART 健康，支持多磁盘对比 |
| 设备管理 | 设备节点 CRUD、Agent 状态检查、连接测试 |
| 数据管理 | 数据归档/下载/删除，生命周期管理（活跃→归档→压缩→过期删除） |
| AI 分析 | 基于大模型的测试结果智能分析，生成性能评估、疑点发现、优化建议报告 |

## 技术栈

| 技术 | 版本 | 说明 |
|------|------|------|
| React | 18.x | 核心框架 |
| TypeScript | 5.x | 类型安全 |
| Vite | 5.x | 构建工具 |
| Ant Design | 5.x | UI 组件库 |
| Zustand | 4.x | 轻量状态管理 |
| @tanstack/react-query | 5.x | 数据请求与缓存 |
| ECharts | 5.x | 性能图表 |
| Axios | 1.x | HTTP 客户端 |
| React Router | 6.x | 路由管理 |
| Day.js | - | 时间处理 |
| react-markdown | 9.x | AI 分析报告渲染 |
| file-saver | 2.x | 数据导出下载 |

## 项目结构

```
frontend/
├── index.html                        # HTML 入口
├── package.json                      # 依赖配置
├── vite.config.ts                    # Vite 配置（路径别名 + API 代理）
├── tsconfig.json                     # TypeScript 配置
└── src/
    ├── main.tsx                      # 应用入口（QueryClientProvider）
    ├── App.tsx                       # 路由配置（BrowserRouter + Layout）
    ├── vite-env.d.ts                 # Vite 类型声明
    │
    ├── types/                        # TypeScript 类型定义
    │   ├── task.ts                   #   Task, FioConfig, FioTrendPoint, TaskCreateParams
    │   ├── device.ts                 #   Device, DeviceAddParams
    │   ├── monitor.ts                #   HostMetricPoint, DiskMetricPoint, TimeRange
    │   ├── analysis.ts               #   AiAnalysisRequest, AiAnalysisResult
    │   └── data.ts                   #   DataRecord, DataOverview, DataListParams
    │
    ├── utils/                        # 工具函数
    │   ├── request.ts                #   Axios 实例（baseURL=/api, 拦截器）
    │   ├── format.ts                 #   formatTime, formatBytes, formatNumber 等
    │   ├── download.ts               #   downloadBlob, downloadJson
    │   └── constants.ts              #   状态映射、FIO参数选项常量
    │
    ├── api/                          # API 封装层
    │   ├── index.ts                  #   统一导出
    │   ├── task.ts                   #   CRUD + getTrend
    │   ├── device.ts                 #   CRUD + testConnection
    │   ├── monitor.ts                #   getHostMetrics, getDiskMetrics, getDiskList
    │   ├── analysis.ts               #   analyze, getResult, getHistory
    │   └── data.ts                   #   list, download, archive, delete
    │
    ├── stores/                       # Zustand 状态管理
    │   ├── taskStore.ts              #   任务列表/筛选状态
    │   ├── monitorStore.ts           #   监控选择状态（主机/磁盘/时间范围）
    │   └── uiStore.ts                #   侧边栏折叠状态
    │
    ├── hooks/                        # 自定义 Hooks
    │   ├── useTask.ts                #   useTaskList, useTaskDetail, useCreateTask, useFioTrend
    │   ├── useMonitor.ts             #   useHostMonitor, useDiskMonitor, useDiskList
    │   ├── useAiAnalysis.ts          #   useAiAnalysis, useTriggerAnalysis
    │   ├── usePolling.ts             #   轮询 Hook（运行中任务自动刷新）
    │   └── useWebSocket.ts           #   WebSocket Hook（预留）
    │
    ├── components/                   # 通用组件
    │   ├── Layout/                   #   Header + Sidebar + Content 布局
    │   │   ├── index.tsx             #     AppLayout（Outlet 嵌套路由）
    │   │   ├── Header.tsx            #     顶部导航栏
    │   │   └── Sidebar.tsx           #     侧边菜单（仪表盘/任务/监控/设备/数据）
    │   ├── TaskStatusBadge/          #   任务状态标签（PENDING/RUNNING/SUCCESS/FAILED）
    │   ├── TimeRangeSelector/        #   时间窗口选择器（1m/5m/15m/1h/全部/自定义）
    │   ├── TaskCreateModal/          #   创建任务弹窗（设备配置+FIO基础+高级折叠+故障）
    │   ├── AiAnalysisPanel/          #   AI 分析面板（触发+范围选择+Markdown报告）
    │   └── LoadingOverlay/           #   加载遮罩
    │
    ├── pages/                        # 页面组件
    │   ├── Dashboard/index.tsx       #   仪表盘（统计卡片+最近任务+设备状态+趋势图）
    │   ├── TaskList/index.tsx        #   任务列表（筛选+搜索+分页+创建弹窗入口）
    │   ├── TaskDetail/               #   任务详情
    │   │   ├── index.tsx             #     基本信息+配置+结果汇总+SMART+AI分析
    │   │   └── FioTrendSection.tsx   #     FIO 趋势图（双Y轴IOPS/BW + 延迟图）
    │   ├── MonitorHost/index.tsx     #   主机监控（CPU/内存/网络/系统信息图表）
    │   ├── MonitorDisk/index.tsx     #   磁盘监控（IOPS/BW/延迟/队列/util/SMART）
    │   ├── DeviceManage/index.tsx    #   设备管理（CRUD+连接测试+详情展开）
    │   └── DataManage/index.tsx      #   数据管理（概览+筛选+批量下载/归档/删除）
    │
    └── styles/
        └── global.css                # 全局样式（CSS变量+滚动条+响应式）
```

## 路由

| 路径 | 页面 | 说明 |
|------|------|------|
| `/` | Dashboard | 仪表盘 |
| `/tasks` | TaskList | 任务列表 |
| `/tasks/:id` | TaskDetail | 任务详情（趋势图 + AI 分析） |
| `/monitor/hosts` | MonitorHost | 主机维度监控 |
| `/monitor/disks` | MonitorDisk | 磁盘维度监控 |
| `/devices` | DeviceManage | 设备管理 |
| `/data` | DataManage | 数据管理 |

## 快速开始

```bash
# 安装依赖
cd frontend
npm install

# 启动开发服务器（默认 http://localhost:3000）
npm run dev

# 生产构建
npm run build

# 预览构建产物
npm run preview
```

## 开发配置

### API 代理

开发模式下 `/api` 请求自动代理到后端（`vite.config.ts`）：

```typescript
server: {
  port: 3000,
  proxy: {
    '/api': {
      target: 'http://127.0.0.1:5000',
      changeOrigin: true,
    },
  },
}
```

### 路径别名

`@` 映射到 `src/` 目录，支持 `import { taskApi } from '@/api/task'` 写法。

## 部署

Nginx 反向代理配置：

```nginx
server {
    listen 80;
    server_name <your-ip>;

    root /var/www/ssd-frontend/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## API 端点

| 模块 | 方法 | 端点 | 说明 |
|------|------|------|------|
| 任务 | POST | `/api/tasks` | 创建任务 |
| | GET | `/api/tasks` | 任务列表（支持 status/keyword/page 筛选） |
| | GET | `/api/tasks/:id` | 任务详情 |
| | DELETE | `/api/tasks/:id` | 删除任务 |
| | GET | `/api/tasks/:id/trend` | FIO 趋势数据（支持 start/end 时间窗口） |
| | POST | `/api/tasks/:id/ai-analysis` | 触发 AI 分析 |
| | GET | `/api/tasks/:id/ai-analysis` | 获取分析结果 |
| 设备 | GET | `/api/devices` | 设备列表 |
| | POST | `/api/devices` | 添加设备 |
| | PUT | `/api/devices/:id` | 更新设备 |
| | DELETE | `/api/devices/:id` | 删除设备 |
| | POST | `/api/devices/test-connection` | 测试连接 |
| 监控 | GET | `/api/monitor/hosts/:ip/metrics` | 主机监控数据 |
| | GET | `/api/monitor/hosts/:ip/summary` | 主机概览 |
| | GET | `/api/monitor/hosts/:ip/disks` | 磁盘列表 |
| | GET | `/api/monitor/hosts/:ip/disks/:disk/metrics` | 磁盘监控数据 |
| 数据 | GET | `/api/data` | 数据列表 |
| | GET | `/api/data/overview` | 存储概览 |
| | POST | `/api/data/download` | 下载数据 |
| | POST | `/api/data/archive` | 归档数据 |
| | POST | `/api/data/delete` | 删除数据 |
