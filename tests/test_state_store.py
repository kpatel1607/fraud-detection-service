from src.features.state_store import EntityStateStore


def test_entity_state_can_be_saved_and_retrieved(tmp_path):
    db_path = tmp_path / "state.db"

    store = EntityStateStore(
        db_path=str(db_path)
    )

    store.upsert_entity(
        entity_id="ENTITY_001",
        transaction_count=2,
        total_amount=150.0,
        avg_amount=75.0,
        recent_amounts="[50.0, 100.0]",
        last_transaction_time="2026-09-15T10:00:00",
    )

    state = store.get_entity("ENTITY_001")

    assert state is not None
    assert state["cc_num"] == "ENTITY_001"
    assert state["transaction_count"] == 2
    assert state["total_amount"] == 150.0
    assert state["avg_amount"] == 75.0
    assert state["recent_amounts"] == "[50.0, 100.0]"
    assert state["last_transaction_time"] == "2026-09-15T10:00:00"


def test_missing_entity_returns_none(tmp_path):
    db_path = tmp_path / "state.db"

    store = EntityStateStore(
        db_path=str(db_path)
    )

    state = store.get_entity("DOES_NOT_EXIST")

    assert state is None


def test_entity_state_can_be_updated(tmp_path):
    db_path = tmp_path / "state.db"

    store = EntityStateStore(
        db_path=str(db_path)
    )

    store.upsert_entity(
        entity_id="ENTITY_001",
        transaction_count=1,
        total_amount=50.0,
        avg_amount=50.0,
        recent_amounts="[50.0]",
        last_transaction_time="2026-09-15T09:00:00",
    )

    store.upsert_entity(
        entity_id="ENTITY_001",
        transaction_count=2,
        total_amount=110.0,
        avg_amount=55.0,
        recent_amounts="[50.0, 60.0]",
        last_transaction_time="2026-09-15T10:00:00",
    )

    state = store.get_entity("ENTITY_001")

    assert state is not None
    assert state["transaction_count"] == 2
    assert state["total_amount"] == 110.0
    assert state["avg_amount"] == 55.0
    assert state["recent_amounts"] == "[50.0, 60.0]"