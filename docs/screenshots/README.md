# Screenshots Guide

这个目录用于存放项目截图，方便补充到根目录 README、方案文档或演示材料中。

## 建议放置的截图

- dashboard-overview.png
- task-create-guided.png
- task-create-native.png
- task-detail-trend.png
- task-detail-ai-analysis.png
- device-manage.png
- monitor-host.png
- monitor-disk.png
- data-manage.png

## 推荐命名规则

- 使用小写英文
- 单词之间使用中划线
- 优先使用 png
- 一张图只表达一个核心页面或一个核心交互

## 推荐截图说明

如果后续要把截图挂到 README，建议每张图补一行说明，突出页面重点：

- dashboard-overview.png：展示任务总览、设备状态和全局趋势
- task-create-guided.png：展示引导配置模式、模板和配置摘要
- task-create-native.png：展示原生命令模式和 fio CLI 输入方式
- task-detail-trend.png：展示 FIO 趋势、结果摘要和状态信息
- task-detail-ai-analysis.png：展示 AI 分析报告和分析窗口配置
- device-manage.png：展示设备列表、Agent 状态、最后心跳和刷新动作
- monitor-host.png：展示主机资源监控与时间范围切换
- monitor-disk.png：展示磁盘指标、磁盘切换和多指标图表
- data-manage.png：展示归档、下载和删除等数据管理动作

## 建议截图尺寸

- README 展示图：宽度 1600 到 2000 像素
- 文档内局部说明图：宽度 1200 到 1600 像素
- 浏览器建议使用 100% 缩放并隐藏无关桌面元素

## 截图前建议准备

- 保证页面数据完整，不要用空白列表做展示图
- 尽量使用统一的设备名称和任务名称
- 避免暴露真实内网 IP、密钥、密码或业务敏感信息
- 如果要展示 AI 分析，优先准备一条已完成并已有分析结果的任务

## 后续可选增强

- 在 docs/screenshots 下增加 thumbnails 子目录，放压缩版缩略图
- 在根 README 中直接插入关键页面截图
- 为发布演示单独整理一份图文版产品说明