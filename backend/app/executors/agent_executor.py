from typing import Any

import requests

from .base import CommandResult, Executor


class AgentExecutor(Executor):
    def __init__(self, agent_url: str, agent_token: str | None = None):
        self.agent_url = agent_url.rstrip('/')
        self.agent_token = agent_token
        self.session = requests.Session()
        if agent_token:
            self.session.headers.update({'Authorization': f'Bearer {agent_token}'})

    def run(self, command: str, timeout: int = 300) -> CommandResult:
        try:
            response = self.session.post(
                f'{self.agent_url}/execute',
                json={'command': command, 'timeout': timeout},
                timeout=timeout + 10,
            )
            response.raise_for_status()
            payload = response.json()
            rc = payload.get('return_code', -1)
            return CommandResult(
                stdout=payload.get('stdout', ''),
                stderr=payload.get('stderr', ''),
                return_code=rc,
                success=rc == 0,
            )
        except requests.RequestException as error:
            return CommandResult(stdout='', stderr=str(error), return_code=-1, success=False)

    def test_connection(self) -> bool:
        try:
            response = self.session.get(f'{self.agent_url}/health', timeout=5)
            response.raise_for_status()
            return True
        except requests.RequestException:
            return False

    def get_health(self) -> dict[str, Any]:
        response = self.session.get(f'{self.agent_url}/health', timeout=5)
        response.raise_for_status()
        return response.json()

    def get_disk_list(self) -> list[dict[str, Any]]:
        response = self.session.get(f'{self.agent_url}/monitor/disks', timeout=10)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, dict):
            return data.get('disks', [])
        return data

    def get_host_monitor(self) -> dict[str, Any]:
        response = self.session.get(f'{self.agent_url}/monitor/host', timeout=10)
        response.raise_for_status()
        return response.json()

    def get_host_monitor_history(self, start: str | None = None, end: str | None = None) -> list[dict[str, Any]]:
        params = {}
        if start:
            params['start'] = start
        if end:
            params['end'] = end
        response = self.session.get(f'{self.agent_url}/monitor/host/history', params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, dict):
            return data.get('data', [])
        return data

    def get_disk_monitor(self, disk_name: str) -> dict[str, Any]:
        response = self.session.get(f'{self.agent_url}/monitor/disk/{disk_name}', timeout=10)
        response.raise_for_status()
        return response.json()

    def get_disk_monitor_history(self, disk_name: str, start: str | None = None, end: str | None = None) -> list[dict[str, Any]]:
        params = {}
        if start:
            params['start'] = start
        if end:
            params['end'] = end
        response = self.session.get(
            f'{self.agent_url}/monitor/disk/{disk_name}/history',
            params=params,
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        if isinstance(data, dict):
            return data.get('data', [])
        return data

    def get_smart(self, device: str) -> dict[str, Any]:
        response = self.session.get(f'{self.agent_url}/smart/{device}', timeout=10)
        response.raise_for_status()
        return response.json()

    def fio_trend(self, task_id: str, start: str | None = None, end: str | None = None) -> list[dict[str, Any]]:
        params = {}
        if start:
            params['start'] = start
        if end:
            params['end'] = end
        response = self.session.get(f'{self.agent_url}/fio/trend/{task_id}', params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, dict):
            return data.get('data', [])
        return data

    def fio_start(self, task_id: str, config: dict[str, Any], device: str) -> dict[str, Any]:
        response = self.session.post(
            f'{self.agent_url}/fio/start',
            json={'task_id': task_id, 'config': config, 'device': device},
            timeout=15,
        )
        response.raise_for_status()
        return response.json()

    def fio_status(self, task_id: str) -> dict[str, Any]:
        response = self.session.get(f'{self.agent_url}/fio/status/{task_id}', timeout=10)
        response.raise_for_status()
        return response.json()

    def fio_stop(self, task_id: str) -> dict[str, Any]:
        response = self.session.post(f'{self.agent_url}/fio/stop/{task_id}', timeout=10)
        response.raise_for_status()
        return response.json()

    def close(self) -> None:
        self.session.close()

