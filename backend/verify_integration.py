import json
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path


VERIFY_DB = Path('verify_task.db')
STATE = {'tasks': {}}


class Handler(BaseHTTPRequestHandler):
    def _send(self, payload, status=200):
        body = json.dumps(payload).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == '/health':
            self._send({'status': 'healthy', 'version': 'test-agent'})
            return
        if self.path.startswith('/fio/status/'):
            task_id = self.path.split('/')[-1]
            task_state = STATE['tasks'].get(task_id)
            if task_state is None:
                self._send({'status': 'not_found'})
                return
            if task_state['profile'] == 'success':
                self._send({'status': 'success', 'result': {'iops': 1234, 'bandwidth': 5678, 'latency': {'mean': 1, 'min': 1, 'max': 2}}})
                return
            if task_state['profile'] == 'running_then_stop':
                if task_state.get('stopped'):
                    if task_state.get('retry_count', 0) > 0:
                        self._send({'status': 'success', 'result': {'iops': 4321, 'bandwidth': 8765, 'latency': {'mean': 2, 'min': 1, 'max': 4}}})
                    else:
                        self._send({'status': 'failed', 'error': 'User cancelled'})
                else:
                    self._send({'status': 'running'})
            return
        if self.path.startswith('/fio/trend/'):
            task_id = self.path.split('/')[-1]
            task_state = STATE['tasks'].get(task_id, {})
            if task_state.get('profile') == 'running_then_stop' and task_state.get('retry_count', 0) > 0:
                self._send({'data': [{'timestamp': '2026-04-02T12:01:00', 'iops_read': 222, 'iops_write': 333, 'iops_total': 555, 'bw_read': 666, 'bw_write': 777, 'bw_total': 1443, 'lat_mean': 2.2, 'lat_p99': 3.3, 'lat_max': 4.4}]})
                return
            self._send({'data': [{'timestamp': '2026-04-02T12:00:00', 'iops_read': 100, 'iops_write': 200, 'iops_total': 300, 'bw_read': 400, 'bw_write': 500, 'bw_total': 900, 'lat_mean': 1.2, 'lat_p99': 2.3, 'lat_max': 3.4}]})
            return
        if self.path == '/monitor/disks':
            self._send({'disks': [{'name': 'nvme0n1'}]})
            return
        self._send({'error': 'not found'}, 404)

    def do_POST(self):
        length = int(self.headers.get('Content-Length', '0'))
        body = self.rfile.read(length).decode('utf-8') or '{}'
        payload = json.loads(body)
        if self.path == '/fio/start':
            task_id = payload.get('task_id')
            existing = STATE['tasks'].get(task_id)
            if existing is None:
                profile = 'success' if task_id == '1' else 'running_then_stop'
                STATE['tasks'][task_id] = {'profile': profile, 'retry_count': 0, 'stopped': False}
            else:
                existing['retry_count'] = existing.get('retry_count', 0) + 1
                existing['stopped'] = True
            self._send({'success': True, 'task_id': task_id})
            return
        if self.path.startswith('/fio/stop/'):
            task_id = self.path.split('/')[-1]
            task_state = STATE['tasks'].setdefault(task_id, {'profile': 'running_then_stop', 'retry_count': 0, 'stopped': False})
            task_state['stopped'] = True
            self._send({'success': True})
            return
        if self.path == '/execute':
            self._send({'stdout': '', 'stderr': '', 'return_code': 0})
            return
        self._send({'error': 'not found'}, 404)

    def log_message(self, format, *args):
        pass


def main():
    if VERIFY_DB.exists():
        VERIFY_DB.unlink()

    server = HTTPServer(('127.0.0.1', 18080), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    os.environ['DATABASE_URL'] = 'sqlite:///verify_task.db'
    from app import create_app

    app = create_app()
    client = app.test_client()

    try:
        device_resp = client.post('/api/devices', json={'ip': '127.0.0.1', 'name': 'local-agent', 'agent_port': 18080})
        assert device_resp.status_code == 201, device_resp.data

        task_resp = client.post('/api/tasks', json={
            'device_ip': '127.0.0.1',
            'device_user': 'root',
            'device_password': 'root',
            'device_path': '/dev/nvme0n1',
            'config': {'rw': 'randread', 'runtime': 10},
        })
        assert task_resp.status_code == 201, task_resp.data
        task_data = task_resp.get_json()
        assert task_data['status'] == 'RUNNING', task_data

        get_resp = client.get(f"/api/tasks/{task_data['id']}")
        assert get_resp.status_code == 200, get_resp.data
        get_data = get_resp.get_json()
        assert get_data['status'] == 'SUCCESS', get_data
        assert get_data['result']['iops'] == 1234, get_data

        trend_resp = client.get(f"/api/tasks/{task_data['id']}/trend")
        assert trend_resp.status_code == 200, trend_resp.data
        trend_data = trend_resp.get_json()
        assert len(trend_data) == 1, trend_data

        list_resp = client.get('/api/tasks?page=1&pageSize=10')
        assert list_resp.status_code == 200, list_resp.data
        list_data = list_resp.get_json()
        assert list_data['total'] == 1, list_data
        assert list_data['items'][0]['status'] == 'SUCCESS', list_data

        running_task_resp = client.post('/api/tasks', json={
            'device_ip': '127.0.0.1',
            'device_user': 'root',
            'device_password': 'root',
            'device_path': '/dev/nvme0n1',
            'config': {'rw': 'randread', 'runtime': 10},
            'name': 'stop-and-retry-task',
        })
        assert running_task_resp.status_code == 201, running_task_resp.data
        running_task = running_task_resp.get_json()
        assert running_task['status'] == 'RUNNING', running_task

        status_resp = client.get(f"/api/tasks/{running_task['id']}/status")
        assert status_resp.status_code == 200, status_resp.data
        status_data = status_resp.get_json()
        assert status_data['status'] == 'RUNNING', status_data

        stop_resp = client.post(f"/api/tasks/{running_task['id']}/stop")
        assert stop_resp.status_code == 200, stop_resp.data
        stopped_task = stop_resp.get_json()
        assert stopped_task['status'] == 'FAILED', stopped_task
        assert stopped_task['result']['error'] == 'User cancelled', stopped_task

        retry_resp = client.post(f"/api/tasks/{running_task['id']}/retry")
        assert retry_resp.status_code == 200, retry_resp.data
        retried_task = retry_resp.get_json()
        assert retried_task['status'] == 'RUNNING', retried_task

        retry_status_resp = client.get(f"/api/tasks/{running_task['id']}/status")
        assert retry_status_resp.status_code == 200, retry_status_resp.data
        retry_status = retry_status_resp.get_json()
        assert retry_status['status'] == 'SUCCESS', retry_status
        assert retry_status['result']['iops'] == 4321, retry_status

        print(json.dumps({
            'device': device_resp.get_json(),
            'task': get_data,
            'trend': trend_data,
            'list': list_data,
            'stop_task': stopped_task,
            'retry_task': retry_status,
        }, ensure_ascii=False))
    finally:
        server.shutdown()


if __name__ == '__main__':
    main()