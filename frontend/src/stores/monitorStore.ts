import { create } from 'zustand';
import type { TimeRange } from '@/types/monitor';

interface MonitorState {
  selectedHost: string;
  selectedDisks: string[];
  timeRange: TimeRange;
  autoRefresh: boolean;
  refreshInterval: number;
  setSelectedHost: (host: string) => void;
  setSelectedDisks: (disks: string[]) => void;
  setTimeRange: (range: TimeRange) => void;
  setAutoRefresh: (enabled: boolean) => void;
}

export const useMonitorStore = create<MonitorState>((set) => ({
  selectedHost: '',
  selectedDisks: [],
  timeRange: '5m',
  autoRefresh: true,
  refreshInterval: 5000,
  setSelectedHost: (host) => set({ selectedHost: host, selectedDisks: [] }),
  setSelectedDisks: (disks) => set({ selectedDisks: disks }),
  setTimeRange: (range) => set({ timeRange: range }),
  setAutoRefresh: (enabled) => set({ autoRefresh: enabled }),
}));
