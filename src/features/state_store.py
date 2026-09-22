from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional


class EntityStateStore:
    """
    Persistent storage for per-entity transaction history.

    The entity may represent a card, account, wallet, customer,
    device, or another transaction-linked identity.
    """

    def __init__(
        self,
        db_path: str = "data/fraud_state.db",
    ) -> None:
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
        """
        Create the entity-state table if it doesn't exist.

        The physical table name remains `card_state` for backward
        compatibility with existing databases.
        """
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS card_state (
                    cc_num TEXT PRIMARY KEY,
                    transaction_count INTEGER NOT NULL DEFAULT 0,
                    total_amount REAL NOT NULL DEFAULT 0.0,
                    avg_amount REAL,
                    recent_amounts TEXT,
                    last_transaction_time TEXT
                )
                """
            )
            conn.commit()

    def get_entity(
        self,
        entity_id: str,
    ) -> Optional[sqlite3.Row]:
        """
        Retrieve one entity's current state.
        """
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT
                    cc_num,
                    transaction_count,
                    total_amount,
                    avg_amount,
                    recent_amounts,
                    last_transaction_time
                FROM card_state
                WHERE cc_num = ?
                """,
                (entity_id,),
            ).fetchone()

        return row

    def upsert_entity(
        self,
        entity_id: str,
        transaction_count: int,
        total_amount: float,
        avg_amount: Optional[float],
        recent_amounts: str,
        last_transaction_time: str,
    ) -> None:
        """
        Insert or update the current state for an entity.
        """
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO card_state (
                    cc_num,
                    transaction_count,
                    total_amount,
                    avg_amount,
                    recent_amounts,
                    last_transaction_time
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(cc_num)
                DO UPDATE SET
                    transaction_count = excluded.transaction_count,
                    total_amount = excluded.total_amount,
                    avg_amount = excluded.avg_amount,
                    recent_amounts = excluded.recent_amounts,
                    last_transaction_time =
                        excluded.last_transaction_time
                """,
                (
                    entity_id,
                    transaction_count,
                    total_amount,
                    avg_amount,
                    recent_amounts,
                    last_transaction_time,
                ),
            )
            conn.commit()


# Backward-compatible alias.
#
# Existing code can continue importing CardStateStore while
# the internal abstraction becomes EntityStateStore.
CardStateStore = EntityStateStore