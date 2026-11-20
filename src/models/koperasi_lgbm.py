"""Enterprise 2 (Koperasi Tani): LightGBM Price Forecaster + Contract Net Auction (Ke et al., 2017; Smith, 1980)."""
from __future__ import annotations

import pickle
import time
from pathlib import Path
from typing import Any, Dict, List

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error, r2_score

from config.settings import ARTIFACTS_DIR, DATA_DIR, settings

GRADE_MAP = {"A": 0, "B": 1, "C": 2}
SEASON_MAP = {"Dry": 0, "Wet": 1}


class KoperasiPriceModel:
    def __init__(self, random_state: int = settings.random_seed):
        self.model = lgb.LGBMRegressor(
            n_estimators=220,
            learning_rate=0.05,
            num_leaves=31,
            subsample=0.85,
            colsample_bytree=0.85,
            random_state=random_state,
            verbose=-1,
        )
        self.metrics: Dict[str, Any] = {}

    @staticmethod
    def _featurize(df: pd.DataFrame) -> np.ndarray:
        return np.column_stack([
            df["grade"].map(GRADE_MAP).fillna(1).values,
            df["season"].map(SEASON_MAP).fillna(1).values,
            df["month"].values,
            df["regional_supply_ton"].values,
            df["qty_kg"].values,
            df["shelf_life_days"].values,
        ])

    def train_and_evaluate(self, csv_path: Path = DATA_DIR / "koperasi_market_negotiations.csv") -> Dict[str, Any]:
        df = pd.read_csv(csv_path).sort_values("tx_date").reset_index(drop=True)
        X = self._featurize(df)
        y = df["market_ref_price_rp"].values

        n = len(df)
        i_tr, i_val = int(0.70 * n), int(0.85 * n)
        X_train, y_train = X[:i_tr], y[:i_tr]
        X_val, y_val = X[i_tr:i_val], y[i_tr:i_val]
        X_test, y_test = X[i_val:], y[i_val:]

        t0 = time.perf_counter()
        self.model.fit(
            X_train,
            y_train,
            eval_set=[(X_val, y_val)],
            callbacks=[lgb.early_stopping(stopping_rounds=25, verbose=False)],
        )
        train_ms = (time.perf_counter() - t0) * 1000.0

        t1 = time.perf_counter()
        y_pred = self.model.predict(X_test)
        inf_ms = ((time.perf_counter() - t1) * 1000.0) / max(len(X_test), 1)

        mae = float(mean_absolute_error(y_test, y_pred))
        mape = float(mean_absolute_percentage_error(y_test, y_pred) * 100.0)
        r2 = float(r2_score(y_test, y_pred))

        self.metrics = {
            "enterprise": "Koperasi Tani",
            "model": "LightGBM Regressor + Contract Net Auction",
            "train_rows": int(i_tr),
            "val_rows": int(i_val - i_tr),
            "test_rows": int(n - i_val),
            "test_mae_rp": round(mae, 1),
            "test_mape_pct": round(mape, 2),
            "test_r2": round(r2, 4),
            "target_met": mape <= 8.0,
            "train_time_ms": round(train_ms, 1),
            "avg_inference_ms": round(inf_ms, 4),
        }
        return self.metrics

    def predict_price(self, grade: str, season: str = "Wet", month: int = 11, regional_supply_ton: float = 34.0, qty_kg: float = 1500.0, shelf_life_days: int = 3) -> float:
        x = np.array([[GRADE_MAP.get(grade, 1), SEASON_MAP.get(season, 1), month, regional_supply_ton, qty_kg, shelf_life_days]])
        return float(np.round(self.model.predict(x)[0], -2))

    @staticmethod
    def evaluate_contract_net_bids(lot_id: str, qty_kg: float, floor_price_rp: float, bids: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Contract Net Protocol winner selection respecting private floor price and shelf-life urgency."""
        eligible = [b for b in bids if float(b.get("offer_price_rp", 0)) >= floor_price_rp and float(b.get("qty_kg", 0)) > 0]
        if not eligible:
            return {
                "lot_id": lot_id,
                "status": "REJECT_PROPOSAL",
                "reason_code": "BELOW_MINIMUM_VIABILITY_THRESHOLD",  # Never exposes floor_price_rp!
                "winner": None,
                "agreed_price_rp": None,
            }
        # Rank by net revenue contribution (price * absorbed qty)
        best = max(eligible, key=lambda b: float(b["offer_price_rp"]) * min(qty_kg, float(b["qty_kg"])))
        return {
            "lot_id": lot_id,
            "status": "ACCEPT_PROPOSAL",
            "winner": best["buyer_id"],
            "agreed_qty_kg": min(qty_kg, float(best["qty_kg"])),
            "agreed_price_rp": float(best["offer_price_rp"]),
            "slot": best.get("slot", "REGULAR"),
        }

    def save(self, path: Path = ARTIFACTS_DIR / "koperasi_lgbm.pkl") -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump({"model": self.model, "metrics": self.metrics}, f)

    @classmethod
    def load(cls, path: Path = ARTIFACTS_DIR / "koperasi_lgbm.pkl") -> "KoperasiPriceModel":
        inst = cls()
        with open(path, "rb") as f:
            data = pickle.load(f)
        inst.model = data["model"]
        inst.metrics = data["metrics"]
        return inst
