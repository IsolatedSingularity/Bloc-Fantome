"""The benchmark compares equivalent cold operations across repetitions."""

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))

from benchmark_large_world import measure


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
