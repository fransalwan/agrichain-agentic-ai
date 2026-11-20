"""Enterprise 5 (SuperMart): XGBoost Demand Forecasting + Newsvendor Safety-Stock PO (Chen & Guestrin, 2016)."""
from __future__ import annotations

import pickle
import time
from pathlib import Path
from typing import Any, Dict

import numpy as np
import pandas as pd
import xgboost as xgb
from scipy.stats import norm
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error, root_mean_squared_error, r2_score

from config.settings import ARTIFACTS_DIR, DATA_DIR, settings

STORE_MAP = {"SM-01": 0, "SM-02": 1, "SM-03": 2}
SEASON_MAP = {"Dry": 0, "Wet": 1}


class SuperMartDemandModel:
    def __init__(self, random_state: int = settings.random_seed):
        self.model = xgb.XGBRegressor(
            n_estimators=240,
            learning_rate=0.05,
            max_depth=5,
            subsample=0.85,
            colsample_bytree=0.85,
            random_state=random_state,
            n_jobs=-1,
        )
        self.residual_std: float = 35.0
        self.metrics: Dict[str, Any] = {}

    @staticmethod
    def _featurize(df: pd.DataFrame) -> np.ndarray:
        return np.column_stack([
            df["store_id"].map(STORE_MAP).fillna(0).values,
            df["day_of_week"].values,
            df["month"].values,
            df["price_rp"].values,
            df["is_promo"].values,
            df["is_weekend"].values,
            df["season_flag"].map(SEASON_MAP).fillna(1).values,
        ])

    def train_and_evaluate(self, csv_path: Path = DATA_DIR / "supermart_pos_sales.csv") -> Dict[str, Any]:
        df = pd.read_csv(csv_path).sort_values(["sales_date", "store_id"]).reset_index(drop=True)
        X = self._featurize(df)
        y = df["demand_sold_kg"].values

        n = len(df)
        i_tr, i_val = int(0.70 * n), int(0.85 * n)
        X_train, y_train = X[:i_tr], y[:i_tr]
        X_val, y_val = X[i_tr:i_val], y[i_tr:i_val]
        X_test, y_test = X[i_val:], y[i_val:]

        t0 = time.perf_counter()
        self.model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
        train_ms = (time.perf_counter() - t0) * 1000.0

        t1 = time.perf_counter()
        y_pred = self.model.predict(X_test)
        inf_ms = ((time.perf_counter() - t1) * 1000.0) / max(len(X_test), 1)

        mae = float(mean_absolute_error(y_test, y_pred))
        rmse = float(root_mean_squared_error(y_test, y_pred))
        mape = float(mean_absolute_percentage_error(y_test, y_pred) * 100.0)
        r2 = float(r2_score(y_test, y_pred))
        self.residual_std = float(np.std(y_test - y_pred))

        self.metrics = {
            "enterprise": "SuperMart",
            "model": "XGBoost Regression + Newsvendor Safety-Stock",
            "train_rows": int(i_tr),
            "val_rows": int(i_val - i_tr),
            "test_rows": int(n - i_val),
            "test_mae_kg": round(mae, 2),
            "test_rmse_kg": round(rmse, 2),
            "test_mape_pct": round(mape, 2),
            "target_mape_pct": "<= 15.0%",
            "target_met": mape <= 15.0,
            "test_r2": round(r2, 4),
            "residual_std_kg": round(self.residual_std, 2),
            "train_time_ms": round(train_ms, 1),
            "avg_inference_ms": round(inf_ms, 4),
        }
        return self.metrics

    def forecast_total_chain_demand(
        self,
        day_of_week: int = 4,
        month: int = 11,
        price_rp: float = 14000.0,
        is_promo: int = 0,
        season: str = "Wet",
    ) -> float:
        is_weekend = 1 if day_of_week >= 5 else 0
        rows = np.array([
            [store_idx, day_of_week, month, price_rp, is_promo, is_weekend, SEASON_MAP.get(season, 1)]
            for store_idx in (0, 1, 2)
        ])
        return float(np.round(self.model.predict(rows).sum(), 1))

    def compute_newsvendor_po(
        self,
        forecast_demand_kg: float,
        current_stock_kg: float = 0.0,
        sell_price_rp: float = 14500.0,
        buy_cost_rp: float = 10000.0,
        salvage_value_rp: float = 1500.0,
    ) -> Dict[str, Any]:
        """Classic Newsvendor optimal order quantity balancing underage (stockout) vs overage (spoilage)."""
        c_u = max(100.0, sell_price_rp - buy_cost_rp)      # Underage cost (lost margin)
        c_o = max(100.0, buy_cost_rp - salvage_value_rp)   # Overage cost (spoilage loss)
        critical_fractile = c_u / (c_u + c_o)
        z_star = float(norm.ppf(critical_fractile))
        # Aggregate std across 3 stores
        agg_std = self.residual_std * np.sqrt(3.0)
        optimal_target = max(0.0, forecast_demand_kg + z_star * agg_std)
        po_qty = max(0.0, optimal_target - current_stock_kg)
        return {
            "forecast_demand_kg": round(forecast_demand_kg, 1),
            "critical_fractile": round(critical_fractile, 3),
            "safety_buffer_kg": round(z_star * agg_std, 1),
            "recommended_po_kg": round(po_qty, 1),
        }

    def save(self, path: Path = ARTIFACTS_DIR / "supermart_xgb.pkl") -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump({"model": self.model, "residual_std": self.residual_std, "metrics": self.metrics}, f)

    @classmethod
    def load(cls, path: Path = ARTIFACTS_DIR / "supermart_xgb.pkl") -> "SuperMartDemandModel":
        inst = cls()
        with open(path, "rb") as f:
            data = pickle.load(f)
        inst.model = data["model"]
        inst.residual_std = data["residual_std"]
        inst.metrics = data["metrics"]
        return inst
