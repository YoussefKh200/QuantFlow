"""
Volatility Regime Classifier.

4-state Hidden Markov Model trained on:
  [log_return, rv_21d, atm_iv_30d, iv_rank, skew_25d]

States are sorted by mean IV level post-training and mapped to
human-readable regime labels.  Heuristic rules (IV/RV ratio)
overlay the statistical classification.
"""
from __future__ import annotations

import warnings
from enum import Enum
from typing import Optional

import numpy as np
import pandas as pd

from app.core.logging import get_logger

logger = get_logger(__name__)


class VolRegime(str, Enum):
    LOW = "low_volatility"
    NORMAL = "normal_volatility"
    HIGH = "high_volatility"
    COMPRESSION = "compression"
    EXPANSION = "expansion"
    EVENT = "event_driven"


class RegimeClassifier:
    """
    HMM-based regime detection with heuristic overlay.

    Training: requires ~252 rows of daily data with columns:
      close, hv_21d, atm_iv_30d, iv_rank, skew_25d

    Inference: uses last 20 observations for Viterbi decode.
    """

    N_STATES = 4
    TRAINING_WINDOW = 252

    def __init__(self) -> None:
        self._model = None
        self._trained = False
        self._state_order: Optional[np.ndarray] = None

    def _import_hmm(self):
        """Lazy import — hmmlearn is only needed when training."""
        try:
            from hmmlearn import hmm
            return hmm
        except ImportError:
            raise ImportError("hmmlearn required: pip install hmmlearn")

    def _build_features(self, df: pd.DataFrame) -> np.ndarray:
        """
        Feature matrix for HMM.
        All features normalized to roughly [-2, 2] range.
        """
        log_ret = np.log(df["close"].pct_change().fillna(0) + 1)
        rv = df["hv_21d"].ffill().fillna(0.20)
        iv = df["atm_iv_30d"].ffill().fillna(0.20)
        iv_rank_norm = df["iv_rank"].fillna(50.0) / 100.0
        skew = df["skew_25d"].fillna(0.0)

        return np.column_stack([log_ret, rv, iv, iv_rank_norm, skew])

    def train(self, df: pd.DataFrame) -> None:
        """
        Fit the HMM on the most recent TRAINING_WINDOW rows.

        Parameters
        ----------
        df : DataFrame with columns: close, hv_21d, atm_iv_30d, iv_rank, skew_25d
        """
        hmm = self._import_hmm()
        training_data = df.tail(self.TRAINING_WINDOW).copy()

        if len(training_data) < 60:
            raise ValueError(f"Need ≥60 rows to train, got {len(training_data)}")

        X = self._build_features(training_data)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            model = hmm.GaussianHMM(
                n_components=self.N_STATES,
                covariance_type="full",
                n_iter=1000,
                tol=1e-4,
                random_state=42,
                verbose=False,
            )
            model.fit(X)

        self._model = model
        self._trained = True

        # Sort states by mean ATM IV (column index 2)
        iv_means = model.means_[:, 2]
        self._state_order = np.argsort(iv_means)

        logger.info(
            "regime_classifier_trained",
            n_samples=len(training_data),
            converged=model.monitor_.converged,
            iv_means_sorted=iv_means[self._state_order].tolist(),
        )

    def classify(self, df: pd.DataFrame) -> dict:
        """
        Classify the current regime from the most recent observations.

        Returns dict with:
          regime, state_probability, rv_21d, atm_iv, iv_rv_ratio,
          is_compression, is_expansion
        """
        if not self._trained or self._model is None:
            return self._fallback_classify(df)

        X = self._build_features(df.tail(30))

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            states = self._model.predict(X)
            proba = self._model.predict_proba(X)

        current_raw = int(states[-1])
        sorted_pos = int(np.where(self._state_order == current_raw)[0][0])

        # Map sorted position to regime label (0=low, 1=normal, 2=high, 3=expansion)
        regime_map = [VolRegime.LOW, VolRegime.NORMAL, VolRegime.HIGH, VolRegime.EXPANSION]
        regime = regime_map[min(sorted_pos, 3)]

        rv = float(df["hv_21d"].iloc[-1]) if "hv_21d" in df.columns else 0.20
        iv = float(df["atm_iv_30d"].iloc[-1]) if "atm_iv_30d" in df.columns else 0.20
        iv_rv_ratio = iv / rv if rv > 0 else 1.0

        # ---- Heuristic overlays ----
        # IV/RV compression: IV much lower than realized vol — unusual, often precedes spike
        if iv_rv_ratio < 0.80:
            regime = VolRegime.COMPRESSION
        # IV/RV expansion: IV much higher than realized — fear premium, trend regime
        elif iv_rv_ratio > 1.60 and sorted_pos >= 2:
            regime = VolRegime.EXPANSION

        return {
            "regime": regime.value,
            "state_index": sorted_pos,
            "state_probability": float(proba[-1, current_raw]),
            "rv_21d": round(rv, 4),
            "atm_iv": round(iv, 4),
            "iv_rv_ratio": round(iv_rv_ratio, 3),
            "is_compression": regime == VolRegime.COMPRESSION,
            "is_expansion": regime == VolRegime.EXPANSION,
        }

    def _fallback_classify(self, df: pd.DataFrame) -> dict:
        """
        Simple heuristic classification when HMM not yet trained.
        Used on first startup or when training data is insufficient.
        """
        rv = float(df["hv_21d"].iloc[-1]) if "hv_21d" in df.columns and len(df) > 0 else 0.20
        iv = float(df["atm_iv_30d"].iloc[-1]) if "atm_iv_30d" in df.columns and len(df) > 0 else 0.20
        iv_rank = float(df["iv_rank"].iloc[-1]) if "iv_rank" in df.columns and len(df) > 0 else 50.0
        iv_rv = iv / rv if rv > 0 else 1.0

        if iv < 0.12 or iv_rank < 15:
            regime = VolRegime.LOW
        elif iv > 0.35 or iv_rank > 85:
            regime = VolRegime.HIGH
        elif iv_rv < 0.80:
            regime = VolRegime.COMPRESSION
        elif iv_rv > 1.60:
            regime = VolRegime.EXPANSION
        else:
            regime = VolRegime.NORMAL

        return {
            "regime": regime.value,
            "state_index": -1,
            "state_probability": 0.5,
            "rv_21d": round(rv, 4),
            "atm_iv": round(iv, 4),
            "iv_rv_ratio": round(iv_rv, 3),
            "is_compression": regime == VolRegime.COMPRESSION,
            "is_expansion": regime == VolRegime.EXPANSION,
            "method": "heuristic_fallback",
        }

    @property
    def is_trained(self) -> bool:
        return self._trained


class RealizedVolCalculator:
    """
    Historical/Realized Volatility calculations.
    Multiple window conventions.
    """

    @staticmethod
    def compute(
        closes: np.ndarray,
        windows: tuple[int, ...] = (5, 10, 21, 63),
        annualize: bool = True,
    ) -> dict[str, float]:
        """
        Yang-Zhang realized vol estimator using close-to-close log returns.
        Returns HV for each window.
        """
        if len(closes) < 2:
            return {f"hv_{w}d": float("nan") for w in windows}

        log_returns = np.log(closes[1:] / closes[:-1])
        factor = np.sqrt(252) if annualize else 1.0
        result = {}

        for w in windows:
            if len(log_returns) >= w:
                rv = float(np.std(log_returns[-w:], ddof=1) * factor)
            else:
                rv = float("nan")
            result[f"hv_{w}d"] = round(rv, 6) if not np.isnan(rv) else None

        return result
