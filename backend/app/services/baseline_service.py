from app.extensions import db
from app.models.baseline import Baseline
from app.models.task import Task, TaskStatus
from app.utils.helpers import ApiError
from app.utils.logger import get_logger

logger = get_logger(__name__)


class BaselineService:
    @staticmethod
    def create(data: dict) -> Baseline:
        task = Task.query.get(data['task_id'])
        if not task or task.status != TaskStatus.SUCCESS:
            raise ApiError('VALIDATION_ERROR', '只能从成功任务创建基线', 400)

        baseline = Baseline(
            name=data['name'],
            device_model=data.get('device_model'),
            firmware=data.get('firmware'),
            fio_config=task.config,
            result=task.result,
            source_task_id=task.id,
            device_ip=task.device_ip,
            device_path=task.device_path,
        )
        db.session.add(baseline)
        db.session.commit()
        logger.info('Baseline %d created from task %d', baseline.id, task.id)
        return baseline

    @staticmethod
    def list(keyword: str | None = None, device_model: str | None = None,
             page: int = 1, page_size: int = 10) -> dict:
        query = Baseline.query
        if keyword:
            query = query.filter(Baseline.name.like(f'%{keyword}%'))
        if device_model:
            query = query.filter_by(device_model=device_model)
        pagination = query.order_by(Baseline.created_at.desc()).paginate(
            page=page, per_page=page_size, error_out=False,
        )
        return {
            'items': [b.to_dict() for b in pagination.items],
            'total': pagination.total,
        }

    @staticmethod
    def get(baseline_id: int) -> Baseline:
        baseline = Baseline.query.get(baseline_id)
        if not baseline:
            raise ApiError('NOT_FOUND', '基线不存在', 404)
        return baseline

    @staticmethod
    def delete(baseline_id: int) -> None:
        baseline = BaselineService.get(baseline_id)
        from app.models.regression_result import RegressionResult
        any_regressions = RegressionResult.query.filter(
            RegressionResult.baseline_id == baseline_id,
        ).first()
        if any_regressions:
            raise ApiError('CONFLICT', '该基线存在回归测试引用，无法删除', 409)
        db.session.delete(baseline)
        db.session.commit()
        logger.info('Baseline %d deleted', baseline_id)
