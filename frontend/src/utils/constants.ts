export const TASK_STATUS_MAP: Record<string, { color: string; text: string }> = {
  PENDING: { color: 'default', text: '等待中' },
  RUNNING: { color: 'processing', text: '运行中' },
  SUCCESS: { color: 'success', text: '成功' },
  FAILED: { color: 'error', text: '失败' },
};

export const RW_OPTIONS = [
  { value: 'read', label: '顺序读' },
  { value: 'write', label: '顺序写' },
  { value: 'rw', label: '顺序读写' },
  { value: 'randread', label: '随机读' },
  { value: 'randwrite', label: '随机写' },
  { value: 'randrw', label: '随机读写' },
];

export const IOENGINE_OPTIONS = [
  { value: 'sync', label: 'sync' },
  { value: 'libaio', label: 'libaio' },
  { value: 'io_uring', label: 'io_uring' },
  { value: 'posixaio', label: 'posixaio' },
  { value: 'mmap', label: 'mmap' },
];

export const VERIFY_OPTIONS = [
  { value: 'md5', label: 'MD5' },
  { value: 'crc32', label: 'CRC32' },
  { value: 'crc64', label: 'CRC64' },
  { value: 'sha256', label: 'SHA256' },
];

export const MEM_OPTIONS = [
  { value: 'malloc', label: 'malloc' },
  { value: 'mmap', label: 'mmap' },
  { value: 'shmhuge', label: 'shmhuge' },
];

export const RANDOM_DIST_OPTIONS = [
  { value: 'random', label: '均匀随机' },
  { value: 'zipf', label: 'Zipf分布' },
  { value: 'pareto', label: 'Pareto分布' },
];

export const FAULT_TYPE_OPTIONS = [
  { value: 'none', label: '无故障' },
  { value: 'power_off', label: '断电' },
  { value: 'drop_device', label: '设备掉盘' },
];

export const TASK_TEMPLATE_OPTIONS = [
  { value: 'randread-latency', label: '4k 随机读延迟' },
  { value: 'randwrite-pressure', label: '4k 随机写压力' },
  { value: 'seqread-throughput', label: '128k 顺序读吞吐' },
  { value: 'seqwrite-throughput', label: '128k 顺序写吞吐' },
  { value: 'mixed-7030', label: '70/30 混合读写' },
  { value: 'steady-state', label: 'SSD 稳态压力' },
  { value: 'custom', label: '自定义' },
];

export const TASK_TEMPLATE_PRESETS = {
  'randread-latency': {
    rw: 'randread',
    bs: '4k',
    numjobs: 1,
    iodepth: 1,
    runtime: 60,
    time_based: true,
    direct: true,
  },
  'randwrite-pressure': {
    rw: 'randwrite',
    bs: '4k',
    numjobs: 4,
    iodepth: 32,
    runtime: 120,
    time_based: true,
    direct: true,
  },
  'seqread-throughput': {
    rw: 'read',
    bs: '128k',
    numjobs: 1,
    iodepth: 32,
    runtime: 60,
    time_based: true,
    direct: true,
  },
  'seqwrite-throughput': {
    rw: 'write',
    bs: '128k',
    numjobs: 1,
    iodepth: 32,
    runtime: 60,
    time_based: true,
    direct: true,
  },
  'mixed-7030': {
    rw: 'randrw',
    bs: '4k',
    numjobs: 4,
    iodepth: 32,
    runtime: 120,
    time_based: true,
    direct: true,
    rwmixread: 70,
    rwmixwrite: 30,
  },
  'steady-state': {
    rw: 'randwrite',
    bs: '4k',
    size: '1G',
    numjobs: 4,
    iodepth: 64,
    runtime: 300,
    time_based: true,
    direct: true,
  },
} as const;

export const DATA_STATUS_MAP: Record<string, { color: string; text: string }> = {
  active: { color: 'green', text: '活跃' },
  archived: { color: 'orange', text: '归档' },
  compressed: { color: 'blue', text: '压缩' },
};

export const DATA_TYPE_MAP: Record<string, string> = {
  fio_result: 'FIO结果',
  fio_trend: 'FIO趋势',
  host_monitor: '主机监控',
  disk_monitor: '磁盘监控',
};
