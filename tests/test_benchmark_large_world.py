"""The benchmark compares equivalent cold operations across repetitions."""

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))

from benchmark_large_world import measure


def test_small_sample_p95_uses_nearest_rank_not_second_largest(monkeypatch):
    # Five cold runs cannot support a finely estimated tail percentile.
    ticks=iter((0, .001, 1, 1.002, 2, 2.003, 3, 3.004, 4, 4.100))
    monkeypatch.setattr('benchmark_large_world.time.perf_counter',lambda:next(ticks))
    result=measure(lambda:None)
    assert result['p95_ms']==result['max_ms']


def test_measure_runs_sample_setup_before_each_timed_operation():
    state = {"value": 0}
    observed = []

    def setup():
        state["value"] = 10

    def operation():
        observed.append(state["value"])
        state["value"] += 1

    result = measure(operation, repetitions=5, sample_setup=setup)

    assert observed == [10] * 5
    assert len(result["samples_ms"]) == 5
