from src.model.feature_registry import FeatureRegistry


def test_feature_registry_registers_and_retrieves_provider():
    registry = FeatureRegistry()

    provider = lambda transaction, historical: 123.0

    registry.register("test_feature", provider)

    assert registry.has("test_feature")
    assert registry.get("test_feature") is provider


def test_feature_registry_returns_none_for_unknown_feature():
    registry = FeatureRegistry()

    assert not registry.has("unknown_feature")
    assert registry.get("unknown_feature") is None


def test_feature_registry_rejects_empty_feature_name():
    registry = FeatureRegistry()

    try:
        registry.register("", lambda transaction, historical: 1.0)
    except ValueError as exc:
        assert "Feature name cannot be empty" in str(exc)
    else:
        raise AssertionError(
            "Expected ValueError for empty feature name."
        )


def test_feature_registry_rejects_duplicate_provider():
    registry = FeatureRegistry()

    registry.register(
        "test_feature",
        lambda transaction, historical: 1.0,
    )

    try:
        registry.register(
            "test_feature",
            lambda transaction, historical: 2.0,
        )
    except ValueError as exc:
        assert "already registered" in str(exc)
    else:
        raise AssertionError(
            "Expected ValueError for duplicate feature provider."
        )