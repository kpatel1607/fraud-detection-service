# Real-Time Fraud Detection & Risk Assessment API

A production-oriented machine learning service for real-time transaction fraud scoring, behavioral anomaly detection, operational risk decisions, and human analyst review.

The system combines an XGBoost fraud classifier with persistent transaction history, configurable contextual rules, risk assessment, idempotent transaction processing, human review workflows, ground-truth evaluation, structured logging, and Docker deployment.

> **Dataset note:** The current model was trained and evaluated on a synthetic Kaggle credit-card transaction dataset. Model metrics therefore demonstrate the engineering and ML pipeline rather than real-world financial fraud performance.

---

## Overview

The service accepts a transaction and produces:

1. A machine-learning fraud probability
2. A model classification
3. A contextual risk assessment
4. An operational action
5. Human-readable risk reasons
6. Persistent behavioral history for future transactions

A simplified scoring flow is:

```text
Transaction
    │
    ▼
API validation
    │
    ▼
Idempotency check
    │
    ▼
Historical feature calculation
    │
    ▼
Feature construction
    │
    ▼
XGBoost prediction
    │
    ├── fraud probability
    │
    ▼
Risk Engine
    │
    ├── model thresholds
    ├── behavioral anomaly rules
    └── contextual signals
    │
    ▼
APPROVE / HUMAN_REVIEW / HOLD
    │
    ├── Transaction persistence
    ├── State update
    └── Review queue when required
```

---

## Key capabilities

* Real-time fraud probability scoring with XGBoost
* Persistent per-entity transaction history
* Behavioral features based on recent and historical spending
* Configurable contextual risk rules
* Separate ML prediction and operational risk decisions
* Human analyst review workflow
* Ground-truth collection after review
* TP/TN/FP/FN monitoring metrics
* Transaction idempotency
* Request IDs and structured logging
* Rotating log files
* API-key authentication
* Trusted-host validation
* Configurable CORS
* Production configuration validation
* Docker deployment
* Non-root container execution
* 87 automated tests covering the application and integration flows

---

# Machine Learning Model

The deployed model is an `XGBClassifier` using six features:

| Feature             | Description                                               |
| ------------------- | --------------------------------------------------------- |
| `amt`               | Current transaction amount                                |
| `hour`              | Hour of the transaction                                   |
| `category`          | Transaction category                                      |
| `prev_avg_amt`      | Historical average transaction amount                     |
| `prev_5_avg_amt`    | Average of the most recent five transactions              |
| `amt_ratio_recent5` | Current amount divided by recent five-transaction average |

The feature pipeline is separated from the model itself through a feature registry and model adapter.

### Model configuration

```text
max_depth              = 6
min_child_weight       = 5
subsample              = 0.8
learning_rate          = 0.05
colsample_bytree       = 0.8
n_estimators           = 1000
early_stopping_rounds  = 50
best_iteration         = 471
tree_method            = hist
```

### Validation results

The model was evaluated using a temporal validation split.

| Metric           | Result |
| ---------------- | -----: |
| PR-AUC           | 0.9695 |
| ROC-AUC          | 0.9994 |
| Precision @ 0.50 | 95.85% |
| Recall @ 0.50    | 87.36% |
| F1 @ 0.50        | 91.41% |

These metrics are specific to the current synthetic dataset and validation setup and should not be interpreted as production financial-fraud performance.

---

# Risk Decision System

The service deliberately separates the **ML prediction** from the **operational risk decision**.

The model produces a probability:

```text
fraud_probability
```

The risk engine then determines the operational response.

### Default thresholds

|     Probability | Risk level  | Action         |
| --------------: | ----------- | -------------- |
|        `< 0.40` | `LOW_RISK`  | `APPROVE`      |
| `0.40 – < 0.80` | `REVIEW`    | `HUMAN_REVIEW` |
|       `>= 0.80` | `HIGH_RISK` | `HOLD`         |

The thresholds are configurable through environment variables.

The risk engine can also use contextual signals such as:

* extreme deviation from recent spending
* extreme deviation from historical spending
* late-night transactions
* configured elevated-risk categories

A contextual anomaly can escalate a low ML-risk transaction into human review without changing the underlying model probability.

This keeps:

```text
ML prediction
```

separate from:

```text
Business / operational decision
```

which makes the system easier to audit and modify.

---

# Human Review Workflow

Transactions requiring review are stored in a persistent review queue.

```text
HUMAN_REVIEW
      │
      ▼
   PENDING
      │
      ▼
   Analyst
      │
      ├── CONFIRMED_FRAUD
      │
      └── LEGITIMATE
      │
      ▼
 Ground truth recorded
      │
      ▼
 TP / TN / FP / FN
```

The analyst's decision does **not** modify the original ML probability or model decision.

Instead, it creates ground-truth information that can be used to evaluate the system.

This allows the application to distinguish between:

* what the model predicted
* what the operational system did
* what an analyst ultimately determined

---

# API

## Authentication

Protected endpoints require:

```http
X-API-Key: <your-api-key>
```

The health endpoint does not require authentication.

---

## Health check

```http
GET /health
```

Example response:

```json
{
  "status": "ok",
  "service": "fraud-detection-api",
  "model_version": "1.1.0"
}
```

---

## Score a transaction

```http
POST /score
```

Required header:

```http
X-API-Key: <your-api-key>
```

Example request:

```json
{
  "transaction_id": "TXN_001",
  "entity_id": "CUSTOMER_001",
  "amount": 5000.0,
  "category": "shopping_net",
  "transaction_time": "2020-06-21T23:00:00"
}
```

Example response:

```json
{
  "transaction_id": "TXN_001",
  "fraud_probability": 0.06,
  "model_decision": "LEGITIMATE",
  "risk_level": "REVIEW",
  "action": "HUMAN_REVIEW",
  "reasons": [
    "Transaction amount is 90.9× the card's recent 5-transaction average.",
    "Transaction occurred during a late-night period."
  ],
  "amount": 5000.0,
  "hour": 23,
  "category": "shopping_net",
  "prev_avg_amt": 55.0,
  "prev_5_avg_amt": 55.0,
  "amt_ratio_recent5": 90.9090909091
}
```

The exact response values depend on the transaction's stored history and model prediction.

---

## View pending reviews

```http
GET /reviews/pending
```

Requires API authentication.

Returns the currently unresolved review items.

---

## Resolve a review

```http
POST /reviews/{transaction_id}/resolve
```

Example request:

```json
{
  "analyst_decision": "CONFIRMED_FRAUD",
  "analyst_reason": "Verified fraudulent transaction."
}
```

Supported analyst decisions:

```text
CONFIRMED_FRAUD
LEGITIMATE
```

Resolving a review records the resulting ground truth for monitoring.

---

## Monitoring metrics

```http
GET /monitoring/metrics
```

Example response:

```json
{
  "evaluated_transactions": 100,
  "true_positives": 40,
  "true_negatives": 50,
  "false_positives": 5,
  "false_negatives": 5,
  "precision": 0.8889,
  "recall": 0.8889,
  "f1_score": 0.8889,
  "accuracy": 0.9
}
```

Metrics are calculated only for transactions for which ground truth is available.

---

# Idempotency

Transaction scoring is idempotent using the transaction identifier.

If the same transaction is submitted again, the existing transaction result is returned rather than processing the transaction history a second time.

This prevents duplicate requests from incorrectly updating behavioral state multiple times.

For example:

```text
Request 1
TXN_001
    │
    ├── score
    ├── persist
    └── update history

Request 2
TXN_001
    │
    └── return existing result
```

This is particularly important for APIs where clients may retry requests after network failures.

---

# Project Architecture

```text
fraud_detection/
│
├── models/
│   ├── fraud_model_metadata.json
│   ├── fraud_preprocessor.joblib
│   └── fraud_xgb_model.json
│
├── notebooks/
│   └── 01_data_understanding.ipynb
│
├── src/
│   ├── adapters/
│   │   └── kaggle_fraud.py
│   │
│   ├── api/
│   │   ├── main.py
│   │   ├── schemas.py
│   │   └── security.py
│   │
│   ├── domain/
│   │   └── transaction.py
│   │
│   ├── features/
│   │   ├── canonical.py
│   │   ├── historical.py
│   │   └── state_store.py
│   │
│   ├── model/
│   │   ├── default_features.py
│   │   ├── feature_builder.py
│   │   ├── feature_registry.py
│   │   ├── model_adapter.py
│   │   ├── predictor.py
│   │   └── xgboost_adapter.py
│   │
│   ├── monitoring/
│   │   ├── evaluator.py
│   │   ├── metrics.py
│   │   └── outcomes.py
│   │
│   ├── review/
│   │   └── review_queue.py
│   │
│   ├── rules/
│   │   ├── context_analyzer.py
│   │   └── risk_engine.py
│   │
│   ├── services/
│   │   └── fraud_scoring.py
│   │
│   ├── storage/
│   │   └── transaction_store.py
│   │
│   ├── config.py
│   └── logging_config.py
│
├── tests/
│   ├── test_api.py
│   ├── test_full_system.py
│   ├── test_model.py
│   ├── test_risk_engine.py
│   ├── test_review_queue.py
│   └── ...
│
├── Dockerfile
├── requirements.txt
├── requirements-runtime.txt
├── .env.example
├── .gitignore
└── .dockerignore
```

---

# Design Principles

## Canonical transaction model

The application uses a universal transaction representation:

```python
CanonicalTransaction
```

with:

```text
transaction_id
entity_id
amount
category
transaction_time
```

Dataset-specific formats are translated into this representation through adapters.

For example, the current Kaggle dataset uses:

```text
cc_num
```

but the public application interface uses:

```text
entity_id
```

This prevents the core service from being tied to a particular dataset schema.

---

## Feature registry

Model features are registered independently from the feature builder.

This allows the model metadata to define:

```text
which features are required
```

while the feature registry defines:

```text
how those features are calculated
```

This reduces hard-coded feature construction inside the scoring service.

---

## Model adapter

The service uses a framework-independent model interface:

```python
ModelAdapter
```

The current implementation is:

```text
XGBoostModelAdapter
```

This keeps model-specific loading and prediction logic outside the main scoring workflow.

---

## Persistent behavioral state

Historical transaction information is stored in SQLite.

The current state tracks:

* transaction count
* total transaction amount
* average transaction amount
* recent transaction amounts
* last transaction time

This state is used to construct behavioral features for subsequent transactions.

---

# Configuration

Configuration is provided through environment variables.

Example:

```env
ENVIRONMENT=production

API_KEY=replace-with-a-long-random-secret

MODEL_PATH=models/fraud_xgb_model.json
PREPROCESSOR_PATH=models/fraud_preprocessor.joblib
MODEL_VERSION=1.1.0

STATE_DB_PATH=data/fraud_state.db
TRANSACTION_DB_PATH=data/transactions.db
REVIEW_DB_PATH=data/review_queue.db

REVIEW_THRESHOLD=0.40
HIGH_RISK_THRESHOLD=0.80

LATE_NIGHT_HOURS=22,23,0,1,2,3
ELEVATED_FRAUD_CATEGORIES=shopping_net,misc_net,grocery_pos

ALLOWED_HOSTS=your-domain.com
CORS_ORIGINS=https://your-frontend-domain.com

DOCS_ENABLED=false
```

Use `.env.example` as the configuration template.

Do not commit `.env` or `.env.production`.

---

# Running Locally

## 1. Clone the repository

```bash
git clone <repository-url>
cd fraud_detection
```

## 2. Create a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

## 3. Install dependencies

```powershell
pip install -r requirements.txt
```

## 4. Configure the environment

Copy the example configuration:

```powershell
Copy-Item .env.example .env
```

For local development, use a development API key and development settings.

## 5. Start the API

```powershell
uvicorn src.api.main:app --host 127.0.0.1 --port 8000
```

The API will be available at:

```text
http://127.0.0.1:8000
```

If API documentation is enabled:

```text
http://127.0.0.1:8000/docs
```

---

# Running Tests

Run the complete test suite:

```powershell
pytest -q
```

Current test status:

```text
87 passed
```

The suite covers:

* domain validation
* feature calculation
* feature registry
* model loading
* prediction
* risk rules
* state persistence
* transaction persistence
* review workflows
* monitoring metrics
* API validation
* authentication
* CORS
* trusted hosts
* idempotency
* complete transaction lifecycle

---

# Docker

The project includes a production-oriented Docker image.

Build:

```powershell
docker build -t fraud-detection-api:1.0.4 .
```

Run using local development configuration:

```powershell
docker run --rm --name fraud-detection-api `
  --env-file .env `
  -p 8000:8000 `
  -v "${PWD}\data:/app/data" `
  -v "${PWD}\logs:/app/logs" `
  fraud-detection-api:1.0.4
```

The container:

* uses a slim Python base image
* installs CPU-only XGBoost
* runs as a non-root user
* exposes port `8000`
* includes a health check
* persists SQLite data through a mounted volume
* persists logs through a mounted volume

Production configuration can be supplied using `.env.production`.

---

# Production Security Controls

The application includes several basic production safeguards.

### API authentication

Protected endpoints require an API key.

### Trusted hosts

Requests are restricted using Starlette's `TrustedHostMiddleware`.

### CORS

Allowed origins are explicitly configured.

### Production configuration validation

Production configuration rejects:

* the default development API key
* enabled API documentation

when `ENVIRONMENT=production`.

### Logging

Request logging includes:

* request ID
* HTTP method
* path
* status code
* latency

Transaction scoring logs include the transaction ID and scoring result but do not log the entity identifier.

### Container user

The Docker container runs as a dedicated non-root user.

---

# Monitoring and Feedback Loop

The service separates prediction from evaluation.

```text
Transaction
    │
    ▼
Model prediction
    │
    ▼
Operational decision
    │
    ▼
Human review
    │
    ▼
Ground truth
    │
    ▼
Evaluation
    │
    ├── Precision
    ├── Recall
    ├── F1
    ├── Accuracy
    └── TP / TN / FP / FN
```

This creates a foundation for future model monitoring and retraining workflows.

The current implementation does not automatically retrain the model from analyst feedback.

---

# Dataset and Model Limitations

The current model uses a synthetic fraud dataset.

Consequently:

* reported metrics are dataset-specific
* fraud patterns may not represent real financial transactions
* category and temporal relationships may contain synthetic artifacts
* model probabilities should not be interpreted as calibrated real-world fraud probabilities
* the current model has not been validated against production financial data
* the risk thresholds are application configuration rather than universally optimal fraud thresholds

The system architecture is designed so that the model, features, rules, and data adapter can be replaced without redesigning the entire service.

---

# Current Scope

The current implementation is intended as a portfolio-grade ML engineering system demonstrating:

* machine learning modeling
* feature engineering
* temporal validation
* model persistence
* API development
* stateful feature generation
* risk-rule integration
* human-in-the-loop workflows
* monitoring
* testing
* configuration management
* containerization

It is **not** intended to be deployed directly as a financial institution's production fraud platform without additional work around infrastructure, authentication, authorization, secrets management, database scalability, observability, model governance, calibration, drift detection, compliance, and high-availability architecture.

---

# Future Extensions

Potential future improvements include:

* model calibration
* probability threshold optimization based on business costs
* feature drift monitoring
* model drift monitoring
* automated retraining pipelines
* asynchronous scoring
* PostgreSQL-backed persistence
* Redis-based distributed state
* external authentication/authorization
* analyst dashboard
* alerting
* model registry integration
* CI/CD
* cloud deployment
* load testing
* distributed deployment

These are intentionally outside the current implementation so that the core scoring system remains understandable and testable.

---

## License

Add the project's chosen license here before publishing the repository.
