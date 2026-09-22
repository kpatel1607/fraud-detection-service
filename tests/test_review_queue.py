import json

from src.review.review_queue import ReviewQueue


def create_review(queue, transaction_id="txn_001"):
    queue.add_review(
        transaction_id=transaction_id,
        entity_id="CARD_001",
        amount=5000.0,
        category="shopping_net",
        transaction_time="2020-06-21T23:00:00",
        fraud_probability=0.10,
        risk_level="REVIEW",
        action="HUMAN_REVIEW",
        prev_avg_amt=100.0,
        prev_5_avg_amt=100.0,
        amt_ratio_recent5=50.0,
        reasons=[
            "Extreme behavioral anomaly.",
            "Late-night transaction.",
        ],
    )


def test_review_is_added_as_pending(tmp_path):
    queue = ReviewQueue(
        db_path=str(tmp_path / "review.db")
    )

    create_review(queue)

    pending = queue.get_pending_reviews()

    assert len(pending) == 1

    review = pending[0]

    assert review["transaction_id"] == "txn_001"
    assert review["status"] == "PENDING"
    assert review["fraud_probability"] == 0.10
    assert review["action"] == "HUMAN_REVIEW"

    reasons = json.loads(review["reasons"])

    assert "Extreme behavioral anomaly." in reasons


def test_review_can_be_resolved(tmp_path):
    queue = ReviewQueue(
        db_path=str(tmp_path / "review.db")
    )

    create_review(queue)

    resolved = queue.resolve_review(
        transaction_id="txn_001",
        analyst_decision="LEGITIMATE",
        analyst_reason="Manual verification found the transaction legitimate.",
    )

    assert resolved is not None
    assert resolved["status"] == "RESOLVED"
    assert resolved["analyst_decision"] == "LEGITIMATE"
    assert (
        resolved["analyst_reason"]
        == "Manual verification found the transaction legitimate."
    )
    assert resolved["reviewed_at"] is not None


def test_resolved_review_is_removed_from_pending(tmp_path):
    queue = ReviewQueue(
        db_path=str(tmp_path / "review.db")
    )

    create_review(queue)

    queue.resolve_review(
        transaction_id="txn_001",
        analyst_decision="CONFIRMED_FRAUD",
        analyst_reason="Manual verification confirmed fraud.",
    )

    pending = queue.get_pending_reviews()

    assert pending == []


def test_invalid_analyst_decision_is_rejected(tmp_path):
    queue = ReviewQueue(
        db_path=str(tmp_path / "review.db")
    )

    create_review(queue)

    try:
        queue.resolve_review(
            transaction_id="txn_001",
            analyst_decision="INVALID",
            analyst_reason="Invalid test decision.",
        )
        assert False, "Expected ValueError"
    except ValueError:
        pass