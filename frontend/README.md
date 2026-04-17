# Frontend 模块说明

Frontend 提供 SSD Engine 的用户交互界面，承载任务创建、监控查看、分析阅读和数据操作等完整控制台能力。

## 1. 架构说明

### 1.1 技术架构

- React + TypeScript：页面与业务逻辑开发
- React Router：页面路由组织
- React Query：服务端状态拉取与缓存
- Zustand：界面状态与页面上下文管理
- ECharts：趋势图与监控图可视化
- Axios：统一 API 请求封装

### 1.2 目录结构

```text
frontend/src/
├── api/             接口封装
├── components/      可复用组件
├── hooks/           业务 Hook
├── pages/           页面级功能
├── stores/          客户端状态
├── types/           类型定义
├── utils/           请求与格式化工具
└── styles/          全局样式
```

## 2. 业务逻辑说明

### 2.1 页面主流程

1. 设备管理：录入设备并检查 Agent 状态
2. 任务管理：按参数创建任务并追踪执行状态
3. 任务详情：查看 fio 趋势、结果摘要、SMART 与 AI 报告
4. 主机/磁盘监控：按设备和时间窗查看历史变化
5. 数据管理：归档、下载、删除历史数据

### 2.2 状态与数据流

- 服务器状态：由 React Query 管理，负责缓存与请求重试
- 页面交互状态：由 Zustand 管理，例如筛选条件、当前设备选择
- 轮询策略：对运行中任务与实时监控进行周期刷新
- 错误处理：统一请求拦截与页面提示

### 2.3 组件分工

- 页面组件：负责业务场景编排（任务、设备、监控、数据）
- 通用组件：负责状态标签、时间选择器、布局容器等复用能力
- API 层：负责前端模型到后端接口的映射，不在页面中拼接 URL

## 3. API 对接说明

Frontend 通过 `src/api/*` 对 Backend 的 `/api` 路由进行封装。

### 3.1 任务接口映射

| 前端方法 | 后端接口 |
|------|------|
| `taskApi.create` | `POST /api/tasks` |
| `taskApi.list` | `GET /api/tasks` |
| `taskApi.get` | `GET /api/tasks/<id>` |
| `taskApi.getStatus` | `GET /api/tasks/<id>/status` |
| `taskApi.getTrend` | `GET /api/tasks/<id>/trend` |
| `taskApi.stop` | `POST /api/tasks/<id>/stop` |
| `taskApi.retry` | `POST /api/tasks/<id>/retry` |
| `taskApi.delete` | `DELETE /api/tasks/<id>` |

### 3.2 设备接口映射

| 前端方法 | 后端接口 |
|------|------|
| `deviceApi.list` | `GET /api/devices` |
| `deviceApi.add` | `POST /api/devices` |
| `deviceApi.update` | `PUT /api/devices/<id>` |
| `deviceApi.delete` | `DELETE /api/devices/<id>` |
| `deviceApi.getInfo` | `GET /api/devices/<id>/info` |
| `deviceApi.testConnection` | `POST /api/devices/test-connection` |
| `deviceApi.getAgentStatus` | `GET /api/devices/<id>/agent-status` |

### 3.3 监控、分析、数据接口映射

| 前端方法 | 后端接口 |
|------|------|
| `monitorApi.getHostMetrics` | `GET /api/monitor/hosts/<host>/metrics` |
| `monitorApi.getDiskList` | `GET /api/monitor/hosts/<host>/disks` |
| `monitorApi.getDiskMetrics` | `GET /api/monitor/hosts/<host>/disks/<disk>/metrics` |
| `monitorApi.getHostSummary` | `GET /api/monitor/hosts/<host>/summary` |
| `analysisApi.analyze` | `POST /api/tasks/<taskId>/ai-analysis` |
| `analysisApi.getResult` | `GET /api/tasks/<taskId>/ai-analysis` |
| `analysisApi.getHistory` | `GET /api/tasks/<taskId>/ai-analysis/history` |
| `dataApi.list` | `GET /api/data` |
| `dataApi.getOverview` | `GET /api/data/overview` |
| `dataApi.download` | `POST /api/data/download` |
| `dataApi.archive` | `POST /api/data/archive` |
| `dataApi.delete` | `POST /api/data/delete` |
| `dataApi.compress` | `POST /api/data/compress` |

## 4. 本地开发与部署

### 4.1 本地开发

```bash
cd frontend
npm install
npm run dev
```

开发模式下通过 Vite 代理将 `/api` 转发到 Backend。

### 4.2 生产构建

```bash
cd frontend
npm run build
npm run preview
```

生产部署建议使用 Nginx 托管 `dist`，并将 `/api` 反向代理到 Backend。
