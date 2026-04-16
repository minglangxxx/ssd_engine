import dayjs from 'dayjs';

export function formatApiDateTime(time?: dayjs.ConfigType): string {
  return dayjs(time).format('YYYY-MM-DDTHH:mm:ss.SSSZ');
}

export function formatTime(time: string): string {
  return dayjs(time).format('YYYY-MM-DD HH:mm:ss');
}

export function formatShortTime(time: string): string {
  return dayjs(time).format('MM-DD HH:mm');
}

export function formatChartTime(time: string): string {
  return dayjs(time).format('HH:mm:ss');
}

export function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

export function formatBandwidth(bytesPerSec: number): string {
  return formatBytes(bytesPerSec) + '/s';
}

export function formatPercent(value: number): string {
  return value.toFixed(1) + '%';
}

export function formatNumber(value: number): string {
  if (value >= 1000000) return (value / 1000000).toFixed(1) + 'M';
  if (value >= 1000) return (value / 1000).toFixed(1) + 'K';
  return value.toString();
}

export function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds}秒`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}分钟`;
  const hours = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  return mins > 0 ? `${hours}小时${mins}分钟` : `${hours}小时`;
}

export function formatUptime(seconds: number): string {
  const days = Math.floor(seconds / 86400);
  if (days > 0) return `${days}天`;
  return formatDuration(seconds);
}
