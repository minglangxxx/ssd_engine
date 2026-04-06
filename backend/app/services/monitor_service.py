from __future__ import annotations

from app.executors.agent_executor import AgentExecutor


class MonitorService:
    @staticmethod
    def get_agent(host: str) -> AgentExecutor:
        return AgentExecutor(f'http://{host}:8080')

    @staticmethod
    def _flatten_host_point(point: dict) -> dict:
        cpu = point.get('cpu', {})
        memory = point.get('memory', {})
        network = point.get('network', {})
        system = point.get('system', {})
        return {
            'timestamp': point.get('timestamp'),
            'cpu_usage_percent': cpu.get('cpu_usage_percent', 0),
            'cpu_user_percent': cpu.get('cpu_user_percent', 0),
            'cpu_system_percent': cpu.get('cpu_system_percent', 0),
            'cpu_iowait_percent': cpu.get('cpu_iowait_percent', 0),
            'cpu_steal_percent': cpu.get('cpu_steal_percent', 0),
            'load_avg_1m': cpu.get('load_avg_1m', 0),
            'load_avg_5m': cpu.get('load_avg_5m', 0),
            'load_avg_15m': cpu.get('load_avg_15m', 0),
            'mem_total_bytes': memory.get('mem_total_bytes', 0),
            'mem_used_bytes': memory.get('mem_used_bytes', 0),
            'mem_available_bytes': memory.get('mem_available_bytes', 0),
            'mem_usage_percent': memory.get('mem_usage_percent', 0),
            'mem_buffers_bytes': memory.get('mem_buffers_bytes', 0),
            'mem_cached_bytes': memory.get('mem_cached_bytes', 0),
            'swap_total_bytes': memory.get('swap_total_bytes', 0),
            'swap_used_bytes': memory.get('swap_used_bytes', 0),
            'net_rx_bytes_per_sec': network.get('net_rx_bytes_per_sec', 0),
            'net_tx_bytes_per_sec': network.get('net_tx_bytes_per_sec', 0),
            'net_rx_packets_per_sec': network.get('net_rx_packets_per_sec', 0),
            'net_tx_packets_per_sec': network.get('net_tx_packets_per_sec', 0),
            'net_rx_errors': network.get('net_rx_errors', 0),
            'net_tx_errors': network.get('net_tx_errors', 0),
            'tcp_connections': network.get('tcp_connections', 0),
            'context_switches_per_sec': system.get('context_switches_per_sec', 0),
            'interrupts_per_sec': system.get('interrupts_per_sec', 0),
            'process_count': system.get('process_count', 0),
        }

    @staticmethod
    def get_host_metrics(host: str, start: str | None = None, end: str | None = None) -> list[dict]:
        agent = MonitorService.get_agent(host)
        try:
            if start or end:
                return [MonitorService._flatten_host_point(item) for item in agent.get_host_monitor_history(start, end)]
            return [MonitorService._flatten_host_point(agent.get_host_monitor())]
        finally:
            agent.close()

    @staticmethod
    def get_disk_list(host: str) -> list[str]:
        agent = MonitorService.get_agent(host)
        try:
            disks = agent.get_disk_list()
            names: list[str] = []
            for disk in disks:
                if isinstance(disk, dict):
                    names.append(disk.get('name', ''))
                elif isinstance(disk, str):
                    names.append(disk)
            return [item for item in names if item]
        finally:
            agent.close()

    @staticmethod
    def get_disk_metrics(host: str, disk_name: str, start: str | None = None, end: str | None = None) -> list[dict]:
        agent = MonitorService.get_agent(host)
        try:
            if start or end:
                return agent.get_disk_monitor_history(disk_name, start, end)
            return [agent.get_disk_monitor(disk_name)]
        finally:
            agent.close()

    @staticmethod
    def get_host_summary(host: str) -> dict:
        agent = MonitorService.get_agent(host)
        try:
            snapshot = agent.get_host_monitor()
            cpu = snapshot.get('cpu', {})
            memory = snapshot.get('memory', {})
            system = snapshot.get('system', {})
            return {
                'cpu_usage_percent': cpu.get('cpu_usage_percent', 0),
                'mem_usage_percent': memory.get('mem_usage_percent', 0),
                'iowait_percent': cpu.get('cpu_iowait_percent', 0),
                'load_avg_1m': cpu.get('load_avg_1m', 0),
                'load_avg_5m': cpu.get('load_avg_5m', 0),
                'load_avg_15m': cpu.get('load_avg_15m', 0),
                'uptime_seconds': system.get('uptime_seconds', 0),
                'kernel_version': system.get('kernel_version', ''),
                'process_count': system.get('process_count', 0),
            }
        finally:
            agent.close()
