from __future__ import annotations

from datetime import UTC, datetime
import sqlite3
from pathlib import Path
from typing import Any


class PaySimTransactionStore:
    """
    Persistent store for scored PaySim transactions.

    This is separate from the card TransactionStore because
    PaySim has different transaction fields and semantics.
    """

    def __init__(
        self,
        db_path: str = "data/paysim_transactions.db",
    ):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._initialize_database()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _initialize_database(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS paysim_transactions (
                    transaction_id TEXT PRIMARY KEY,
                    transaction_type TEXT NOT NULL,

                    amount REAL NOT NULL,
                    oldbalance_org REAL NOT NULL,
                    oldbalance_dest REAL NOT NULL,

                    fraud_probability REAL NOT NULL,
                    model_decision TEXT NOT NULL,
                    risk_level TEXT NOT NULL,
                    action TEXT NOT NULL,

                    created_at TEXT NOT NULL,

                    actual_outcome TEXT,
                    outcome_source TEXT,
                    outcome_reason TEXT,
                    outcome_at TEXT
                )
                """
            )

            conn.commit()

    def get_transaction(
        self,
        transaction_id: str,
    ) -> dict[str, Any] | None:

        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT *
                FROM paysim_transactions
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
        transaction_type: str,
        amount: float,
        oldbalance_org: float,
        oldbalance_dest: float,
        fraud_probability: float,
        model_decision: str,
        risk_level: str,
        action: str,
        created_at: str,
    ) -> None:

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO paysim_transactions (
                    transaction_id,
                    transaction_type,
                    amount,
                    oldbalance_org,
                    oldbalance_dest,
                    fraud_probability,
                    model_decision,
                    risk_level,
                    action,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    transaction_id,
                    transaction_type,
                    amount,
                    oldbalance_org,
                    oldbalance_dest,
                    fraud_probability,
                    model_decision,
                    risk_level,
                    action,
                    created_at,
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

        if actual_outcome not in {
            "FRAUD",
            "LEGITIMATE",
        }:
            raise ValueError(
                "actual_outcome must be "
                "'FRAUD' or 'LEGITIMATE'"
            )

        if not outcome_source:
            raise ValueError(
                "outcome_source is required"
            )

        outcome_at = datetime.now(UTC).isoformat()

        with self._connect() as conn:
            cursor = conn.execute(
                """
                UPDATE paysim_transactions
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
                FROM paysim_transactions
                WHERE transaction_id = ?
                """,
                (transaction_id,),
            ).fetchone()

        return dict(row)

    def get_evaluated_transactions(
        self,
    ) -> list[dict]:

        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    transaction_id,
                    model_decision,
                    actual_outcome,
                    outcome_source,
                    outcome_at
                FROM paysim_transactions
                WHERE actual_outcome IS NOT NULL
                ORDER BY outcome_at
                """
            ).fetchall()

        return [dict(row) for row in rows]