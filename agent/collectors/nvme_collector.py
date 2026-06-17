import json
import subprocess
import time

from logger import get_logger

logger = get_logger(__name__)


class NvmeCollector:
    @staticmethod
    def id_ctrl(device: str) -> dict:
        try:
            result = subprocess.run(
                ['nvme', 'id-ctrl', device, '-o', 'json'],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            if result.returncode != 0:
                logger.warning('nvme id-ctrl failed for %s: %s', device, result.stderr.strip())
                return {}
            return json.loads(result.stdout)
        except Exception:
            logger.exception('Failed to collect id-ctrl for %s', device)
            return {}

    @staticmethod
    def id_ns(device: str) -> dict:
        try:
            result = subprocess.run(
                ['nvme', 'id-ns', device, '-o', 'json'],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            if result.returncode != 0:
                logger.warning('nvme id-ns failed for %s: %s', device, result.stderr.strip())
                return {}
            return json.loads(result.stdout)
        except Exception:
            logger.exception('Failed to collect id-ns for %s', device)
            return {}

    @staticmethod
    def error_log(device: str) -> dict:
        """读取 NVMe Error Log，device 应为 controller 路径（如 /dev/nvme0）"""
        try:
            result = subprocess.run(
                ['nvme', 'error-log', device, '-o', 'json'],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            if result.returncode != 0:
                logger.warning('nvme error-log failed for %s: %s', device, result.stderr.strip())
                return {}
            return json.loads(result.stdout)
        except Exception:
            logger.exception('Failed to collect error-log for %s', device)
            return {}

    @staticmethod
    def error_log_verify(controller: str) -> dict:
        """增量比对 SMART num_err_log_entries 计数器的单调性及 error-log 缓冲区合理性

        NVMe 规范中 num_err_log_entries 是累计计数器（单调递增），
        而 nvme error-log 返回的是环形缓冲区（最多 64 条），
        两者不可做等值比对。改用两次采样增量校验：
        1. 第一次采样 SMART 计数器 → 读 error-log 缓冲区
        2. 等待 2 秒
        3. 第二次采样 SMART 计数器
        校验：计数器不应减少 + 缓冲区条目数 ≤ 计数器最新值
        """
        try:
            smart1_result = subprocess.run(
                ['nvme', 'smart-log', controller, '-o', 'json'],
                capture_output=True, text=True, timeout=15, check=False,
            )
            if smart1_result.returncode != 0:
                return {'skipped': True, 'skip_reason': '第一次smart-log读取失败'}

            smart1_data = json.loads(smart1_result.stdout)
            count1 = int(smart1_data.get('num_err_log_entries', 0) or 0)

            err_result = subprocess.run(
                ['nvme', 'error-log', controller, '-o', 'json'],
                capture_output=True, text=True, timeout=15, check=False,
            )
            if err_result.returncode != 0:
                return {'skipped': True, 'skip_reason': '读取error-log失败'}

            err_data = json.loads(err_result.stdout)
            err_entry_count = len(err_data.get('error_log_entries', []))

            time.sleep(2)

            smart2_result = subprocess.run(
                ['nvme', 'smart-log', controller, '-o', 'json'],
                capture_output=True, text=True, timeout=15, check=False,
            )
            if smart2_result.returncode != 0:
                return {
                    'error_log_count': err_entry_count,
                    'smart_count_first': count1,
                    'smart_count_second': None,
                    'consistent': None,
                    'skipped': True,
                    'skip_reason': '第二次smart-log读取失败',
                }
            smart2_data = json.loads(smart2_result.stdout)
            count2 = int(smart2_data.get('num_err_log_entries', 0) or 0)

            counter_not_decreased = (count2 >= count1)
            buffer_within_counter = (err_entry_count <= count2)

            consistent = counter_not_decreased and buffer_within_counter
            return {
                'error_log_count': err_entry_count,
                'smart_count_first': count1,
                'smart_count_second': count2,
                'counter_delta': count2 - count1,
                'consistent': consistent,
            }
        except Exception as e:
            logger.exception('Failed to verify error-log for %s', controller)
            return {'skipped': True, 'skip_reason': str(e)}
