from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.domain.paysim_transaction import PaySimTransaction


class PaySimFeatureBuilder:
    """
    Builds the exact feature schema expected by the PaySim model.
    """

    def __init__(
        self,
        metadata_path: str = "models/paysim/metadata.json",
    ) -> None:
        self.metadata_path = Path(metadata_path)

        if not self.metadata_path.exists():
            raise FileNotFoundError(
                f"PaySim metadata not found: {self.metadata_path}"
            )

        with self.metadata_path.open("r", encoding="utf-8") as file:
            self.metadata = json.load(file)

        self.expected_features = self.metadata["features"]

    def build(self, transaction: PaySimTransaction) -> pd.DataFrame:
        """
        Build a single-row DataFrame matching the PaySim model's
        training feature schema.
        """

        amount = transaction.amount
        oldbalance_org = transaction.oldbalance_org
        oldbalance_dest = transaction.oldbalance_dest

        if oldbalance_org > 0:
            sender_amount_ratio = amount / oldbalance_org
            sender_balance_coverage = min(sender_amount_ratio, 1.0)
            log_sender_amount_ratio = np.log1p(sender_amount_ratio)
        else:
            sender_balance_coverage = np.nan
            log_sender_amount_ratio = np.nan

        sender_balance_zero = int(oldbalance_org == 0)
        destination_balance_zero = int(oldbalance_dest == 0)

        feature_values = {
            "type": transaction.transaction_type,
            "amount": amount,
            "oldbalanceOrg": oldbalance_org,
            "oldbalanceDest": oldbalance_dest,
            "sender_balance_coverage": sender_balance_coverage,
            "log_sender_amount_ratio": log_sender_amount_ratio,
            "sender_balance_zero": sender_balance_zero,
            "destination_balance_zero": destination_balance_zero,
        }

        missing_features = [
            feature
            for feature in self.expected_features
            if feature not in feature_values
        ]

        if missing_features:
            raise ValueError(
                "Missing PaySim features: "
                f"{missing_features}"
            )

        return pd.DataFrame(
            [
                {
                    feature: feature_values[feature]
                    for feature in self.expected_features
                }
            ]
        )