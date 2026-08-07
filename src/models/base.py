from abc import ABC, abstractmethod
from typing import Any

import numpy as np
import pandas as pd


class BaseFraudModel(ABC):
    """
    Abstract Base Class outlining interface compliance for all ML Classifiers in the system.
    """

    @abstractmethod
    def load(self, model_dir: str) -> None:
        """
        Loads classifier weights and pipeline dependencies from serialization directory.
        """
        pass

    @abstractmethod
    def predict_probability(self, features: pd.DataFrame) -> np.ndarray:
        """
        Runs inference and returns raw fraud probability array.
        """
        pass

    @abstractmethod
    def train(self, X: pd.DataFrame, y: pd.Series) -> dict[str, Any]:
        """
        Fits the underlying classifier and returns performance metric dictionary.
        """
        pass
