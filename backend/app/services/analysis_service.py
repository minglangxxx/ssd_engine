from __future__ import annotations

import json
import re
import threading
from datetime import datetime, timedelta
from numbers import Number
from pathlib import Path

from flask import current_app
from openai import OpenAI

from app.config import Config
from app.extensions import db
from app.models.analysis import AiAnalysis
from app.models.task import Task
from app.services.monitor_service import MonitorService
from app.services.task_service import TaskService
from app.utils.helpers import ApiError


MAX_CONTEXT_POINTS = 120

PROMPTS_DIR = Path(__file__).resolve().parent.parent / 'prompts'


def _load_prompt(filename: str) -> str:
    """从 prompts 目录加载提示词文件，去除首尾空白。"""
    path = PROMPTS_DIR / filename
    return path.read_text(encoding='utf-8').strip()


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
        task, execution_window, analysis = self._prepare_analysis(
            task_id,
            include_fio,
            include_host_monitor,
            include_disk_monitor,
            window_before_seconds,
            window_after_seconds,
        )
        return self._execute_analysis(
            task,
            analysis,
            execution_window,
            include_fio,
            include_host_monitor,
            include_disk_monitor,
        )

    @classmethod
    def submit_analysis(
        cls,
        task_id: int,
        include_fio: bool,
        include_host_monitor: bool,
        include_disk_monitor: bool,
        window_before_seconds: int = 30,
        window_after_seconds: int = 30,
    ) -> AiAnalysis:
        service = cls()
        task, execution_window, analysis = service._prepare_analysis(
            task_id,
            include_fio,
            include_host_monitor,
            include_disk_monitor,
            window_before_seconds,
            window_after_seconds,
        )

        app = current_app._get_current_object()
        worker = threading.Thread(
            target=cls._run_analysis_in_background,
            kwargs={
                'app': app,
                'analysis_id': analysis.id,
                'task_id': task.id,
                'execution_window': execution_window,
                'include_fio': include_fio,
                'include_host_monitor': include_host_monitor,
                'include_disk_monitor': include_disk_monitor,
            },
            daemon=True,
        )
        worker.start()
        return analysis

    def _prepare_analysis(
        self,
        task_id: int,
        include_fio: bool,
        include_host_monitor: bool,
        include_disk_monitor: bool,
        window_before_seconds: int,
        window_after_seconds: int,
    ) -> tuple[Task, dict, AiAnalysis]:
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

        return task, execution_window, analysis

    @classmethod
    def _run_analysis_in_background(
        cls,
        *,
        app,
        analysis_id: int,
        task_id: int,
        execution_window: dict,
        include_fio: bool,
        include_host_monitor: bool,
        include_disk_monitor: bool,
    ) -> None:
        with app.app_context():
            service = cls()
            analysis = AiAnalysis.query.get(analysis_id)
            task = Task.query.get(task_id)
            if analysis is None or task is None:
                return

            service._execute_analysis(
                task,
                analysis,
                execution_window,
                include_fio,
                include_host_monitor,
                include_disk_monitor,
            )

    def _execute_analysis(
        self,
        task: Task,
        analysis: AiAnalysis,
        execution_window: dict,
        include_fio: bool,
        include_host_monitor: bool,
        include_disk_monitor: bool,
    ) -> AiAnalysis:

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
        return _load_prompt('system_prompt.md')

    def _build_prompt(self, context: dict) -> str:
        template = _load_prompt('user_prompt_template.md')
        return template + '\n' + json.dumps(context, ensure_ascii=False, indent=2, default=str)

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
        """从 LLM 报告中提取结构化摘要。

        优先匹配结构化格式（性能评级章节），回退到关键词匹配以兼容旧格式报告。
        """
        # ── 1. 性能评级：优先从「## 性能评级」章节提取 ──
        rating = 'normal'
        rating_match = re.search(
            r'##\s*性能评级\s*\n\s*(excellent|good|normal|poor)',
            report,
            re.IGNORECASE,
        )
        if rating_match:
            rating = rating_match.group(1).lower()
        else:
            # 回退：关键词匹配（兼容旧格式报告）
            lowered = report.lower()
            if 'excellent' in lowered or '优秀' in report:
                rating = 'excellent'
            elif 'good' in lowered or '良好' in report:
                rating = 'good'
            elif 'poor' in lowered or '较差' in report or '异常' in report:
                rating = 'poor'

        # ── 2. 发现问题数：从「## 发现问题」章节统计列表项 ──
        issues_section = re.search(
            r'##\s*发现问题\s*\n(.*?)(?=\n##|\Z)',
            report,
            re.DOTALL,
        )
        if issues_section:
            issues_found = len(re.findall(r'^\s*-\s+', issues_section.group(1), re.MULTILINE))
        else:
            issues_found = report.count('- ')

        # ── 3. 优化建议数：从「## 优化建议」章节统计列表项 ──
        suggestions_section = re.search(
            r'##\s*优化建议\s*\n(.*?)(?=\n##|\Z)',
            report,
            re.DOTALL,
        )
        if suggestions_section:
            suggestions_count = len(re.findall(r'^\s*-\s+', suggestions_section.group(1), re.MULTILINE))
        else:
            lowered = report.lower()
            suggestions_count = report.count('建议') + lowered.count('suggest')

        return {
            'performance_rating': rating,
            'issues_found': issues_found,
            'suggestions_count': suggestions_count,
        }

    @staticmethod
    def get_latest(task_id: int) -> AiAnalysis | None:
        return AiAnalysis.query.filter_by(task_id=task_id).order_by(AiAnalysis.created_at.desc()).first()

    @staticmethod
    def get_history(task_id: int) -> list[AiAnalysis]:
        return AiAnalysis.query.filter_by(task_id=task_id).order_by(AiAnalysis.created_at.desc()).all()
