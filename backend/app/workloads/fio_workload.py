from enum import Enum
import re
from typing import Any


class FioParameterType(Enum):
    STRING = 'string'
    INTEGER = 'integer'
    BOOLEAN = 'boolean'


class FioConfigError(Exception):
    def __init__(self, errors: list[dict[str, str]]):
        self.errors = errors
        message = '\n'.join(f"- {error['field']}: {error['message']}" for error in errors)
        super().__init__(message)


FIO_PARAMETERS: dict[str, dict[str, Any]] = {
    'rw': {'type': FioParameterType.STRING, 'default': 'randread', 'values': ['read', 'write', 'rw', 'randread', 'randwrite', 'randrw']},
    'bs': {'type': FioParameterType.STRING, 'default': '4k', 'pattern': r'^\d+[KMGkmg]$'},
    'size': {'type': FioParameterType.STRING, 'default': '1G', 'pattern': r'^\d+[KMGkmg]$'},
    'numjobs': {'type': FioParameterType.INTEGER, 'default': 1, 'min': 1, 'max': 128},
    'iodepth': {'type': FioParameterType.INTEGER, 'default': 32, 'min': 1, 'max': 256},
    'runtime': {'type': FioParameterType.INTEGER, 'default': 60, 'min': 1, 'max': 86400},
    'time_based': {'type': FioParameterType.BOOLEAN, 'default': True},
    'ioengine': {'type': FioParameterType.STRING, 'default': 'sync', 'values': ['sync', 'libaio', 'io_uring', 'posixaio', 'mmap']},
    'direct': {'type': FioParameterType.BOOLEAN, 'default': True},
    'sync': {'type': FioParameterType.BOOLEAN, 'default': False},
    'fsync': {'type': FioParameterType.INTEGER, 'default': 0, 'min': 0},
    'buffer_pattern': {'type': FioParameterType.STRING, 'default': None},
    'thinktime': {'type': FioParameterType.INTEGER, 'default': 0, 'min': 0},
    'latency_target': {'type': FioParameterType.INTEGER, 'default': 0, 'min': 0},
    'rate': {'type': FioParameterType.INTEGER, 'default': 0, 'min': 0},
    'rate_iops': {'type': FioParameterType.INTEGER, 'default': 0, 'min': 0},
    'verify': {'type': FioParameterType.STRING, 'default': None, 'values': ['md5', 'crc32', 'crc64', 'sha256']},
    'verify_fatal': {'type': FioParameterType.BOOLEAN, 'default': False},
    'cpus_allowed': {'type': FioParameterType.STRING, 'default': None},
    'mem': {'type': FioParameterType.STRING, 'default': 'malloc', 'values': ['malloc', 'mmap', 'shmhuge']},
    'random_distribution': {'type': FioParameterType.STRING, 'default': 'random', 'values': ['random', 'zipf', 'pareto']},
    'randseed': {'type': FioParameterType.INTEGER, 'default': None},
    'rwmixread': {'type': FioParameterType.INTEGER, 'default': 50, 'min': 0, 'max': 100},
    'rwmixwrite': {'type': FioParameterType.INTEGER, 'default': 50, 'min': 0, 'max': 100},
    'stats_interval': {'type': FioParameterType.INTEGER, 'default': 1000, 'min': 100, 'max': 60000},
    'log_avg_msec': {'type': FioParameterType.INTEGER, 'default': 1000, 'min': 100, 'max': 60000},
    'loops': {'type': FioParameterType.INTEGER, 'default': 1, 'min': 1, 'max': 10000},
    'startdelay': {'type': FioParameterType.INTEGER, 'default': 0, 'min': 0, 'max': 3600},
}


class FioConfigValidator:
    @staticmethod
    def validate(config: dict[str, Any]) -> list[dict[str, str]]:
        errors: list[dict[str, str]] = []

        for key, value in config.items():
            if key not in FIO_PARAMETERS:
                errors.append({'field': key, 'message': f'未知参数: {key}'})
                continue

            spec = FIO_PARAMETERS[key]
            spec_type = spec['type']

            if spec_type == FioParameterType.INTEGER:
                if not isinstance(value, int) or isinstance(value, bool):
                    errors.append({'field': key, 'message': '类型错误，应为整数'})
                    continue
                if 'min' in spec and value < spec['min']:
                    errors.append({'field': key, 'message': f"值过小，最小值为 {spec['min']}"})
                if 'max' in spec and value > spec['max']:
                    errors.append({'field': key, 'message': f"值过大，最大值为 {spec['max']}"})
            elif spec_type == FioParameterType.STRING:
                if not isinstance(value, str):
                    errors.append({'field': key, 'message': '类型错误，应为字符串'})
                    continue
                if 'values' in spec and value not in spec['values']:
                    errors.append({'field': key, 'message': f"无效值，可选: {spec['values']}"})
                if 'pattern' in spec and not re.match(spec['pattern'], value):
                    errors.append({'field': key, 'message': f"格式错误，应匹配 {spec['pattern']}"})
            elif spec_type == FioParameterType.BOOLEAN:
                if not isinstance(value, bool):
                    errors.append({'field': key, 'message': '类型错误，应为布尔值'})

        return errors

    @staticmethod
    def apply_defaults(config: dict[str, Any]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, spec in FIO_PARAMETERS.items():
            if key in config and config[key] is not None:
                result[key] = config[key]
            elif spec.get('default') is not None:
                result[key] = spec['default']
        return result
