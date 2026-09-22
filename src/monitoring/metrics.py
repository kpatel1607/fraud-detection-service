from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ClassificationMetrics:
    true_positives: int
    true_negatives: int
    false_positives: int
    false_negatives: int

    precision: float
    recall: float
    f1_score: float
    accuracy: float


def calculate_metrics(
    true_positives: int,
    true_negatives: int,
    false_positives: int,
    false_negatives: int,
) -> ClassificationMetrics:

    if min(
        true_positives,
        true_negatives,
        false_positives,
        false_negatives,
    ) < 0:
        raise ValueError(
            "Confusion-matrix counts cannot be negative."
        )

    total = (
        true_positives
        + true_negatives
        + false_positives
        + false_negatives
    )

    precision_denominator = (
        true_positives + false_positives
    )

    recall_denominator = (
        true_positives + false_negatives
    )

    precision = (
        true_positives / precision_denominator
        if precision_denominator
        else 0.0
    )

    recall = (
        true_positives / recall_denominator
        if recall_denominator
        else 0.0
    )

    f1_score = (
        2 * precision * recall / (precision + recall)
        if (precision + recall)
        else 0.0
    )

    accuracy = (
        (true_positives + true_negatives) / total
        if total
        else 0.0
    )

    return ClassificationMetrics(
        true_positives=true_positives,
        true_negatives=true_negatives,
        false_positives=false_positives,
        false_negatives=false_negatives,
        precision=precision,
        recall=recall,
        f1_score=f1_score,
        accuracy=accuracy,
    )