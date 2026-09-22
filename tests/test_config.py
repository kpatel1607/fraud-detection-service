import pytest

from src.config import Settings


def test_default_settings_are_valid():
    settings = Settings()

    assert settings.review_threshold == 0.40
    assert settings.high_risk_threshold == 0.80
    assert settings.model_version == "1.1.0"


def test_high_risk_threshold_must_be_greater():
    with pytest.raises(ValueError):
        Settings(
            review_threshold=0.80,
            high_risk_threshold=0.40,
        )


def test_thresholds_must_be_between_zero_and_one():
    with pytest.raises(ValueError):
        Settings(
            review_threshold=1.5,
            high_risk_threshold=0.80,
        )


def test_model_paths_are_exposed_as_path_objects():
    settings = Settings()

    assert settings.model_file.name == (
        "fraud_xgb_model.json"
    )

    assert settings.preprocessor_file.name == (
        "fraud_preprocessor.joblib"
    )


def test_environment_values_are_loaded(monkeypatch):
    monkeypatch.setenv(
        "REVIEW_THRESHOLD",
        "0.30",
    )

    monkeypatch.setenv(
        "HIGH_RISK_THRESHOLD",
        "0.75",
    )

    settings = Settings(
        _env_file=None,
    )

    assert settings.review_threshold == 0.30
    assert settings.high_risk_threshold == 0.75
    
    
def test_production_cannot_use_default_api_key():
    with pytest.raises(
        ValueError,
        match="Production environment cannot use the default development API key",
    ):
        Settings(
            _env_file=None,
            environment="production",
            api_key="dev-api-key-change-me",
            docs_enabled=False,
        )


def test_production_must_disable_docs():
    with pytest.raises(
        ValueError,
        match="API docs must be disabled in production",
    ):
        Settings(
            _env_file=None,
            environment="production",
            api_key="real-production-secret",
            docs_enabled=True,
        )


def test_valid_production_settings():
    settings = Settings(
        _env_file=None,
        environment="production",
        api_key="real-production-secret",
        docs_enabled=False,
        allowed_hosts="api.example.com",
        cors_origins="https://app.example.com",
    )

    assert settings.environment == "production"
    assert settings.docs_enabled is False
    
    
def test_context_rule_settings_have_expected_defaults():
    settings = Settings()

    assert settings.late_night_hours == "22,23,0,1,2,3"
    assert (
        settings.elevated_fraud_categories
        == "shopping_net,misc_net,grocery_pos"
    )


def test_context_rule_settings_can_be_overridden(monkeypatch):
    monkeypatch.setenv(
        "LATE_NIGHT_HOURS",
        "20,21,22",
    )
    monkeypatch.setenv(
        "ELEVATED_FRAUD_CATEGORIES",
        "electronics,travel",
    )

    settings = Settings()

    assert settings.late_night_hours == "20,21,22"
    assert settings.elevated_fraud_categories == "electronics,travel"
    
def test_context_rule_settings_are_parsed_into_sets():
    settings = Settings(
        late_night_hours="20,21,22",
        elevated_fraud_categories="electronics,travel",
    )

    assert settings.late_night_hour_set == {20, 21, 22}
    assert settings.elevated_fraud_category_set == {
        "electronics",
        "travel",
    }