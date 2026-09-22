import pytest

from src.monitoring.metrics import calculate_metrics


def test_metrics_are_calculated_correctly():
    metrics = calculate_metrics(
        true_positives=80,
        true_negatives=900,
        false_positives=20,
        false_negatives=10,
    )

    assert metrics.true_positives == 80
    assert metrics.true_negatives == 900
    assert metrics.false_positives == 20
    assert metrics.false_negatives == 10

    assert metrics.precision == pytest.approx(
        80 / 100
    )

    assert metrics.recall == pytest.approx(
        80 / 90
    )

    assert metrics.f1_score == pytest.approx(
        2 * (80 / 100) * (80 / 90)
        / ((80 / 100) + (80 / 90))
    )

    assert metrics.accuracy == pytest.approx(
        (80 + 900) / 1010
    )


def test_zero_predictions_do_not_cause_division_error():
    metrics = calculate_metrics(
        true_positives=0,
        true_negatives=100,
        false_positives=0,
        false_negatives=0,
    )

    assert metrics.precision == 0.0
    assert metrics.recall == 0.0
    assert metrics.f1_score == 0.0
    assert metrics.accuracy == 1.0


def test_all_counts_zero():
    metrics = calculate_metrics(
        true_positives=0,
        true_negatives=0,
        false_positives=0,
        false_negatives=0,
    )

    assert metrics.precision == 0.0
    assert metrics.recall == 0.0
    assert metrics.f1_score == 0.0
    assert metrics.accuracy == 0.0


def test_negative_counts_are_rejected():
    with pytest.raises(ValueError):
        calculate_metrics(
            true_positives=-1,
            true_negatives=10,
            false_positives=2,
            false_negatives=1,
        )