# Real-Time Fraud Detection & Risk Assessment API

A portfolio-grade machine learning engineering system for real-time fraud scoring, risk assessment, behavioral analysis, human analyst review, and transaction monitoring.

The project demonstrates how a fraud detection model can be integrated into a stateful API rather than treated as an isolated notebook experiment.

The repository currently contains **two independent fraud detection pipelines**:

1. **Credit-card transaction fraud detection** using a synthetic Kaggle dataset.
2. **Mobile-money transaction fraud detection** using the PaySim dataset.

Both pipelines share the same engineering principles while keeping their dataset-specific feature logic and models isolated.

> **Dataset note:** Both datasets used in this project are synthetic. The reported ML metrics demonstrate the modeling and engineering pipeline on those datasets and should not be interpreted as real-world financial fraud performance.

---

## Overview

The service combines machine learning with operational decision-making.

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
Dataset-specific feature construction
    │
    ▼
XGBoost prediction
    │
    ├── fraud probability
    │
    ▼
Risk policy / Risk Engine
    │
    ├── model decision
    ├── risk thresholds
    └── contextual signals where applicable
    │
    ▼
APPROVE / HUMAN_REVIEW / HOLD
    │
    ├── Transaction persistence
    ├── State update where applicable
    └── Review queue when required
```

The architecture deliberately separates:

```text
ML prediction
       ↓
Operational risk decision
       ↓
Human review
       ↓
Ground truth / evaluation
```

This makes the system easier to test, audit, and modify.

---

# Key Capabilities

* Real-time fraud probability scoring with XGBoost
* Two independent fraud detection pipelines
* Dataset-specific feature builders
* Persistent transaction state
* Behavioral feature generation
* Configurable operational risk thresholds
* Human-in-the-loop review workflows
* Ground-truth collection
* TP / TN / FP / FN evaluation
* Transaction idempotency
* Request IDs
* Structured logging
* Rotating log files
* API-key authentication
* Trusted-host validation
* Configurable CORS
* Production configuration validation
* Docker deployment
* Non-root container execution
* Automated test suite
* GitHub Actions CI
* Model and preprocessing artifacts stored separately from application logic

---

# Architecture

The project supports two scoring paths:

```text
                    ┌─────────────────────┐
                    │     FastAPI API     │
                    └──────────┬──────────┘
                               │
              ┌────────────────┴────────────────┐
              │                                 │
              ▼                                 ▼
       POST /score                       POST /score/paysim
              │                                 │
              ▼                                 ▼
    FraudScoringService                PaySimScoringService
              │                                 │
              ▼                                 ▼
       Kaggle feature                   PaySim feature
          pipeline                         pipeline
              │                                 │
              ▼                                 ▼
       Kaggle XGBoost                    PaySim XGBoost
              │                                 │
              └────────────────┬────────────────┘
                               │
                               ▼
                     Operational risk policy
                               │
                    ┌──────────┼──────────┐
                    ▼          ▼          ▼
                 APPROVE     REVIEW      HOLD
                               │
                               ▼
                         Review Queue
                               │
                               ▼
                          Ground Truth
                               │
                               ▼
                           Monitoring
```

The low-level model interface is shared through the model adapter abstraction, while dataset-specific feature construction remains isolated.

---

# Machine Learning Models

## 1. Credit-Card Fraud Model

The original fraud model was trained using a synthetic Kaggle credit-card transaction dataset.

### Features

The production scoring model uses six features:

| Feature             | Description                                                   |
| ------------------- | ------------------------------------------------------------- |
| `amt`               | Current transaction amount                                    |
| `hour`              | Hour of the transaction                                       |
| `category`          | Transaction category                                          |
| `prev_avg_amt`      | Historical average transaction amount                         |
| `prev_5_avg_amt`    | Average of the most recent five transactions                  |
| `amt_ratio_recent5` | Current amount divided by the recent five-transaction average |

Historical features are generated from persisted transaction state rather than from future information.

### Model configuration

```text
XGBClassifier

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

| Metric           | Result |
| ---------------- | -----: |
| PR-AUC           | 0.9695 |
| ROC-AUC          | 0.9994 |
| Precision @ 0.50 | 95.85% |
| Recall @ 0.50    | 87.36% |
| F1 @ 0.50        | 91.41% |

These results are specific to the synthetic Kaggle dataset and its validation setup.

---

# 2. PaySim Fraud Model

The second modeling experiment uses the **PaySim synthetic mobile-money transaction dataset**.

This model was added to determine whether the service architecture could support a materially different fraud domain without modifying the core scoring design.

## Dataset

```text
Transactions:       6,362,620
Fraudulent:             8,213
Fraud rate:            0.1291%
```

Transaction types:

| Type     | Approx. share |
| -------- | ------------: |
| CASH_OUT |        35.17% |
| PAYMENT  |        33.81% |
| CASH_IN  |        21.99% |
| TRANSFER |         8.38% |
| DEBIT    |         0.65% |

Fraud was observed only in:

* `TRANSFER`
* `CASH_OUT`

The other transaction types contained no fraud examples in the dataset.

---

## PaySim Feature Engineering

The final model uses:

```text
type
amount
oldbalanceOrg
oldbalanceDest
sender_balance_coverage
log_sender_amount_ratio
sender_balance_zero
destination_balance_zero
```

### Derived features

`sender_balance_coverage` represents how much of the sender's available balance the transaction consumes, capped at 1.

`log_sender_amount_ratio` is based on:

```text
amount / oldbalanceOrg
```

with logarithmic transformation to reduce the effect of extreme ratios.

Zero-balance indicators are also retained:

```text
sender_balance_zero
destination_balance_zero
```

### Features deliberately excluded

The PaySim model does **not** use:

* `newbalanceOrig`
* `newbalanceDest`
* `isFlaggedFraud`
* `nameOrig`
* `nameDest`
* `step`

Reasons:

* `newbalanceOrig` and `newbalanceDest` are post-transaction values and therefore introduce leakage into real-time prediction.
* `isFlaggedFraud` is an existing fraud-detection rule and would make the independent model evaluation less meaningful.
* `nameOrig` and `nameDest` are high-cardinality identifiers without useful sender history in this dataset.
* `step` was removed after ablation showed negligible improvement.

---

## PaySim Temporal Validation

The PaySim model uses a chronological split rather than a random split.

```text
Training:    steps 1–499
Validation:  steps 500–599
Test:        steps 600–743
```

Dataset sizes:

```text
Training:    6,055,699
Validation:    203,330
Test:          103,591
```

This prevents future transactions from influencing model training when evaluating earlier transactions.

The dataset also exhibited a significant temporal fraud-rate shift, making chronological evaluation particularly relevant.

---

## PaySim Model Configuration

```text
XGBClassifier

n_estimators         = 1000
learning_rate        = 0.05
max_depth            = 8
min_child_weight     = 5
subsample            = 0.8
colsample_bytree     = 0.8
tree_method          = hist
random_state         = 42
early_stopping       = 50
```

Hyperparameters were selected using **validation PR-AUC**.

The test set was reserved for final evaluation.

---

## PaySim Held-Out Test Results

Final test performance:

| Metric          |  Result |
| --------------- | ------: |
| PR-AUC          |  0.9939 |
| ROC-AUC         |  0.9999 |
| Precision       |  94.77% |
| Recall          |  99.69% |
| F1              |  97.17% |
| True Negatives  | 101,884 |
| False Positives |      89 |
| False Negatives |       5 |
| True Positives  |   1,613 |

The false-positive rate among legitimate test transactions was approximately:

```text
0.087%
```

The model detected:

```text
1,613 / 1,618
```

fraudulent test transactions.

These results demonstrate that the architecture can support a second fraud domain, but they should not be interpreted as evidence of equivalent performance on real mobile-money transactions.

---

# PaySim Error Analysis

The final PaySim test set contained five false negatives.

The errors were investigated individually rather than simply optimizing the model around them.

The false negatives included:

* one high-value `TRANSFER` transaction with a relatively small amount-to-origin-balance ratio
* several zero-amount `CASH_OUT` fraud examples

The zero-amount fraud cases had extremely small support in the dataset, so no hard-coded zero-amount fraud rule was introduced.

This avoids turning a dataset-specific anomaly into an unsupported production rule.

The false-positive analysis also showed substantial overlap between legitimate and fraudulent high-balance-coverage transactions.

Consequently, additional arbitrary rules were not added merely to improve the test confusion matrix.

---

# Risk Decision System

The service deliberately separates the **ML prediction** from the **operational risk decision**.

The model produces:

```text
fraud_probability
```

The operational policy then maps that probability to a risk level and action.

## Default thresholds

|     Probability | Risk level  | Action         |
| --------------: | ----------- | -------------- |
|        `< 0.40` | `LOW_RISK`  | `APPROVE`      |
| `0.40 – < 0.80` | `REVIEW`    | `HUMAN_REVIEW` |
|       `>= 0.80` | `HIGH_RISK` | `HOLD`         |

The thresholds are configurable through environment variables.

The model classification threshold is separate:

```text
fraud_probability >= 0.50
        ↓
model_decision = FRAUD
```

Therefore:

```text
Model decision ≠ Operational action
```

This distinction is intentional.

A transaction can have a low model fraud probability but still be escalated by contextual rules in the credit-card pipeline.

---

# PaySim Risk Policy

PaySim uses the same operational risk thresholds through the shared application configuration.

The PaySim scoring path therefore follows:

```text
PaySim transaction
       ↓
PaySim feature builder
       ↓
PaySim XGBoost model
       ↓
Fraud probability
       ↓
PaySim risk policy
       ↓
APPROVE / HUMAN_REVIEW / HOLD
```

During validation, the PaySim model produced a strongly bimodal score distribution.

The configured review band contained very few transactions.

The review population was **not artificially enlarged** simply to make the human-review architecture appear more active.

This preserves the behavior of the evaluated model rather than introducing an arbitrary threshold adjustment.

---

# Human Review Workflow

Transactions requiring human review are stored in a persistent review queue.

```text
HUMAN_REVIEW
      │
      ▼
   PENDING
      │
      ▼
   Analyst
      │
      ├── FRAUD
      │
      └── LEGITIMATE
      │
      ▼
Ground truth recorded
      │
      ▼
TP / TN / FP / FN
```

The analyst's decision does **not** modify the original model probability.

Instead, it creates ground-truth information that can be used to evaluate the system.

This allows the application to distinguish between:

```text
What the model predicted
        ↓
What the operational system did
        ↓
What the analyst determined
```

Both credit-card and PaySim pipelines have review workflow support.

---

# API

## Authentication

Protected endpoints require:

```http
X-API-Key: <your-api-key>
```

The health endpoint does not require authentication.

---

## Health Check

```http
GET /health
```

Example:

```json
{
  "status": "ok",
  "service": "fraud-detection-api",
  "model_version": "1.1.0"
}
```

---

# Credit-Card Scoring API

## Score a transaction

```http
POST /score
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

The service returns a fraud probability, model decision, risk level, action, and relevant feature information.

Example response:

```json
{
  "transaction_id": "TXN_001",
  "fraud_probability": 0.06,
  "model_decision": "LEGITIMATE",
  "risk_level": "REVIEW",
  "action": "HUMAN_REVIEW",
  "reasons": [
    "Transaction amount is significantly above the recent transaction average.",
    "Transaction occurred during a configured late-night period."
  ]
}
```

Exact values depend on the stored transaction history and model prediction.

---

## Credit-Card Review Queue

```http
GET /reviews/pending
```

Returns unresolved credit-card review items.

---

## Resolve Credit-Card Review

```http
POST /reviews/{transaction_id}/resolve
```

Supported outcomes include:

```text
FRAUD
LEGITIMATE
```

Resolving a review records ground truth for evaluation.

---

## Credit-Card Monitoring

```http
GET /monitoring/metrics
```

Metrics include:

```text
evaluated transactions
true positives
true negatives
false positives
false negatives
precision
recall
F1
accuracy
```

Metrics are calculated only for transactions with available ground truth.

---

# PaySim API

## Score a PaySim transaction

```http
POST /score/paysim
```

Example request:

```json
{
  "transaction_id": "PAYSIM_001",
  "transaction_type": "TRANSFER",
  "amount": 500000.0,
  "oldbalance_org": 500000.0,
  "oldbalance_dest": 0.0
}
```

Example high-risk response:

```json
{
  "transaction_id": "PAYSIM_001",
  "fraud_probability": 0.9985,
  "model_decision": "FRAUD",
  "risk_level": "HIGH_RISK",
  "action": "HOLD"
}
```

---

## PaySim Review Queue

```http
GET /reviews/paysim
```

Returns pending PaySim review items.

---

## Resolve PaySim Review

```http
POST /reviews/paysim/{transaction_id}/resolve
```

Supported outcomes:

```text
FRAUD
LEGITIMATE
```

---

## PaySim Monitoring

```http
GET /monitoring/paysim/metrics
```

Provides PaySim-specific ground-truth evaluation metrics.

---

# Idempotency

Transaction scoring is idempotent using the transaction identifier.

If the same transaction is submitted again, the existing transaction result is returned rather than processing the transaction history a second time.

```text
Request 1
TXN_001
    │
    ├── score
    ├── persist
    └── update state

Request 2
TXN_001
    │
    └── return existing result
```

This prevents retrying clients from accidentally updating behavioral state multiple times.

The same principle is applied to the PaySim scoring path.

---

# Project Structure

```text
fraud_detection/
│
├── models/
│   ├── fraud_model_metadata.json
│   ├── fraud_preprocessor.joblib
│   ├── fraud_xgb_model.json
│   │
│   └── paysim/
│       ├── metadata.json
│       ├── preprocessor.joblib
│       └── xgboost_model.json
│
├── notebooks/
│   ├── 01_data_understanding.ipynb
│   └── 02_paysim_data_understanding.ipynb
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
│   │   ├── transaction.py
│   │   └── paysim_transaction.py
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
│   │   ├── paysim_feature_builder.py
│   │   ├── paysim_predictor.py
│   │   ├── predictor.py
│   │   └── xgboost_adapter.py
│   │
│   ├── monitoring/
│   │   ├── evaluator.py
│   │   ├── metrics.py
│   │   ├── outcomes.py
│   │   └── paysim_evaluator.py
│   │
│   ├── review/
│   │   ├── review_queue.py
│   │   ├── paysim_review.py
│   │   └── paysim_review_queue.py
│   │
│   ├── rules/
│   │   ├── context_analyzer.py
│   │   ├── paysim_risk_policy.py
│   │   └── risk_engine.py
│   │
│   ├── services/
│   │   ├── fraud_scoring.py
│   │   └── paysim_scoring.py
│   │
│   ├── storage/
│   │   ├── transaction_store.py
│   │   └── paysim_transaction_store.py
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
│   ├── test_paysim_evaluator.py
│   ├── test_paysim_risk_policy.py
│   ├── test_paysim_scoring.py
│   └── ...
│
├── Dockerfile
├── requirements.txt
├── requirements-runtime.txt
├── .env.example
├── .gitignore
├── .dockerignore
└── README.md
```

---

# Design Principles

## Dataset-Specific Adapters

The original credit-card dataset contains dataset-specific fields such as:

```text
cc_num
```

The public application interface instead uses:

```text
entity_id
```

Dataset-specific translation is isolated in the adapter layer.

This prevents the core service from becoming tightly coupled to the original Kaggle dataset.

PaySim has its own domain model and feature builder rather than forcing mobile-money transactions into the credit-card feature schema.

---

## Feature Construction

The credit-card pipeline uses a feature registry and feature builder to separate:

```text
Which features are required
```

from:

```text
How those features are calculated
```

The PaySim pipeline uses its own feature builder because its fraud signals and transaction mechanics are fundamentally different.

This keeps the two modeling pipelines explicit rather than hiding dataset-specific assumptions inside generic code.

---

## Model Adapter

The application uses a model abstraction:

```python
ModelAdapter
```

with the current XGBoost implementation:

```text
XGBoostModelAdapter
```

Model loading and prediction logic therefore remain outside the main scoring workflow.

---

## Persistent State

The credit-card pipeline maintains persistent behavioral state used for historical features.

The current state includes information such as:

* transaction count
* total transaction amount
* average transaction amount
* recent transaction amounts
* last transaction time

The PaySim pipeline does not invent sender-history features because the PaySim dataset contains extremely high-cardinality sender identifiers with very limited repeated history.

This is an intentional example of allowing the dataset to determine which features are actually defensible.

---

# Leakage Prevention

The project explicitly considers information availability at prediction time.

For PaySim, post-transaction fields such as:

```text
newbalanceOrig
newbalanceDest
```

were excluded because they contain information that would only be available after the transaction.

Similarly, the existing:

```text
isFlaggedFraud
```

rule was excluded from the independent ML model.

This distinction is important when building fraud models intended for real-time use.

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

CORS_ORIGINS=["https://your-frontend-domain.com"]

DOCS_ENABLED=false
```

Use `.env.example` as the configuration template.

Do not commit:

```text
.env
.env.production
```

---

# Running Locally

## 1. Clone the repository

```powershell
git clone https://github.com/kpatel1607/fraud-detection-service.git

cd fraud-detection-service
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

# Testing

Run the complete test suite:

```powershell
python -m pytest -v -W error
```

Current verified status:

```text
109 passed
```

The suite covers:

* domain validation
* feature calculation
* feature registry
* model loading
* prediction
* PaySim prediction
* risk policies
* state persistence
* transaction persistence
* review workflows
* PaySim review workflows
* monitoring metrics
* API validation
* authentication
* CORS
* trusted hosts
* idempotency
* complete transaction lifecycle
* PaySim evaluation

---

# Continuous Integration

The project includes GitHub Actions CI.

The workflow:

```text
Push / Pull Request
        ↓
Ubuntu runner
        ↓
Python 3.12
        ↓
Install dependencies
        ↓
Run pytest
```

The test command used by CI is:

```powershell
python -m pytest -v -W error
```

This ensures that the application test suite is executed automatically on repository changes.

---

# Docker

The project includes a production-oriented Docker image.

Build:

```powershell
docker build -t fraud-detection-api:latest .
```

Run using local development configuration:

```powershell
docker run --rm --name fraud-detection-api `
  --env-file .env `
  -p 8000:8000 `
  -v "${PWD}\data:/app/data" `
  -v "${PWD}\logs:/app/logs" `
  fraud-detection-api:latest
```

The container:

* uses a slim Python base image
* installs CPU-oriented XGBoost dependencies
* runs as a non-root user
* exposes port `8000`
* includes a health check
* persists SQLite data through a mounted volume
* persists logs through a mounted volume

Production configuration can be supplied using:

```text
.env.production
```

---

# Production Security Controls

The application includes several basic security safeguards.

## API Authentication

Protected endpoints require an API key.

## Trusted Hosts

Requests are restricted using Starlette's:

```text
TrustedHostMiddleware
```

## CORS

Allowed origins are explicitly configured.

## Production Configuration Validation

Production configuration rejects unsafe defaults such as:

* the default development API key
* enabled API documentation

when:

```text
ENVIRONMENT=production
```

## Logging

Request logging includes:

* request ID
* HTTP method
* path
* status code
* latency

Transaction scoring logs include transaction identifiers and scoring results without logging the entity identifier.

## Container User

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

This provides the foundation for future:

* model monitoring
* drift detection
* calibration analysis
* retraining workflows

The current implementation does **not** automatically retrain models from analyst feedback.

---

# Dataset and Model Limitations

The project intentionally documents its limitations.

## Synthetic data

The Kaggle credit-card dataset and PaySim are synthetic datasets.

Therefore:

* reported metrics are dataset-specific
* fraud patterns may not represent real financial transactions
* synthetic temporal relationships may not match production behavior
* model probabilities should not be interpreted as calibrated real-world fraud probabilities
* the models have not been validated against production financial data

## Threshold limitations

The operational thresholds:

```text
0.40
0.80
```

are application configuration values rather than universally optimal fraud thresholds.

Threshold selection should ultimately depend on:

* fraud loss
* false-positive cost
* review capacity
* customer impact
* business risk tolerance

## Generalization

The PaySim experiment demonstrates that the service can support a second fraud domain without replacing the core architecture.

It does **not** prove that the same model features or thresholds should be transferred between domains.

---

# Current Scope

The current implementation is intended as a **portfolio-grade ML engineering system** demonstrating:

* machine learning modeling
* feature engineering
* temporal validation
* leakage prevention
* model persistence
* API development
* stateful feature generation
* dataset-specific model pipelines
* risk-rule integration
* human-in-the-loop workflows
* monitoring
* ground-truth evaluation
* testing
* configuration management
* containerization
* continuous integration

It is **not** intended to be deployed directly as a financial institution's production fraud platform without additional work around:

* scalable infrastructure
* authorization
* secrets management
* database scalability
* distributed state
* observability
* model calibration
* drift detection
* model governance
* compliance
* high availability
* disaster recovery
* load testing
* production security review

---

# Future Extensions

Potential future improvements include:

* probability calibration
* business-cost-based threshold optimization
* feature drift monitoring
* model drift monitoring
* automated retraining pipelines
* asynchronous scoring
* PostgreSQL-backed persistence
* Redis-based distributed state
* external authentication and authorization
* analyst dashboard
* alerting
* model registry integration
* cloud deployment
* load testing
* distributed deployment

These are intentionally outside the current implementation so that the core scoring system remains understandable and testable.

---

# Repository

GitHub:

https://github.com/kpatel1607/fraud-detection-service

---

## License

Add the project's chosen license before publishing the repository under a formal open-source license.
