from __future__ import annotations

from datetime import UTC, datetime
import sqlite3
from pathlib import Path

from src.review.paysim_review import PaySimReview


class PaySimReviewQueue:
    """
    Persistent review queue for PaySim transactions.
    """

    def __init__(
        self,
        db_path: str = "data/paysim_review_queue.db",
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
                CREATE TABLE IF NOT EXISTS paysim_review_queue (
                    review_id INTEGER PRIMARY KEY AUTOINCREMENT,

                    transaction_id TEXT NOT NULL UNIQUE,
                    transaction_type TEXT NOT NULL,

                    amount REAL NOT NULL,
                    oldbalance_org REAL NOT NULL,
                    oldbalance_dest REAL NOT NULL,

                    fraud_probability REAL NOT NULL,
                    model_decision TEXT NOT NULL,
                    risk_level TEXT NOT NULL,
                    action TEXT NOT NULL,

                    status TEXT NOT NULL DEFAULT 'PENDING',

                    actual_outcome TEXT,

                    created_at TEXT NOT NULL,
                    reviewed_at TEXT
                )
                """
            )

            conn.commit()

    def add_review(
        self,
        review: PaySimReview,
    ) -> None:
        """
        Add a PaySim transaction to the review queue.
        """

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO paysim_review_queue (
                    transaction_id,
                    transaction_type,
                    amount,
                    oldbalance_org,
                    oldbalance_dest,
                    fraud_probability,
                    model_decision,
                    risk_level,
                    action,
                    status,
                    actual_outcome,
                    created_at,
                    reviewed_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    review.transaction_id,
                    review.transaction_type,
                    review.amount,
                    review.oldbalance_org,
                    review.oldbalance_dest,
                    review.fraud_probability,
                    review.model_decision,
                    review.risk_level,
                    review.action,
                    review.status,
                    review.actual_outcome,
                    datetime.now(UTC).isoformat(),
                    (
                        review.reviewed_at.isoformat()
                        if review.reviewed_at
                        else None
                    ),
                ),
            )

            conn.commit()

    def get_pending_reviews(self) -> list[dict]:
        """
        Return all pending PaySim reviews.
        """

        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM paysim_review_queue
                WHERE status = 'PENDING'
                ORDER BY created_at ASC
                """
            ).fetchall()

        return [dict(row) for row in rows]

    def get_review(
        self,
        transaction_id: str,
    ) -> dict | None:
        """
        Retrieve one PaySim review.
        """

        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT *
                FROM paysim_review_queue
                WHERE transaction_id = ?
                """,
                (transaction_id,),
            ).fetchone()

        return dict(row) if row is not None else None

    def resolve_review(
        self,
        transaction_id: str,
        actual_outcome: str,
    ) -> dict | None:
        """
        Resolve a pending PaySim review.
        """

        if actual_outcome not in {"FRAUD", "LEGITIMATE"}:
            raise ValueError(
                "actual_outcome must be "
                "'FRAUD' or 'LEGITIMATE'"
            )

        reviewed_at = datetime.now(UTC).isoformat()

        with self._connect() as conn:
            cursor = conn.execute(
                """
                UPDATE paysim_review_queue
                SET
                    status = 'RESOLVED',
                    actual_outcome = ?,
                    reviewed_at = ?
                WHERE transaction_id = ?
                  AND status = 'PENDING'
                """,
                (
                    actual_outcome,
                    reviewed_at,
                    transaction_id,
                ),
            )

            if cursor.rowcount == 0:
                return None

            row = conn.execute(
                """
                SELECT *
                FROM paysim_review_queue
                WHERE transaction_id = ?
                """,
                (transaction_id,),
            ).fetchone()

        return dict(row)