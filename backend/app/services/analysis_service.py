from __future__ import annotations

import json
from datetime import datetime

from openai import OpenAI

from app.config import Config
from app.extensions import db
from app.models.analysis import AiAnalysis
from app.models.task import Task
from app.services.monitor_service import MonitorService
from app.utils.helpers import ApiError


class AnalysisService:
    def __init__(self):
        if not Config.AI_API_KEY:
            raise ApiError('VALIDATION_ERROR', '未配置 AI_API_KEY', 400)
        self.client = OpenAI(api_key=Config.AI_API_KEY, base_url=Config.AI_BASE_URL)
        self.model = Config.AI_MODEL

    def analyze(self, task_id: int, include_fio: bool, include_host_monitor: bool, include_disk_monitor: bool) -> AiAnalysis:
        task = Task.query.get(task_id)
        if not task:
            raise ApiError('NOT_FOUND', '任务不存在', 404)

        analysis = AiAnalysis(task_id=task_id, status='analyzing')
        db.session.add(analysis)
        db.session.commit()

        try:
            context = self._build_context(task, include_fio, include_host_monitor, include_disk_monitor)
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
            analysis.completed_at = datetime.utcnow()
            db.session.commit()
            return analysis
        except Exception as error:
            analysis.status = 'failed'
            analysis.error = str(error)
            db.session.commit()
            return analysis

    def _build_context(self, task: Task, include_fio: bool, include_host_monitor: bool, include_disk_monitor: bool) -> dict:
        context: dict = {'task': task.to_dict()}
        if include_fio:
            context['fio'] = {'config': task.config, 'result': task.result, 'device_path': task.device_path}
        if include_host_monitor:
            context['host_monitor'] = MonitorService.get_host_metrics(task.device_ip)
        if include_disk_monitor:
            disk_name = task.device_path.split('/')[-1]
            context['disk_monitor'] = MonitorService.get_disk_metrics(task.device_ip, disk_name)
        return context

    def _system_prompt(self) -> str:
        return (
            '你是一名专业的存储性能分析工程师和SSD测试专家。'
            '请基于给定的FIO结果、主机监控和磁盘监控数据，给出性能评估、疑点发现、优化建议和总结。'
        )

    def _build_prompt(self, context: dict) -> str:
        return '请分析以下 SSD 测试数据：\n' + json.dumps(context, ensure_ascii=False, indent=2, default=str)

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
