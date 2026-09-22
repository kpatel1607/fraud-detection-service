from __future__ import annotations

from datetime import UTC, datetime
import json
import sqlite3
from pathlib import Path
from typing import Any


class TransactionStore:
    def __init__(self, db_path: str = "data/transactions.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._initialize_database()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _migrate_database(self) -> None:
        required_columns = {
            "actual_outcome": "TEXT",
            "outcome_source": "TEXT",
            "outcome_reason": "TEXT",
            "outcome_at": "TEXT",
        }

        with self._connect() as conn:
            existing_columns = {
                row["name"]
                for row in conn.execute(
                    "PRAGMA table_info(transactions)"
                ).fetchall()
            }

            for column_name, column_type in required_columns.items():
                if column_name not in existing_columns:
                    conn.execute(
                        f"""
                        ALTER TABLE transactions
                        ADD COLUMN {column_name} {column_type}
                        """
                    )

            conn.commit()

    def _initialize_database(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS transactions (
                    transaction_id TEXT PRIMARY KEY,
                    cc_num TEXT NOT NULL,
                    amount REAL NOT NULL,
                    category TEXT NOT NULL,
                    transaction_time TEXT NOT NULL,
                    fraud_probability REAL NOT NULL,
                    model_decision TEXT NOT NULL,
                    risk_level TEXT NOT NULL,
                    action TEXT NOT NULL,
                    reasons TEXT NOT NULL,
                    prev_avg_amt REAL,
                    prev_5_avg_amt REAL,
                    amt_ratio_recent5 REAL,
                    created_at TEXT NOT NULL,
                    actual_outcome TEXT,
                    outcome_source TEXT,
                    outcome_reason TEXT,
                    outcome_at TEXT
                )
                """
            )

            conn.commit()

        self._migrate_database()

    def get_transaction(
        self,
        transaction_id: str,
    ) -> dict[str, Any] | None:

        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT *
                FROM transactions
                WHERE transaction_id = ?
                """,
                (transaction_id,),
            ).fetchone()

        if row is None:
            return None

        return dict(row)

    def save_transaction(
        self,
        *,
        transaction_id: str,
        entity_id: str,
        amount: float,
        category: str,
        transaction_time: str,
        fraud_probability: float,
        model_decision: str,
        risk_level: str,
        action: str,
        reasons: list[str],
        prev_avg_amt: float | None,
        prev_5_avg_amt: float | None,
        amt_ratio_recent5: float | None,
        created_at: str,
        actual_outcome: str | None = None,
        outcome_source: str | None = None,
        outcome_reason: str | None = None,
        outcome_at: str | None = None
    ) -> None:

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO transactions (
                    transaction_id,
                    cc_num,
                    amount,
                    category,
                    transaction_time,
                    fraud_probability,
                    model_decision,
                    risk_level,
                    action,
                    reasons,
                    prev_avg_amt,
                    prev_5_avg_amt,
                    amt_ratio_recent5,
                    created_at,
                    actual_outcome,
                    outcome_source,
                    outcome_reason,
                    outcome_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ? ,? ,?)
                """,
                (
                    transaction_id,
                    entity_id,
                    amount,
                    category,
                    transaction_time,
                    fraud_probability,
                    model_decision,
                    risk_level,
                    action,
                    json.dumps(reasons),
                    prev_avg_amt,
                    prev_5_avg_amt,
                    amt_ratio_recent5,
                    created_at,
                    actual_outcome,
                    outcome_source,
                    outcome_reason,
                    outcome_at,
                ),
            )

            conn.commit()
            
            
    def set_actual_outcome(
            self,
            transaction_id: str,
            actual_outcome: str,
        outcome_source: str,
        outcome_reason: str | None = None,
    ) -> dict | None:

        if actual_outcome not in {"FRAUD", "LEGITIMATE"}:
            raise ValueError(
                "actual_outcome must be 'FRAUD' or 'LEGITIMATE'"
            )

        if not outcome_source:
            raise ValueError(
                "outcome_source is required"
            )

        outcome_at = datetime.now(UTC).isoformat()

        with self._connect() as conn:
            cursor = conn.execute(
                """
                UPDATE transactions
                SET
                    actual_outcome = ?,
                    outcome_source = ?,
                    outcome_reason = ?,
                    outcome_at = ?
                WHERE transaction_id = ?
                """,
                (
                    actual_outcome,
                    outcome_source,
                    outcome_reason,
                    outcome_at,
                    transaction_id,
                ),
            )

            if cursor.rowcount == 0:
                return None

            row = conn.execute(
                """
                SELECT *
                FROM transactions
                WHERE transaction_id = ?
                """,
                (transaction_id,),
            ).fetchone()

        return dict(row)
    
    def get_evaluated_transactions(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    transaction_id,
                    model_decision,
                    actual_outcome,
                    outcome_source,
                    outcome_at
                FROM transactions
                WHERE actual_outcome IS NOT NULL
                ORDER BY outcome_at
                """
            ).fetchall()

        return [dict(row) for row in rows]