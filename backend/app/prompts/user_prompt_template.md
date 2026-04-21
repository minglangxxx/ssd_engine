以下是 SSD 测试相关的结构化数据，各字段说明如下：

- `task`：任务元数据（含设备 IP、磁盘路径、FIO 参数配置等）。
- `analysis_window`：分析所用的时间窗口（fio_start/fio_end 为 FIO 运行区间，analysis_start/analysis_end 为含前后扩展的完整监控区间）。
- `fio`：FIO 基准测试数据。
  - `config`：FIO 任务参数（rw, bs, iodepth, numjobs, size, runtime 等）。
  - `result`：FIO 最终输出结果 JSON（含 iops, bw, lat, clat, slat 等及其百分位值）。
  - `trend_points`：运行期间逐秒采样的 IOPS / 带宽 / 延迟时序（已降采样至≤120 点）。
  - `trend_summary`：时序数值字段的统计摘要（min / max / avg / last）。
- `host_monitor`：主机级监控时序及摘要（CPU 利用率、内存使用率、网络收发字节等）。
- `disk_monitor`：磁盘级监控时序及摘要（IOPS、带宽、await、aqu-sz、util 等）。
- `input_manifest`：本次分析纳入的数据源类型与记录数。

请严格按照系统提示词中定义的分析框架和输出格式，对以下数据进行分析：