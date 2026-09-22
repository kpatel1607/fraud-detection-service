import pytest

from src.monitoring.outcomes import classify_outcome


def test_true_positive():
    result = classify_outcome(
        predicted="FRAUD",
        actual="FRAUD",
    )

    assert result.label == "TP"


def test_false_positive():
    result = classify_outcome(
        predicted="FRAUD",
        actual="LEGITIMATE",
    )

    assert result.label == "FP"


def test_false_negative():
    result = classify_outcome(
        predicted="LEGITIMATE",
        actual="FRAUD",
    )

    assert result.label == "FN"


def test_true_negative():
    result = classify_outcome(
        predicted="LEGITIMATE",
        actual="LEGITIMATE",
    )

    assert result.label == "TN"


def test_invalid_prediction_is_rejected():
    with pytest.raises(ValueError):
        classify_outcome(
            predicted="UNKNOWN",
            actual="FRAUD",
        )


def test_invalid_actual_outcome_is_rejected():
    with pytest.raises(ValueError):
        classify_outcome(
            predicted="FRAUD",
            actual="UNKNOWN",
        )