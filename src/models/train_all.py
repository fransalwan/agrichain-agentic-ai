"""Train and evaluate all 5 heterogeneous enterprise ML models + verify MILP-FEFO & CVRP."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.settings import RESULTS_DIR
from src.data.db_adapter import EnterpriseDatabaseAdapter
from src.data.generate_dummy_data import generate_all
from src.models.agrofarm_rf import AgroFarmYieldModel
from src.models.coldchain_iforest_cvrp import ColdChainMonitoringAndRouting
from src.models.freshfood_cnn import FreshFoodVisualGradingModel
from src.models.koperasi_lgbm import KoperasiPriceModel
from src.models.milp_fefo import solve_milp_fefo
from src.models.supermart_xgb import SuperMartDemandModel
from src.protocols.fipa_epcis import HarvestBatch


def train_and_evaluate_all() -> dict:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    print("[1/4] Generating multi-enterprise dummy datasets (seed=42)...")
    data_counts = generate_all(seed=42)
    db_status = EnterpriseDatabaseAdapter().materialize_local_dbs()

    print("[2/4] Training & evaluating 5 heterogeneous local enterprise ML models...")
    m1 = AgroFarmYieldModel()
    r1 = m1.train_and_evaluate()
    m1.save()

    m2 = KoperasiPriceModel()
    r2 = m2.train_and_evaluate()
    m2.save()

    m3 = FreshFoodVisualGradingModel()
    r3 = m3.train_and_evaluate()
    m3.save()

    m4 = ColdChainMonitoringAndRouting()
    r4 = m4.train_and_evaluate()
    m4.save()

    m5 = SuperMartDemandModel()
    r5 = m5.train_and_evaluate()
    m5.save()

    print("[3/4] Verifying Global MILP-FEFO solver on showcase 4,500 kg scenario...")
    showcase_lots = [
        HarvestBatch(lot_id="H001", qty_kg=2000, grade="A", shelf_life_days=5, ask_price_rp=10000, food_safety_approved=True),
        HarvestBatch(lot_id="H002", qty_kg=1500, grade="B", shelf_life_days=3, ask_price_rp=7000, food_safety_approved=True),
        HarvestBatch(lot_id="H003", qty_kg=1000, grade="C", shelf_life_days=2, ask_price_rp=4000, food_safety_approved=True),
    ]
    milp_normal = solve_milp_fefo(showcase_lots, demand_supermart_kg=2000, cap_freshfood_reg_kg=2000, cap_cold_storage_kg=3000, allow_overtime=False)
    milp_disrupt = solve_milp_fefo(showcase_lots, demand_supermart_kg=2000, cap_freshfood_reg_kg=2000, cap_freshfood_ot_kg=500, cap_cold_storage_kg=1000, allow_overtime=True)

    summary = {
        "dataset_counts": data_counts,
        "local_databases": db_status,
        "enterprise_models": {
            "AGT-01_AgroFarm": r1,
            "AGT-02_Koperasi": r2,
            "AGT-03_FreshFood": r3,
            "AGT-04_ColdChain": r4,
            "AGT-05_SuperMart": r5,
        },
        "milp_showcase_verification": {
            "normal_condition": milp_normal,
            "cold_storage_failure_adaptive": milp_disrupt,
        },
    }

    out_file = RESULTS_DIR / "ml_metrics.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"[4/4] Saved ML & MILP verification metrics to {out_file}")
    for name, m in summary["enterprise_models"].items():
        print(f"  * {name} ({m['model']}): target_met={m['target_met']}")
    print(f"  * MILP Normal FLR={milp_normal['food_loss_rate_pct']}%, OFR={milp_normal['order_fulfillment_rate_pct']}%, solve={milp_normal['solve_time_ms']}ms")
    print(f"  * MILP Disrupt Adaptive FLR={milp_disrupt['food_loss_rate_pct']}%, OFR={milp_disrupt['order_fulfillment_rate_pct']}%, OT={milp_disrupt['overtime_activated']}")
    return summary


if __name__ == "__main__":
    train_and_evaluate_all()
