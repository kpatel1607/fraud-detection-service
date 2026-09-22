from fastapi.testclient import TestClient

from src.api.main import create_app
from src.config import Settings


def create_test_client(tmp_path):
    settings = Settings(
        api_key="test-secret-key",
        allowed_hosts="testserver,localhost,127.0.0.1",
        state_db_path=str(tmp_path / "state.db"),
        transaction_db_path=str(tmp_path / "transactions.db"),
        review_db_path=str(tmp_path / "review.db"),
    )

    app = create_app(settings)

    return TestClient(app)


def test_health(tmp_path):
    client = create_test_client(tmp_path)

    response = client.get("/health")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "ok"
    assert data["service"] == "fraud-detection-api"
    assert data["model_version"] == "1.1.0"


def test_score_cold_start(tmp_path):
    client = create_test_client(tmp_path)
    response = client.post(
        "/score",
        headers={
            "X-API-Key": "test-secret-key",
        },
        json={
            "transaction_id": "api_pytest_001",
            "entity_id": "API_PYTEST_CARD_001",
            "amount": 50.0,
            "category": "grocery_pos",
            "transaction_time": "2020-06-21T12:00:00",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["transaction_id"] == "api_pytest_001"
    assert 0.0 <= data["fraud_probability"] <= 1.0
    assert data["model_decision"] == "LEGITIMATE"
    assert data["action"] == "APPROVE"

    assert data["prev_avg_amt"] is None
    assert data["prev_5_avg_amt"] is None
    assert data["amt_ratio_recent5"] is None


def test_invalid_amount_is_rejected(tmp_path):
    client = create_test_client(tmp_path)
    response = client.post(
        "/score",
        headers={
            "X-API-Key": "test-secret-key",
        },
        json={
            "transaction_id": "api_pytest_invalid_001",
            "entity_id": "API_PYTEST_CARD_002",
            "amount": -100.0,
            "category": "grocery_pos",
            "transaction_time": "2020-06-21T12:00:00",
        },
    )

    assert response.status_code == 422


def test_missing_required_field_is_rejected(tmp_path):
    client = create_test_client(tmp_path)
    response = client.post(
        "/score",
        headers={
            "X-API-Key": "test-secret-key",
        },
        json={
            "transaction_id": "api_pytest_invalid_002",
            "entity_id": "API_PYTEST_CARD_003",
            "amount": 50.0,
            "category": "grocery_pos",
        },
    )

    assert response.status_code == 422


def test_score_and_duplicate_are_idempotent(tmp_path):
    client = create_test_client(tmp_path)
    payload = {
        "transaction_id": "api_pytest_duplicate_001",
        "entity_id": "API_PYTEST_CARD_004",
        "amount": 50.0,
        "category": "grocery_pos",
        "transaction_time": "2020-06-21T12:00:00",
    }

    first_response = client.post(
        "/score",
        headers={
            "X-API-Key": "test-secret-key",
        },
        json=payload,
    )

    second_response = client.post(
        "/score",
        headers={
            "X-API-Key": "test-secret-key",
        },
        json=payload,
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    assert second_response.json() == first_response.json()


def test_review_workflow(tmp_path):
    client = create_test_client(tmp_path)
    score_response = client.post(
        "/score",
        headers={
            "X-API-Key": "test-secret-key",
        },
        json={
            "transaction_id": "api_pytest_review_001",
            "entity_id": "API_PYTEST_CARD_005",
            "amount": 5000.0,
            "category": "shopping_net",
            "transaction_time": "2020-06-21T23:00:00",
        },
    )

    assert score_response.status_code == 200

    score_data = score_response.json()

    assert score_data["action"] == "HUMAN_REVIEW"

    pending_response = client.get(
        "/reviews/pending",
        headers={
            "X-API-Key": "test-secret-key",
        }
    )

    assert pending_response.status_code == 200

    pending = pending_response.json()

    matching_reviews = [
        review
        for review in pending
        if review["transaction_id"] == "api_pytest_review_001"
    ]

    assert len(matching_reviews) == 1
    assert matching_reviews[0]["entity_id"] == "API_PYTEST_CARD_005"
    assert "cc_num" not in matching_reviews[0]

    resolve_response = client.post(
        "/reviews/api_pytest_review_001/resolve",
        headers={
            "X-API-Key": "test-secret-key",
        },
        json={
            "analyst_decision": "LEGITIMATE",
            "analyst_reason": "Automated API test resolution.",
        },
    )

    assert resolve_response.status_code == 200

    resolved = resolve_response.json()

    assert resolved["status"] == "RESOLVED"
    assert resolved["analyst_decision"] == "LEGITIMATE"
    assert resolved["entity_id"] == "API_PYTEST_CARD_005"
    assert "cc_num" not in resolved
    assert (
        resolved["analyst_reason"]
        == "Automated API test resolution."
    )


def test_invalid_analyst_decision_is_rejected(tmp_path):
    client = create_test_client(tmp_path)
    response = client.post(
        "/reviews/nonexistent_transaction/resolve",
        headers={
            "X-API-Key": "test-secret-key",
        },
        json={
            "analyst_decision": "INVALID",
            "analyst_reason": "Invalid decision test.",
        },
    )

    assert response.status_code == 422
    
def test_monitoring_metrics_with_no_labels(tmp_path):
    client = create_test_client(tmp_path)

    response = client.get(
        "/monitoring/metrics",
        headers={
            "X-API-Key": "test-secret-key",
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert data["evaluated_transactions"] == 0

    assert data["true_positives"] == 0
    assert data["true_negatives"] == 0
    assert data["false_positives"] == 0
    assert data["false_negatives"] == 0

    assert data["precision"] == 0.0
    assert data["recall"] == 0.0
    assert data["f1_score"] == 0.0
    assert data["accuracy"] == 0.0
    
def test_monitoring_metrics_after_review_resolution(tmp_path):
    client = create_test_client(tmp_path)

    score_response = client.post(
        "/score",
        headers={
            "X-API-Key": "test-secret-key",
        },
        json={
            "transaction_id": "api_metrics_001",
            "entity_id": "API_METRICS_CARD_001",
            "amount": 5000.0,
            "category": "shopping_net",
            "transaction_time": "2020-06-21T23:00:00",
        },
    )

    assert score_response.status_code == 200
    assert score_response.json()["action"] == "HUMAN_REVIEW"

    resolve_response = client.post(
        "/reviews/api_metrics_001/resolve",
        headers={
            "X-API-Key": "test-secret-key",
        },
        json={
            "analyst_decision": "CONFIRMED_FRAUD",
            "analyst_reason": "Test analyst confirmation.",
        },
    )

    assert resolve_response.status_code == 200

    metrics_response = client.get(
        "/monitoring/metrics",
        headers={
            "X-API-Key": "test-secret-key",
        }
    )

    assert metrics_response.status_code == 200

    data = metrics_response.json()

    assert data["evaluated_transactions"] == 1
    assert data["true_positives"] == 1
    assert data["true_negatives"] == 0
    assert data["false_positives"] == 0
    assert data["false_negatives"] == 0

    assert data["precision"] == 1.0
    assert data["recall"] == 1.0
    assert data["f1_score"] == 1.0
    assert data["accuracy"] == 1.0
    
def test_score_requires_api_key(tmp_path):
    client = create_test_client(tmp_path)

    response = client.post(
        "/score",
        json={
            "transaction_id": "security_test_001",
            "entity_id": "SECURITY_CARD_001",
            "amount": 50.0,
            "category": "grocery_pos",
            "transaction_time": "2020-06-21T12:00:00",
        },
    )

    assert response.status_code == 401


def test_score_rejects_invalid_api_key(tmp_path):
    client = create_test_client(tmp_path)

    response = client.post(
        "/score",
        headers={"X-API-Key": "wrong-key"},
        json={
            "transaction_id": "security_test_002",
            "entity_id": "SECURITY_CARD_002",
            "amount": 50.0,
            "category": "grocery_pos",
            "transaction_time": "2020-06-21T12:00:00",
        },
    )

    assert response.status_code == 403
    
    
def test_invalid_host_is_rejected(tmp_path):
    client = create_test_client(tmp_path)

    response = client.get(
        "/health",
        headers={
            "Host": "malicious.example.com",
        },
    )

    assert response.status_code == 400
    
def test_valid_host_is_allowed(tmp_path):
    client = create_test_client(tmp_path)

    response = client.get(
        "/health",
        headers={
            "Host": "testserver",
        },
    )

    assert response.status_code == 200
    
def test_allowed_cors_origin(tmp_path):
    client = create_test_client(tmp_path)

    response = client.get(
        "/health",
        headers={
            "Origin": "http://localhost:3000",
        },
    )

    assert response.status_code == 200
    assert (
        response.headers["access-control-allow-origin"]
        == "http://localhost:3000"
    )
    
def test_disallowed_cors_origin(tmp_path):
    client = create_test_client(tmp_path)

    response = client.get(
        "/health",
        headers={
            "Origin": "https://malicious.example.com",
        },
    )

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers
    
def test_docs_enabled_by_default(tmp_path):
    client = create_test_client(tmp_path)

    response = client.get("/docs")

    assert response.status_code == 200
    
def test_docs_can_be_disabled(tmp_path):
    settings = Settings(
        api_key="test-secret-key",
        docs_enabled=False,
        allowed_hosts="testserver",
        state_db_path=str(tmp_path / "state.db"),
        transaction_db_path=str(tmp_path / "transactions.db"),
        review_db_path=str(tmp_path / "review.db"),
    )

    app = create_app(settings)
    client = TestClient(app)

    response = client.get("/docs")

    assert response.status_code == 404