from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OrdinalEncoder
from sqlalchemy import select
from sqlalchemy.orm import Session

from bayroute.features import (
    CATEGORICAL_FEATURES,
    MODEL_FEATURES,
    NUMERIC_FEATURES,
    feature_row,
    observations_to_frame,
)
from bayroute.models import TransitObservation
from bayroute.schemas import PredictionRequest

MODEL_VERSION = "bayroute-hgbt-v1"


class ModelNotReadyError(RuntimeError):
    pass


class DelayModelService:
    def __init__(self) -> None:
        self.pipeline: Pipeline | None = None
        self.metrics: dict[str, Any] | None = None
        self.residual_p90_seconds = 180.0

    def train(self, session: Session) -> dict[str, Any]:
        observations = list(
            session.scalars(
                select(TransitObservation).order_by(TransitObservation.captured_at.asc())
            )
        )
        if len(observations) < 50:
            raise ModelNotReadyError("At least 50 observations are required to train the model")

        frame = observations_to_frame(observations)
        split_index = max(1, int(len(frame) * 0.8))
        train = frame.iloc[:split_index]
        test = frame.iloc[split_index:]
        if test.empty:
            raise ModelNotReadyError("Chronological test split is empty")

        preprocessor = ColumnTransformer(
            transformers=[
                (
                    "categorical",
                    OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1),
                    CATEGORICAL_FEATURES,
                ),
                ("numeric", SimpleImputer(strategy="median"), NUMERIC_FEATURES),
            ]
        )
        self.pipeline = Pipeline(
            steps=[
                ("features", preprocessor),
                (
                    "regressor",
                    HistGradientBoostingRegressor(
                        learning_rate=0.07,
                        max_iter=180,
                        max_leaf_nodes=23,
                        min_samples_leaf=18,
                        l2_regularization=0.25,
                        random_state=42,
                    ),
                ),
            ]
        )
        self.pipeline.fit(train[MODEL_FEATURES], train["target_delay_seconds"])

        predictions = self.pipeline.predict(test[MODEL_FEATURES])
        actual = test["target_delay_seconds"].to_numpy()
        mae = float(mean_absolute_error(actual, predictions))
        baseline_value = float(train["target_delay_seconds"].median())
        baseline_predictions = np.full(shape=len(test), fill_value=baseline_value)
        baseline_mae = float(mean_absolute_error(actual, baseline_predictions))
        residuals = np.abs(actual - predictions)
        self.residual_p90_seconds = float(np.quantile(residuals, 0.9))
        improvement = 0.0 if baseline_mae == 0 else (baseline_mae - mae) / baseline_mae * 100

        self.metrics = {
            "trained_records": len(train),
            "test_records": len(test),
            "mae_seconds": round(mae, 2),
            "baseline_mae_seconds": round(baseline_mae, 2),
            "improvement_percent": round(improvement, 2),
            "within_two_minutes_percent": round(float(np.mean(residuals <= 120) * 100), 2),
            "residual_p90_seconds": round(self.residual_p90_seconds, 2),
            "trained_at": datetime.now(UTC).replace(tzinfo=None),
            "model_version": MODEL_VERSION,
        }
        return self.metrics

    def predict(self, request: PredictionRequest) -> dict[str, Any]:
        if self.pipeline is None:
            raise ModelNotReadyError("Delay model has not been trained")

        row = feature_row(
            route_id=request.route_id,
            stop_id=request.stop_id,
            prediction_time=request.prediction_time,
            current_delay_seconds=request.current_delay_seconds,
            previous_stop_delay_seconds=request.previous_stop_delay_seconds,
            headway_minutes=request.headway_minutes,
        )
        predicted = int(round(float(self.pipeline.predict(pd.DataFrame([row]))[0])))
        margin = int(round(self.residual_p90_seconds))
        if predicted < -60:
            status = "early"
        elif predicted <= 120:
            status = "on_time"
        elif predicted <= 300:
            status = "minor_delay"
        else:
            status = "major_delay"
        return {
            "predicted_delay_seconds": predicted,
            "predicted_delay_minutes": round(predicted / 60, 1),
            "status": status,
            "interval_low_seconds": predicted - margin,
            "interval_high_seconds": predicted + margin,
            "model_version": MODEL_VERSION,
        }

    def save(self, artifact_path: str) -> Path:
        if self.pipeline is None or self.metrics is None:
            raise ModelNotReadyError("Cannot save an untrained model")
        path = Path(artifact_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {
                "pipeline": self.pipeline,
                "metrics": self.metrics,
                "residual_p90_seconds": self.residual_p90_seconds,
            },
            path,
        )
        return path

    def load(self, artifact_path: str) -> bool:
        path = Path(artifact_path)
        if not path.exists():
            return False
        payload = joblib.load(path)
        self.pipeline = payload["pipeline"]
        self.metrics = payload["metrics"]
        self.residual_p90_seconds = payload["residual_p90_seconds"]
        return True
