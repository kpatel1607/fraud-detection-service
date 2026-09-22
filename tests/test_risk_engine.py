from src.rules.risk_engine import RiskEngine


def test_low_risk_normal_transaction():
    engine = RiskEngine(
        review_threshold=0.40,
        high_risk_threshold=0.80,
        late_night_hours={22, 23, 0, 1, 2, 3},
        elevated_fraud_categories={
            "shopping_net",
            "misc_net",
            "grocery_pos",
        },
    )

    result = engine.assess(
        fraud_probability=0.10,
        amount=50.0,
        hour=12,
        category="grocery_pos",
        prev_avg_amt=None,
        prev_5_avg_amt=None,
    )

    assert result.risk_level == "LOW_RISK"
    assert result.action == "APPROVE"


def test_extreme_behavioral_anomaly_escalates():
    engine = RiskEngine(
        review_threshold=0.40,
        high_risk_threshold=0.80,
        late_night_hours={22, 23, 0, 1, 2, 3},
        elevated_fraud_categories={
            "shopping_net",
            "misc_net",
            "grocery_pos",
        },
    )

    result = engine.assess(
        fraud_probability=0.06,
        amount=5000.0,
        hour=23,
        category="shopping_net",
        prev_avg_amt=50.0,
        prev_5_avg_amt=50.0,
    )

    assert result.risk_level == "REVIEW"
    assert result.action == "HUMAN_REVIEW"

    assert any(
        "extreme behavioral anomaly" in reason.lower()
        for reason in result.reasons
    )


def test_high_model_probability_creates_hold():
    engine = RiskEngine(
        review_threshold=0.40,
        high_risk_threshold=0.80,
        late_night_hours={22, 23, 0, 1, 2, 3},
        elevated_fraud_categories={
            "shopping_net",
            "misc_net",
            "grocery_pos",
        },
    )

    result = engine.assess(
        fraud_probability=0.95,
        amount=500.0,
        hour=14,
        category="shopping_net",
        prev_avg_amt=100.0,
        prev_5_avg_amt=100.0,
    )

    assert result.risk_level == "HIGH_RISK"
    assert result.action == "HOLD"
    
def test_risk_engine_uses_custom_context_rules():
    engine = RiskEngine(
        review_threshold=0.40,
        high_risk_threshold=0.80,
        late_night_hours={10},
        elevated_fraud_categories={"custom_category"},
    )

    assessment = engine.assess(
        fraud_probability=0.10,
        amount=100.0,
        hour=10,
        category="custom_category",
        prev_avg_amt=100.0,
        prev_5_avg_amt=100.0,
    )

    assert any(
        "late-night" in reason.lower()
        for reason in assessment.reasons
    )

    assert any(
        "custom_category" in reason
        for reason in assessment.reasons
    )
    
def test_risk_engine_requires_context_rules():
    try:
        RiskEngine(
            review_threshold=0.40,
            high_risk_threshold=0.80,
        )
    except ValueError as exc:
        assert "late_night_hours" in str(exc)
    else:
        raise AssertionError(
            "RiskEngine should require context rules."
        )