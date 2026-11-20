"""Enterprise 1 (AgroFarm): Random Forest Yield Prediction Model (Breiman, 2001)."""
from __future__ import annotations

import pickle
import time
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, root_mean_squared_error, r2_score
from sklearn.model_selection import TimeSeriesSplit

from config.settings import ARTIFACTS_DIR, DATA_DIR, settings

FEATURES = ["area_ha", "avg_temp_c", "soil_moisture_pct", "rainfall_mm", "fertilizer_kg_ha", "crop_age_days"]


class AgroFarmYieldModel:
    def __init__(self, random_state: int = settings.random_seed):
        self.model = RandomForestRegressor(
            n_estimators=200,
            max_depth=12,
            min_samples_leaf=3,
            random_state=random_state,
            n_jobs=-1,
        )
        self.metrics: Dict[str, Any] = {}

    def train_and_evaluate(self, csv_path: Path = DATA_DIR / "agrofarm_harvest_history.csv") -> Dict[str, Any]:
        df = pd.read_csv(csv_path).sort_values("harvest_date").reset_index(drop=True)
        X = df[FEATURES].values
        y = df["actual_yield_kg"].values

        # Chronological 70 / 15 / 15 split (Tabel 4.4)
        n = len(df)
        i_tr, i_val = int(0.70 * n), int(0.85 * n)
        X_train, y_train = X[:i_tr], y[:i_tr]
        X_val, y_val = X[i_tr:i_val], y[i_tr:i_val]
        X_test, y_test = X[i_val:], y[i_val:]

        # 5-fold Rolling-Origin CV on training set
        tscv = TimeSeriesSplit(n_splits=5)
        cv_maes = []
        for tr_idx, va_idx in tscv.split(X_train):
            m = RandomForestRegressor(n_estimators=100, max_depth=12, min_samples_leaf=3, random_state=settings.random_seed, n_jobs=-1)
            m.fit(X_train[tr_idx], y_train[tr_idx])
            cv_maes.append(mean_absolute_error(y_train[va_idx], m.predict(X_train[va_idx])))

        t0 = time.perf_counter()
        self.model.fit(np.vstack([X_train, X_val]), np.concatenate([y_train, y_val]))
        train_ms = (time.perf_counter() - t0) * 1000.0

        t1 = time.perf_counter()
        y_pred = self.model.predict(X_test)
        inf_ms = ((time.perf_counter() - t1) * 1000.0) / max(len(X_test), 1)

        mae = float(mean_absolute_error(y_test, y_pred))
        rmse = float(root_mean_squared_error(y_test, y_pred))
        r2 = float(r2_score(y_test, y_pred))
        mean_y = float(np.mean(y_test))
        mae_pct = (mae / mean_y) * 100.0

        self.metrics = {
            "enterprise": "AgroFarm",
            "model": "Random Forest Regression",
            "train_rows": int(i_tr),
            "val_rows": int(i_val - i_tr),
            "test_rows": int(n - i_val),
            "cv_5fold_mae_kg": round(float(np.mean(cv_maes)), 2),
            "test_mae_kg": round(mae, 2),
            "test_mae_pct_of_mean": round(mae_pct, 2),
            "target_mae_pct": "<= 10.0%",
            "target_met": mae_pct <= 10.0,
            "test_rmse_kg": round(rmse, 2),
            "test_r2": round(r2, 4),
            "train_time_ms": round(train_ms, 1),
            "avg_inference_ms": round(inf_ms, 4),
        }
        return self.metrics

    def predict_batch(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        X = np.array([[float(r[f]) for f in FEATURES] for r in records])
        tree_preds = np.array([est.predict(X) for est in self.model.estimators_])
        mean_preds = tree_preds.mean(axis=0)
        std_preds = tree_preds.std(axis=0)

        out = []
        for idx, rec in enumerate(records):
            pred_kg = float(np.round(mean_preds[idx], 1))
            ci = float(np.round(1.96 * std_preds[idx], 1))
            out.append({
                "lot_id": rec.get("lot_id", f"LOT-{idx+1}"),
                "predicted_kg": pred_kg,
                "confidence_interval_95": [round(max(0.0, pred_kg - ci), 1), round(pred_kg + ci, 1)],
                "grade": rec.get("grade", "A"),
                "shelf_life_days": int(rec.get("shelf_life_days", 5)),
            })
        return out

    def save(self, path: Path = ARTIFACTS_DIR / "agrofarm_rf.pkl") -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump({"model": self.model, "metrics": self.metrics}, f)

    @classmethod
    def load(cls, path: Path = ARTIFACTS_DIR / "agrofarm_rf.pkl") -> "AgroFarmYieldModel":
        inst = cls()
        with open(path, "rb") as f:
            data = pickle.load(f)
        inst.model = data["model"]
        inst.metrics = data["metrics"]
        return inst
