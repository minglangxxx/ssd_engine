from enum import Enum
import re
import shlex
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

    @staticmethod
    def parse_cli_command(command: str, device_path: str | None = None) -> dict[str, Any]:
        if not command or not command.strip():
            raise FioConfigError([{'field': 'fio_command', 'message': '原生 fio 命令不能为空'}])

        try:
            tokens = shlex.split(command.strip())
        except ValueError as error:
            raise FioConfigError([{'field': 'fio_command', 'message': f'命令解析失败: {error}'}]) from error

        if not tokens:
            raise FioConfigError([{'field': 'fio_command', 'message': '原生 fio 命令不能为空'}])

        if tokens[0] == 'fio':
            tokens = tokens[1:]

        managed_keys = {'name', 'filename', 'output-format', 'group_reporting', 'status-interval'}
        config: dict[str, Any] = {}
        errors: list[dict[str, str]] = []
        index = 0

        while index < len(tokens):
            token = tokens[index]
            if not token.startswith('--'):
                errors.append({'field': 'fio_command', 'message': f'仅支持 --key=value 或 --key value 形式，无法识别: {token}'})
                index += 1
                continue

            raw_key_value = token[2:]
            if '=' in raw_key_value:
                raw_key, raw_value = raw_key_value.split('=', 1)
                index += 1
            else:
                raw_key = raw_key_value
                next_token = tokens[index + 1] if index + 1 < len(tokens) else None
                spec = FIO_PARAMETERS.get(raw_key)
                if spec and spec['type'] == FioParameterType.BOOLEAN and (next_token is None or next_token.startswith('--')):
                    raw_value = None
                    index += 1
                else:
                    if next_token is None:
                        errors.append({'field': raw_key, 'message': '参数缺少值'})
                        index += 1
                        continue
                    raw_value = next_token
                    index += 2

            if raw_key in managed_keys:
                if raw_key == 'filename' and device_path and raw_value and raw_value != device_path:
                    errors.append({'field': raw_key, 'message': f'filename 与所选设备路径不一致: {raw_value}'})
                continue

            if raw_key not in FIO_PARAMETERS:
                errors.append({'field': raw_key, 'message': f'当前平台暂不支持该 fio 参数: {raw_key}'})
                continue

            try:
                config[raw_key] = FioConfigValidator._coerce_cli_value(raw_key, raw_value)
            except ValueError as error:
                errors.append({'field': raw_key, 'message': str(error)})

        if errors:
            raise FioConfigError(errors)

        return config

    @staticmethod
    def _coerce_cli_value(key: str, raw_value: str | None) -> Any:
        spec = FIO_PARAMETERS[key]
        spec_type = spec['type']

        if spec_type == FioParameterType.BOOLEAN:
            if raw_value is None:
                return True
            normalized = str(raw_value).strip().lower()
            if normalized in {'1', 'true', 'yes', 'on'}:
                return True
            if normalized in {'0', 'false', 'no', 'off'}:
                return False
            raise ValueError('布尔参数只支持 1/0/true/false')

        if raw_value is None:
            raise ValueError('参数缺少值')

        if spec_type == FioParameterType.INTEGER:
            try:
                return int(raw_value)
            except ValueError as error:
                raise ValueError('整数参数格式错误') from error

        return raw_value
