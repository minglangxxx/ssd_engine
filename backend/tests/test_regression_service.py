import pytest
from app.services.regression_service import calc_diff_pct, judge_metric


class TestCalcDiffPct:
    def test_positive_change(self):
        assert calc_diff_pct(100, 120) == 20.0

    def test_negative_change(self):
        assert calc_diff_pct(200, 180) == -10.0

    def test_zero_baseline(self):
        assert calc_diff_pct(0, 50) == 0.0

    def test_no_change(self):
        assert calc_diff_pct(100, 100) == 0.0

    def test_small_baseline(self):
        assert round(calc_diff_pct(1, 2), 2) == 100.0


class TestJudgeMetricIops:
    def test_pass(self):
        assert judge_metric(-3, 'iops') == 'PASS'

    def test_warning(self):
        assert judge_metric(-7, 'iops') == 'WARNING'

    def test_fail(self):
        assert judge_metric(-12, 'iops') == 'FAIL'

    def test_exact_warning_boundary(self):
        assert judge_metric(-5, 'iops') == 'PASS'

    def test_just_below_warning(self):
        assert judge_metric(-5.01, 'iops') == 'WARNING'

    def test_positive_is_pass(self):
        assert judge_metric(10, 'iops') == 'PASS'


class TestJudgeMetricBw:
    def test_pass(self):
        assert judge_metric(-3, 'bw') == 'PASS'

    def test_warning(self):
        assert judge_metric(-7, 'bw') == 'WARNING'

    def test_fail(self):
        assert judge_metric(-12, 'bw') == 'FAIL'


class TestJudgeMetricLatMean:
    def test_pass(self):
        assert judge_metric(8, 'lat_mean') == 'PASS'

    def test_warning(self):
        assert judge_metric(15, 'lat_mean') == 'WARNING'

    def test_fail(self):
        assert judge_metric(25, 'lat_mean') == 'FAIL'

    def test_negative_is_pass(self):
        assert judge_metric(-10, 'lat_mean') == 'PASS'

    def test_exact_fail_boundary(self):
        assert judge_metric(20, 'lat_mean') == 'WARNING'

    def test_just_above_fail(self):
        assert judge_metric(20.01, 'lat_mean') == 'FAIL'


class TestJudgeMetricLatP99:
    def test_pass(self):
        assert judge_metric(12, 'lat_p99') == 'PASS'

    def test_warning(self):
        assert judge_metric(20, 'lat_p99') == 'WARNING'

    def test_fail(self):
        assert judge_metric(35, 'lat_p99') == 'FAIL'

    def test_exact_warning_boundary(self):
        assert judge_metric(15, 'lat_p99') == 'PASS'

    def test_just_above_warning(self):
        assert judge_metric(15.01, 'lat_p99') == 'WARNING'

    def test_exact_fail_boundary(self):
        assert judge_metric(30, 'lat_p99') == 'WARNING'

    def test_just_above_fail(self):
        assert judge_metric(30.01, 'lat_p99') == 'FAIL'


class TestWorstVerdictLogic:
    def _run_service(self, metrics):
        """Simulate worst_verdict aggregation from RegressionService.run"""
        worst = 'PASS'
        for v in metrics:
            if v == 'FAIL':
                worst = 'FAIL'
            elif v == 'WARNING' and worst != 'FAIL':
                worst = 'WARNING'
        return worst

    def test_all_pass(self):
        assert self._run_service(['PASS', 'PASS', 'PASS']) == 'PASS'

    def test_one_warning(self):
        assert self._run_service(['PASS', 'WARNING', 'PASS']) == 'WARNING'

    def test_one_fail(self):
        assert self._run_service(['PASS', 'FAIL', 'PASS']) == 'FAIL'

    def test_warning_and_fail(self):
        assert self._run_service(['WARNING', 'FAIL']) == 'FAIL'

    def test_multiple_warnings(self):
        assert self._run_service(['WARNING', 'WARNING']) == 'WARNING'
