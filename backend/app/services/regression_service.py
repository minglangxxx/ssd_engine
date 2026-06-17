from app.extensions import db
from app.models.baseline import Baseline
from app.models.regression_result import RegressionResult
from app.models.task import Task, TaskStatus
from app.utils.helpers import ApiError
from app.utils.logger import get_logger

logger = get_logger(__name__)

THRESHOLD_TABLE = {
    'iops':     {'warning': -5,  'fail': -10},
    'bw':       {'warning': -5,  'fail': -10},
    'lat_mean': {'warning': 10,  'fail': 20},
    'lat_p99':  {'warning': 15,  'fail': 30},
}


def calc_diff_pct(baseline_val: float, current_val: float) -> float:
    if baseline_val == 0:
        return 0.0
    return (current_val - baseline_val) / baseline_val * 100


def judge_metric(diff_pct: float, metric_name: str) -> str:
    thresholds = THRESHOLD_TABLE[metric_name]
    if metric_name.startswith('lat'):
        if diff_pct > thresholds['fail']:
            return 'FAIL'
        if diff_pct > thresholds['warning']:
            return 'WARNING'
        return 'PASS'
    if diff_pct < thresholds['fail']:
        return 'FAIL'
    if diff_pct < thresholds['warning']:
        return 'WARNING'
    return 'PASS'


METRIC_UNIT = {
    'iops': '',
    'bw': 'MB/s',
    'lat_mean': 'us',
    'lat_p99': 'us',
}

METRIC_NAME_CN = {
    'iops': 'IOPS',
    'bw': '带宽',
    'lat_mean': '平均延迟',
    'lat_p99': 'P99延迟',
}


class RegressionService:
    @staticmethod
    def run(data: dict) -> RegressionResult:
        task = Task.query.get(data['task_id'])
        if not task or task.status != TaskStatus.SUCCESS:
            raise ApiError('VALIDATION_ERROR', '任务未完成，无法回归', 400)
        baseline = Baseline.query.get(data['baseline_id'])
        if not baseline:
            raise ApiError('NOT_FOUND', '基线不存在', 404)

        cur_result = task.result or {}
        base_result = baseline.result or {}

        # 宽松匹配：仅校验 rw 和 bs
        cur_rw = (cur_result.get('rw') or (task.config or {}).get('rw', '')).lower()
        base_rw = (base_result.get('rw') or (baseline.fio_config or {}).get('rw', '')).lower()
        cur_bs = (cur_result.get('bs') or (task.config or {}).get('bs', '4k')).lower()
        base_bs = (base_result.get('bs') or (baseline.fio_config or {}).get('bs', '4k')).lower()
        if cur_rw != base_rw or cur_bs != base_bs:
            raise ApiError('VALIDATION_ERROR', f'FIO 配置不匹配: rw={cur_rw}/{base_rw}, bs={cur_bs}/{base_bs}', 400)

        metrics_spec = [
            ('iops',     base_result.get('iops'),                     cur_result.get('iops')),
            ('bw',       base_result.get('bandwidth'),                cur_result.get('bandwidth')),
            ('lat_mean', base_result.get('latency', {}).get('mean'), cur_result.get('latency', {}).get('mean')),
            ('lat_p99',  base_result.get('latency', {}).get('p99'),  cur_result.get('latency', {}).get('p99')),
        ]

        detail_metrics = []
        worst_verdict = 'PASS'
        for name, base_val, cur_val in metrics_spec:
            if base_val is None or cur_val is None:
                continue
            diff_pct = round(calc_diff_pct(float(base_val), float(cur_val)), 2)
            v = judge_metric(diff_pct, name)
            if v == 'FAIL':
                worst_verdict = 'FAIL'
            elif v == 'WARNING' and worst_verdict != 'FAIL':
                worst_verdict = 'WARNING'
            detail_metrics.append({
                'name': name,
                'display_name': METRIC_NAME_CN.get(name, name),
                'baseline': base_val,
                'current': cur_val,
                'diff_pct': diff_pct,
                'verdict': v,
                'unit': METRIC_UNIT.get(name, ''),
            })

        iops_diff = next((m['diff_pct'] for m in detail_metrics if m['name'] == 'iops'), None)
        bw_diff = next((m['diff_pct'] for m in detail_metrics if m['name'] == 'bw'), None)
        lat_mean_diff = next((m['diff_pct'] for m in detail_metrics if m['name'] == 'lat_mean'), None)
        lat_p99_diff = next((m['diff_pct'] for m in detail_metrics if m['name'] == 'lat_p99'), None)

        result = RegressionResult(
            task_id=task.id,
            baseline_id=baseline.id,
            iops_diff=iops_diff,
            bw_diff=bw_diff,
            lat_mean_diff=lat_mean_diff,
            lat_p99_diff=lat_p99_diff,
            verdict=worst_verdict,
            detail={'metrics': detail_metrics},
        )
        db.session.add(result)
        db.session.commit()
        logger.info('Regression %d created: verdict=%s', result.id, worst_verdict)
        return result

    @staticmethod
    def get(regression_id: int) -> RegressionResult:
        result = RegressionResult.query.get(regression_id)
        if not result:
            raise ApiError('NOT_FOUND', '回归结果不存在', 404)
        return result

    @staticmethod
    def list(verdict: str | None = None, page: int = 1, page_size: int = 10) -> dict:
        query = RegressionResult.query
        if verdict:
            query = query.filter_by(verdict=verdict)
        pagination = query.order_by(RegressionResult.created_at.desc()).paginate(
            page=page, per_page=page_size, error_out=False,
        )
        return {
            'items': [r.to_dict() for r in pagination.items],
            'total': pagination.total,
        }
