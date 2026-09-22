from __future__ import annotations

from datetime import UTC, datetime
import json
import sqlite3
from pathlib import Path
from typing import Optional

from src.storage.transaction_store import TransactionStore


class ReviewQueue:
    """
    Persistent queue for transactions that require human review.
    """

    def __init__(
        self,
        db_path: str = "data/review_queue.db",
        transaction_store: TransactionStore | None = None,
    ):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.transaction_store = transaction_store

        self._initialize_database()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)

        conn.row_factory = sqlite3.Row

        return conn

    def _initialize_database(self) -> None:
        """
        Create the review queue table if it doesn't exist.
        """

        with self._connect() as conn:

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS review_queue (
                    review_id INTEGER PRIMARY KEY AUTOINCREMENT,

                    transaction_id TEXT NOT NULL UNIQUE,
                    cc_num TEXT NOT NULL,

                    amount REAL NOT NULL,
                    category TEXT NOT NULL,
                    transaction_time TEXT NOT NULL,

                    fraud_probability REAL NOT NULL,
                    risk_level TEXT NOT NULL,
                    action TEXT NOT NULL,

                    prev_avg_amt REAL,
                    prev_5_avg_amt REAL,
                    amt_ratio_recent5 REAL,

                    reasons TEXT NOT NULL,

                    status TEXT NOT NULL DEFAULT 'PENDING',

                    analyst_decision TEXT,
                    analyst_reason TEXT,

                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    reviewed_at TEXT
                )
                """
            )

            conn.commit()

    def add_review(
        self,
        transaction_id: str,
        entity_id: str,
        amount: float,
        category: str,
        transaction_time: str,
        fraud_probability: float,
        risk_level: str,
        action: str,
        prev_avg_amt: Optional[float],
        prev_5_avg_amt: Optional[float],
        amt_ratio_recent5: Optional[float],
        reasons: list[str],
    ) -> None:
        """
        Add a transaction to the human-review queue.
        """

        with self._connect() as conn:

            conn.execute(
                """
                INSERT INTO review_queue (
                    transaction_id,
                    cc_num,
                    amount,
                    category,
                    transaction_time,
                    fraud_probability,
                    risk_level,
                    action,
                    prev_avg_amt,
                    prev_5_avg_amt,
                    amt_ratio_recent5,
                    reasons
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    transaction_id,
                    entity_id,
                    amount,
                    category,
                    transaction_time,
                    fraud_probability,
                    risk_level,
                    action,
                    prev_avg_amt,
                    prev_5_avg_amt,
                    amt_ratio_recent5,
                    json.dumps(reasons),
                )
            )

            conn.commit()

    def get_pending_reviews(self) -> list[sqlite3.Row]:
        """
        Return all reviews that haven't been resolved.
        """

        with self._connect() as conn:

            rows = conn.execute(
                """
                SELECT *
                FROM review_queue
                WHERE status = 'PENDING'
                ORDER BY created_at ASC
                """
            ).fetchall()

        return [self._row_to_dict(row) for row in rows]

    def get_review(
        self,
        transaction_id: str
    ) -> Optional[sqlite3.Row]:
        """
        Retrieve one review record.
        """

        with self._connect() as conn:

            row = conn.execute(
                """
                SELECT *
                FROM review_queue
                WHERE transaction_id = ?
                """,
                (transaction_id,)
            ).fetchone()

        return self._row_to_dict(row) if row is not None else None

    def resolve_review(
        self,
        transaction_id: str,
        analyst_decision: str,
        analyst_reason: str,
    ):
        if analyst_decision not in {"CONFIRMED_FRAUD", "LEGITIMATE"}:
            raise ValueError(
                "analyst_decision must be 'CONFIRMED_FRAUD' or 'LEGITIMATE'"
            )

        reviewed_at = datetime.now(UTC).isoformat()

        with self._connect() as conn:
            conn.execute(
                """
                UPDATE review_queue
                SET
                    status = 'RESOLVED',
                    analyst_decision = ?,
                    analyst_reason = ?,
                    reviewed_at = ?
                WHERE transaction_id = ?
                """,
                (
                    analyst_decision,
                    analyst_reason,
                    reviewed_at,
                    transaction_id,
                ),
            )

            row = conn.execute(
                """
                SELECT *
                FROM review_queue
                WHERE transaction_id = ?
                """,
                (transaction_id,),
            ).fetchone()

        if row is None:
            return None
        
        if self.transaction_store is not None:
            self.transaction_store.set_actual_outcome(
                transaction_id=transaction_id,
                actual_outcome=(
                    "FRAUD"
                    if analyst_decision == "CONFIRMED_FRAUD"
                    else "LEGITIMATE"
                ),
                outcome_source="analyst_review",
                outcome_reason=analyst_reason,
            )

        return self._row_to_dict(row)
    
    def _row_to_dict(self, row: sqlite3.Row) -> dict:
        data = dict(row)

        # Internal SQLite compatibility column.
        # The rest of the application uses the universal name.
        data["entity_id"] = data.pop("cc_num")

        return data