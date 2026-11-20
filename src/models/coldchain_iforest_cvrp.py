"""Enterprise 4 (ColdChain Logistics): Isolation Forest Anomaly Detection + Google OR-Tools CVRP (Liu et al., 2008)."""
from __future__ import annotations

import pickle
import time
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd
from ortools.constraint_solver import pywrapcp, routing_enums_pb2
from sklearn.ensemble import IsolationForest
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score

from config.settings import ARTIFACTS_DIR, DATA_DIR, settings

TEL_FEATURES = ["temp_c", "humidity_pct", "power_kw"]


class ColdChainMonitoringAndRouting:
    def __init__(self, random_state: int = settings.random_seed):
        self.iforest = IsolationForest(
            n_estimators=150,
            contamination=0.015,
            max_samples="auto",
            random_state=random_state,
            n_jobs=-1,
        )
        self.metrics: Dict[str, Any] = {}

    def train_and_evaluate(self, csv_path: Path = DATA_DIR / "coldchain_iot_telemetry.csv") -> Dict[str, Any]:
        df = pd.read_csv(csv_path)
        X = df[TEL_FEATURES].values
        y = df["is_anomaly"].values

        # Normal-Only Train (70%) + Mixed Val (15%) / Test (15%) per Tabel 4.4
        n = len(df)
        i_tr, i_val = int(0.70 * n), int(0.85 * n)
        X_train = X[:i_tr][y[:i_tr] == 0]
        X_val, y_val = X[i_tr:i_val], y[i_tr:i_val]
        X_test, y_test = X[i_val:], y[i_val:]

        t0 = time.perf_counter()
        self.iforest.fit(X_train)
        train_ms = (time.perf_counter() - t0) * 1000.0

        t1 = time.perf_counter()
        raw_preds = self.iforest.predict(X_test)  # -1 anomaly, 1 normal
        scores = -self.iforest.decision_function(X_test)
        inf_ms = ((time.perf_counter() - t1) * 1000.0) / max(len(X_test), 1)

        y_pred = (raw_preds == -1).astype(int)
        prec = float(precision_score(y_test, y_pred, zero_division=0))
        rec = float(recall_score(y_test, y_pred, zero_division=0))
        f1 = float(f1_score(y_test, y_pred, zero_division=0))
        auc = float(roc_auc_score(y_test, scores)) if len(np.unique(y_test)) > 1 else 1.0

        # Benchmark OR-Tools CVRP route distance reduction vs naive point-to-point
        cvrp_bench = self.solve_cvrp_demo()

        self.metrics = {
            "enterprise": "ColdChain Logistics",
            "model": "Isolation Forest + Google OR-Tools CVRP",
            "train_normal_rows": int(len(X_train)),
            "val_rows": int(len(X_val)),
            "test_rows": int(len(X_test)),
            "anomaly_precision_pct": round(prec * 100.0, 2),
            "anomaly_recall_pct": round(rec * 100.0, 2),
            "anomaly_f1_pct": round(f1 * 100.0, 2),
            "anomaly_roc_auc": round(auc, 4),
            "cvrp_naive_distance_km": cvrp_bench["naive_distance_km"],
            "cvrp_optimized_distance_km": cvrp_bench["optimized_distance_km"],
            "cvrp_distance_reduction_pct": cvrp_bench["distance_reduction_pct"],
            "target_route_reduction": ">= 10.0%",
            "target_met": (f1 >= 0.90 and cvrp_bench["distance_reduction_pct"] >= 10.0),
            "train_time_ms": round(train_ms, 1),
            "avg_inference_ms": round(inf_ms, 4),
        }
        return self.metrics

    def detect_anomalies(self, readings: List[Dict[str, Any]]) -> Dict[str, Any]:
        X = np.array([[float(r["temp_c"]), float(r["humidity_pct"]), float(r["power_kw"])] for r in readings])
        preds = self.iforest.predict(X)
        scores = -self.iforest.decision_function(X)
        affected_zones = []
        max_score = 0.0
        for idx, (p, s) in enumerate(zip(preds, scores)):
            temp = float(readings[idx]["temp_c"])
            if p == -1 or temp > 12.5 or temp < 6.5:
                z = readings[idx].get("zone_id", f"Z-{idx+1}")
                if z not in affected_zones:
                    affected_zones.append(z)
                max_score = max(max_score, float(np.clip(0.5 + s, 0.0, 0.99)))
        total_zones = 3
        healthy_zones = max(0, total_zones - len(affected_zones))
        effective_cap = healthy_zones * 1000.0
        return {
            "anomaly_detected": len(affected_zones) > 0,
            "affected_zones": affected_zones,
            "previous_capacity_kg": 3000.0,
            "effective_capacity_kg": effective_cap,
            "capacity_drop_pct": round(((3000.0 - effective_cap) / 3000.0) * 100.0, 1),
            "anomaly_score": round(max_score, 3),
        }

    @staticmethod
    def solve_cvrp_demo(
        demands_kg: List[int] | None = None,
        vehicle_capacities: List[int] | None = None,
    ) -> Dict[str, Any]:
        """Solve real Capacitated Vehicle Routing Problem via Google OR-Tools.
        Nodes: 0=Koperasi_Hub (Depot), 1=SuperMart_DC, 2=FreshFood_Plant,
               3=ColdChain_WH01, 4=SuperMart_Branch2, 5=Partner3PL_WH.
        """
        dist_matrix = [
            [0, 42, 28, 19, 48, 54],   # 0: Koperasi_Hub
            [42, 0, 31, 34, 14, 26],   # 1: SuperMart_DC
            [28, 31, 0, 16, 36, 39],   # 2: FreshFood_Plant
            [19, 34, 16, 0, 38, 35],   # 3: ColdChain_WH01
            [48, 14, 36, 38, 0, 22],   # 4: SuperMart_Branch2
            [54, 26, 39, 35, 22, 0],   # 5: Partner3PL_WH
        ]
        node_names = ["Koperasi_Hub", "SuperMart_DC", "FreshFood_Plant", "ColdChain_WH01", "SuperMart_B2", "Partner3PL_WH"]
        demands = demands_kg if demands_kg is not None else [0, 1200, 1500, 500, 800, 500]
        caps = vehicle_capacities if vehicle_capacities is not None else [2000, 2000, 1500]

        # Naive dedicated point-to-point round-trip from depot to every active destination
        naive_km = sum(2 * dist_matrix[0][i] for i in range(1, len(demands)) if demands[i] > 0)

        manager = pywrapcp.RoutingIndexManager(len(dist_matrix), len(caps), 0)
        routing = pywrapcp.RoutingModel(manager)

        def dist_cb(from_i, to_i):
            return dist_matrix[manager.IndexToNode(from_i)][manager.IndexToNode(to_i)]

        transit_idx = routing.RegisterTransitCallback(dist_cb)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_idx)

        def demand_cb(from_i):
            return demands[manager.IndexToNode(from_i)]

        demand_idx = routing.RegisterUnaryTransitCallback(demand_cb)
        routing.AddDimensionWithVehicleCapacity(demand_idx, 0, caps, True, "Capacity")

        params = pywrapcp.DefaultRoutingSearchParameters()
        params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        params.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        params.time_limit.seconds = 1

        sol = routing.SolveWithParameters(params)
        routes = []
        opt_km = 0
        if sol:
            for v in range(len(caps)):
                idx = routing.Start(v)
                r_nodes = []
                r_dist = 0
                r_load = 0
                while not routing.IsEnd(idx):
                    node = manager.IndexToNode(idx)
                    r_nodes.append(node_names[node])
                    r_load += demands[node]
                    prev = idx
                    idx = sol.Value(routing.NextVar(idx))
                    r_dist += routing.GetArcCostForVehicle(prev, idx, v)
                r_nodes.append(node_names[manager.IndexToNode(idx)])
                if r_load > 0:
                    routes.append({"truck": f"TRK-0{v+1}", "stops": r_nodes, "load_kg": r_load, "distance_km": r_dist})
                    opt_km += r_dist
        else:
            opt_km = naive_km

        reduction = ((naive_km - opt_km) / max(naive_km, 1)) * 100.0
        return {
            "routes": routes,
            "naive_distance_km": float(naive_km),
            "optimized_distance_km": float(opt_km),
            "distance_reduction_pct": round(reduction, 2),
            "transport_cost_rp": float(opt_km * 9500),
        }

    def save(self, path: Path = ARTIFACTS_DIR / "coldchain_iforest.pkl") -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump({"iforest": self.iforest, "metrics": self.metrics}, f)

    @classmethod
    def load(cls, path: Path = ARTIFACTS_DIR / "coldchain_iforest.pkl") -> "ColdChainMonitoringAndRouting":
        inst = cls()
        with open(path, "rb") as f:
            data = pickle.load(f)
        inst.iforest = data["iforest"]
        inst.metrics = data["metrics"]
        return inst
