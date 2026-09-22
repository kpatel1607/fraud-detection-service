from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ModelAdapter(ABC):
    """
    Framework-independent interface for a fraud classification model.
    """

    @abstractmethod
    def predict_probability(self, features: Any) -> float:
        """
        Return the probability of the positive/fraud class.
        """
        raise NotImplementedError