from src.rules.context_analyzer import ContextAnalyzer


def test_context_analyzer_accepts_custom_late_night_hours():
    analyzer = ContextAnalyzer(
        late_night_hours={10},
        elevated_fraud_categories=set(),
    )

    signals = analyzer.analyze(
        amount=100.0,
        hour=10,
        category="normal_category",
        prev_avg_amt=100.0,
        prev_5_avg_amt=100.0,
    )

    signal_names = [signal.name for signal in signals]

    assert "LATE_NIGHT_TRANSACTION" in signal_names


def test_context_analyzer_accepts_custom_fraud_categories():
    analyzer = ContextAnalyzer(
        late_night_hours=set(),
        elevated_fraud_categories={"custom_category"},
    )

    signals = analyzer.analyze(
        amount=100.0,
        hour=12,
        category="custom_category",
        prev_avg_amt=100.0,
        prev_5_avg_amt=100.0,
    )

    signal_names = [signal.name for signal in signals]

    assert "ELEVATED_FRAUD_CATEGORY" in signal_names