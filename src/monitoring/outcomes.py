from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ClassificationOutcome:
    predicted: str
    actual: str
    label: str


def classify_outcome(
    predicted: str,
    actual: str,
) -> ClassificationOutcome:

    if predicted not in {"FRAUD", "LEGITIMATE"}:
        raise ValueError(
            "predicted must be 'FRAUD' or 'LEGITIMATE'"
        )

    if actual not in {"FRAUD", "LEGITIMATE"}:
        raise ValueError(
            "actual must be 'FRAUD' or 'LEGITIMATE'"
        )

    if predicted == "FRAUD" and actual == "FRAUD":
        label = "TP"

    elif predicted == "FRAUD" and actual == "LEGITIMATE":
        label = "FP"

    elif predicted == "LEGITIMATE" and actual == "FRAUD":
        label = "FN"

    else:
        label = "TN"

    return ClassificationOutcome(
        predicted=predicted,
        actual=actual,
        label=label,
    )