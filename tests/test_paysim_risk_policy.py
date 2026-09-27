from src.rules.paysim_risk_policy import PaySimRiskPolicy


def test_low_risk_is_approved():
    policy = PaySimRiskPolicy()

    result = policy.assess(0.20)

    assert result.fraud_probability == 0.20
    assert result.risk_level == "LOW_RISK"
    assert result.action == "APPROVE"


def test_review_risk_requires_human_review():
    policy = PaySimRiskPolicy()

    result = policy.assess(0.60)

    assert result.fraud_probability == 0.60
    assert result.risk_level == "REVIEW"
    assert result.action == "HUMAN_REVIEW"


def test_high_risk_is_held():
    policy = PaySimRiskPolicy()

    result = policy.assess(0.90)

    assert result.fraud_probability == 0.90
    assert result.risk_level == "HIGH_RISK"
    assert result.action == "HOLD"