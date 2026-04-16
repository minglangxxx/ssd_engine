from __future__ import annotations

import json
from datetime import datetime, timedelta
from numbers import Number

from openai import OpenAI

from app.config import Config
from app.extensions import db
from app.models.analysis import AiAnalysis
from app.models.task import Task
from app.services.monitor_service import MonitorService
from app.services.task_service import TaskService
from app.utils.helpers import ApiError


MAX_CONTEXT_POINTS = 120


class AnalysisService:
    def __init__(self):
        if not Config.AI_API_KEY:
            raise ApiError('VALIDATION_ERROR', '未配置 AI_API_KEY', 400)
        self.client = OpenAI(api_key=Config.AI_API_KEY, base_url=Config.AI_BASE_URL)
        self.model = Config.AI_MODEL

    def analyze(
        self,
        task_id: int,
        include_fio: bool,
        include_host_monitor: bool,
        include_disk_monitor: bool,
        window_before_seconds: int = 30,
        window_after_seconds: int = 30,
    ) -> AiAnalysis:
        task = Task.query.get(task_id)
        if not task:
            raise ApiError('NOT_FOUND', '任务不存在', 404)
        TaskService.refresh_runtime_state(task)

        execution_window = TaskService.get_execution_window(
            task,
            window_before_seconds=window_before_seconds,
            window_after_seconds=window_after_seconds,
        )
        self._validate_analysis_window(task, execution_window)

        if include_fio and not task.result:
            raise ApiError('VALIDATION_ERROR', '任务尚未产出 FIO 结果，暂时无法分析', 400)

        analysis = AiAnalysis(
            task_id=task_id,
            status='analyzing',
            data_window_start=self._parse_datetime(execution_window.get('analysis_start')),
            data_window_end=self._parse_datetime(execution_window.get('analysis_end')),
        )
        db.session.add(analysis)
        db.session.commit()

        try:
            context = self._build_context(
                task,
                execution_window,
                include_fio,
                include_host_monitor,
                include_disk_monitor,
            )
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {'role': 'system', 'content': self._system_prompt()},
                    {'role': 'user', 'content': self._build_prompt(context)},
                ],
                temperature=0.3,
                max_tokens=4096,
            )
            report = completion.choices[0].message.content or ''
            analysis.status = 'completed'
            analysis.report = report
            analysis.summary = self._extract_summary(report)
            analysis.input_manifest = context.get('input_manifest')
            analysis.source_snapshot_version = task.updated_at.isoformat() if task.updated_at else None
            analysis.completed_at = datetime.utcnow()
            task.last_analysis_at = analysis.completed_at
            db.session.commit()
            return analysis
        except Exception as error:
            analysis.status = 'failed'
            analysis.error = str(error)
            db.session.commit()
            return analysis

    def _build_context(
        self,
        task: Task,
        execution_window: dict,
        include_fio: bool,
        include_host_monitor: bool,
        include_disk_monitor: bool,
    ) -> dict:
        context: dict = {
            'task': task.to_dict(),
            'analysis_window': execution_window,
            'input_manifest': {
                'task_id': task.id,
                'sources': [],
            },
        }

        fio_start = self._as_string(execution_window.get('fio_start'))
        fio_end = self._as_string(execution_window.get('fio_end'))
        analysis_start = self._as_string(execution_window.get('analysis_start'))
        analysis_end = self._as_string(execution_window.get('analysis_end'))

        if include_fio:
            fio_trend = TaskService.get_trend(task.id, fio_start, fio_end)
            context['fio'] = {
                'config': task.config,
                'result': task.result,
                'device_path': task.device_path,
                'trend_points': self._compress_series(fio_trend),
                'trend_summary': self._summarize_numeric_series(fio_trend),
            }
            context['input_manifest']['sources'].append({
                'data_type': 'fio_trend',
                'record_count': len(fio_trend),
                'window_start': fio_start,
                'window_end': fio_end,
            })
        if include_host_monitor:
            host_metrics = MonitorService.get_host_metrics(task.device_ip, analysis_start, analysis_end)
            context['host_monitor'] = {
                'points': self._compress_series(host_metrics),
                'summary': self._summarize_numeric_series(host_metrics),
            }
            context['input_manifest']['sources'].append({
                'data_type': 'host_monitor',
                'record_count': len(host_metrics),
                'window_start': analysis_start,
                'window_end': analysis_end,
            })
        if include_disk_monitor:
            disk_name = task.device_path.split('/')[-1]
            disk_metrics = MonitorService.get_disk_metrics(task.device_ip, disk_name, analysis_start, analysis_end)
            context['disk_monitor'] = {
                'disk_name': disk_name,
                'points': self._compress_series(disk_metrics),
                'summary': self._summarize_numeric_series(disk_metrics),
            }
            context['input_manifest']['sources'].append({
                'data_type': 'disk_monitor',
                'disk_name': disk_name,
                'record_count': len(disk_metrics),
                'window_start': analysis_start,
                'window_end': analysis_end,
            })
        return context

    def _validate_analysis_window(self, task: Task, execution_window: dict) -> None:
        reference_time = task.finished_at or self._parse_datetime(execution_window.get('fio_end'))
        if reference_time is None:
            raise ApiError('VALIDATION_ERROR', '任务缺少可分析时间窗口', 400)

        max_age_days = max(1, int(Config.AI_ANALYSIS_MAX_AGE_DAYS))
        if reference_time < datetime.utcnow() - timedelta(days=max_age_days):
            raise ApiError('VALIDATION_ERROR', f'当前仅支持分析 {max_age_days} 天内完成的任务', 400)

    def _system_prompt(self) -> str:
        return (
            '你是一名专业的存储性能分析工程师和SSD测试专家。'
            '请基于给定的FIO结果、主机监控和磁盘监控数据，给出性能评估、疑点发现、优化建议和总结。'
        )

    def _build_prompt(self, context: dict) -> str:
        return '请分析以下 SSD 测试数据：\n' + json.dumps(context, ensure_ascii=False, indent=2, default=str)

    def _compress_series(self, points: list[dict]) -> list[dict]:
        if len(points) <= MAX_CONTEXT_POINTS:
            return points

        step = max(1, len(points) // MAX_CONTEXT_POINTS)
        sampled = points[::step]
        if sampled[-1] != points[-1]:
            sampled.append(points[-1])
        return sampled[:MAX_CONTEXT_POINTS]

    def _summarize_numeric_series(self, points: list[dict]) -> dict:
        numeric_fields: dict[str, list[float]] = {}
        for point in points:
            if not isinstance(point, dict):
                continue
            for key, value in point.items():
                if key == 'timestamp' or not isinstance(value, Number):
                    continue
                numeric_fields.setdefault(key, []).append(float(value))

        summary: dict[str, dict] = {}
        for key, values in numeric_fields.items():
            if not values:
                continue
            summary[key] = {
                'min': min(values),
                'max': max(values),
                'avg': round(sum(values) / len(values), 4),
                'last': values[-1],
            }
        return summary

    def _as_string(self, value: object) -> str | None:
        if value is None:
            return None
        return str(value)

    def _parse_datetime(self, value: object) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace('Z', '+00:00'))
            except ValueError:
                return None
        return None

    def _extract_summary(self, report: str) -> dict:
        rating = 'normal'
        lowered = report.lower()
        if 'excellent' in lowered or '优秀' in report:
            rating = 'excellent'
        elif 'good' in lowered or '良好' in report:
            rating = 'good'
        elif 'poor' in lowered or '较差' in report or '异常' in report:
            rating = 'poor'
        return {
            'performance_rating': rating,
            'issues_found': report.count('- '),
            'suggestions_count': report.count('建议') + lowered.count('suggest'),
        }

    @staticmethod
    def get_latest(task_id: int) -> AiAnalysis | None:
        return AiAnalysis.query.filter_by(task_id=task_id).order_by(AiAnalysis.created_at.desc()).first()

    @staticmethod
    def get_history(task_id: int) -> list[AiAnalysis]:
        return AiAnalysis.query.filter_by(task_id=task_id).order_by(AiAnalysis.created_at.desc()).all()
