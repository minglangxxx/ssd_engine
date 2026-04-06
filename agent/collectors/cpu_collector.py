import os

import psutil


class CpuCollector:
    def collect(self) -> dict:
        cpu_times = psutil.cpu_times_percent(interval=0)
        load1, load5, load15 = os.getloadavg()
        return {
            'cpu_usage_percent': psutil.cpu_percent(interval=0),
            'cpu_user_percent': cpu_times.user,
            'cpu_system_percent': cpu_times.system,
            'cpu_iowait_percent': getattr(cpu_times, 'iowait', 0),
            'cpu_steal_percent': getattr(cpu_times, 'steal', 0),
            'cpu_idle_percent': cpu_times.idle,
            'load_avg_1m': load1,
            'load_avg_5m': load5,
            'load_avg_15m': load15,
        }
