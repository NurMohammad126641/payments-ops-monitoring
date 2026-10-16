import math

from opsmon.anomaly import detect


def test_flags_rows_above_ratio_and_min_count():
    rows = [("ROCKET", 150, 2.5), ("NAGAD", 30, 25.0), ("BKASH", 3, 0.5)]

    found = detect("not_success_spike", rows, ratio=1.5, min_count=20)

    assert [a.key for a in found] == ["ROCKET"]
    assert found[0].severity == "critical"
    assert found[0].ratio == 60.0


def test_warning_between_ratio_and_twice_ratio():
    found = detect("rule", [("NPSB", 40, 20)], ratio=1.5, min_count=20)

    assert len(found) == 1
    assert found[0].severity == "warning"
    assert found[0].ratio == 2.0


def test_small_counts_are_ignored_even_with_no_baseline():
    assert detect("rule", [("VISA", 5, 0)], ratio=1.5, min_count=20) == []


def test_missing_baseline_is_critical_and_described_as_new():
    found = detect("rule", [("VISA", 25, None)], ratio=1.5, min_count=20)

    assert found[0].severity == "critical"
    assert math.isinf(found[0].ratio)
    assert "new" in found[0].describe()


def test_results_are_sorted_by_ratio_descending():
    rows = [("A", 30, 15), ("B", 90, 10), ("C", 45, 15)]

    found = detect("rule", rows, ratio=1.5, min_count=20)

    assert [a.key for a in found] == ["B", "C", "A"]
