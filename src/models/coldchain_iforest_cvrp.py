"""Enterprise 4 (ColdChain Logistics): Isolation Forest + XGBoost ETA + Google OR-Tools VRPTW/CVRP.

Implements Pillar 2 upgrades from ColdChain Fleet Manager Revised specification:
- Standardized tomato temperature compliance band: 7.0C - 12.0C (eliminating chilling-injury 2-8C conflict)
- Isolation Forest anomaly detection on cold storage/reefer sensor telemetry
- XGBoost Regressor ETA Predictor trained on chronologically split trip history (MAE, RMSE, MAPE vs baseline)
- Google OR-Tools VRPTW (Vehicle Routing Problem with Time Windows) + scenario comparison & Yogyakarta coordinates
"""
from __future__ import annotations

import pickle
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import xgboost as xgb
from ortools.constraint_solver import pywrapcp, routing_enums_pb2
from sklearn.ensemble import IsolationForest
from sklearn.linear_model import LinearRegression
from sklearn.metrics import (
    f1_score,
    mean_absolute_error,
    mean_absolute_percentage_error,
    precision_score,
    recall_score,
    roc_auc_score,
    root_mean_squared_error,
)

from config.settings import ARTIFACTS_DIR, DATA_DIR, settings

TEL_FEATURES = ["temp_c", "humidity_pct", "power_kw"]
ETA_FEATURES = ["distance_km", "traffic_level", "num_stops", "weather_severity", "departure_hour"]

# Real Yogyakarta / Sleman / Bantul coordinates for interactive geospatial route visualization
COLDCHAIN_NODE_META = [
    {"id": 0, "name": "Koperasi_Hub", "lat": -7.7156, "lon": 110.3556, "role": "Depot"},
    {"id": 1, "name": "SuperMart_DC", "lat": -7.7828, "lon": 110.3671, "role": "Retail DC"},
    {"id": 2, "name": "FreshFood_Plant", "lat": -7.7470, "lon": 110.3045, "role": "Processing Plant"},
    {"id": 3, "name": "ColdChain_WH01", "lat": -7.7312, "lon": 110.3880, "role": "Cold Storage"},
    {"id": 4, "name": "SuperMart_B2", "lat": -7.8240, "lon": 110.3790, "role": "Retail Branch"},
    {"id": 5, "name": "Partner3PL_WH", "lat": -7.8555, "lon": 110.3385, "role": "3PL Backup"},
]


class ColdChainETAModel:
    """XGBoost Regressor for cold-chain trip travel duration / ETA prediction (ColdChain Revised Section 4.1)."""

    MODEL_VERSION = "xgb-eta-v1.0"

    def __init__(self, random_state: int = settings.random_seed):
        self.model = xgb.XGBRegressor(
            n_estimators=180,
            learning_rate=0.06,
            max_depth=4,
            subsample=0.85,
            colsample_bytree=0.9,
            random_state=random_state,
            n_jobs=-1,
        )
        self.metrics: Dict[str, Any] = {}

    @staticmethod
    def _generate_trip_history(n_trips: int = 600, seed: int = settings.random_seed) -> pd.DataFrame:
        rng = np.random.default_rng(seed + 104)
        dist = rng.uniform(12.0, 95.0, n_trips)
        traffic = rng.integers(0, 3, n_trips)  # 0=Low, 1=Medium, 2=High
        stops = rng.integers(1, 5, n_trips)
        weather = rng.choice([0, 1, 2], size=n_trips, p=[0.65, 0.25, 0.10])  # 0=Clear, 1=Rain, 2=HeavyRain
        dep_hr = rng.integers(5, 19, n_trips)
        rush = ((dep_hr >= 7) & (dep_hr <= 9)) | ((dep_hr >= 16) & (dep_hr <= 18))

        base_speed_kmh = 46.0 - traffic * 10.5 - weather * 5.0 - rush * 4.5
        drive_min = (dist / np.clip(base_speed_kmh, 14.0, 55.0)) * 60.0
        service_min = stops * (11.5 + traffic * 2.0)
        noise = rng.normal(0.0, 4.2, n_trips)
        actual_min = np.clip(drive_min + service_min + noise, 15.0, 320.0)

        return pd.DataFrame({
            "distance_km": np.round(dist, 1),
            "traffic_level": traffic,
            "num_stops": stops,
            "weather_severity": weather,
            "departure_hour": dep_hr,
            "actual_duration_min": np.round(actual_min, 1),
        })

    def train_and_evaluate(self) -> Dict[str, Any]:
        df = self._generate_trip_history()
        X = df[ETA_FEATURES].values
        y = df["actual_duration_min"].values

        n = len(df)
        i_tr, i_val = int(0.70 * n), int(0.85 * n)
        X_train, y_train = X[:i_tr], y[:i_tr]
        X_val, y_val = X[i_tr:i_val], y[i_tr:i_val]
        X_test, y_test = X[i_val:], y[i_val:]

        lr = LinearRegression().fit(np.vstack([X_train, X_val]), np.concatenate([y_train, y_val]))
        lr_mae = float(mean_absolute_error(y_test, lr.predict(X_test)))

        t0 = time.perf_counter()
        self.model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
        train_ms = (time.perf_counter() - t0) * 1000.0

        y_pred = self.model.predict(X_test)
        mae = float(mean_absolute_error(y_test, y_pred))
        rmse = float(root_mean_squared_error(y_test, y_pred))
        mape = float(mean_absolute_percentage_error(y_test, y_pred) * 100.0)

        self.metrics = {
            "model": "XGBoost ETA Regressor",
            "model_version": self.MODEL_VERSION,
            "test_mae_min": round(mae, 2),
            "test_rmse_min": round(rmse, 2),
            "test_mape_pct": round(mape, 2),
            "baseline_linear_mae_min": round(lr_mae, 2),
            "beats_baseline": bool(mae < lr_mae),
            "train_time_ms": round(train_ms, 1),
        }
        return self.metrics

    def predict_eta_minutes(
        self,
        distance_km: float,
        traffic_level: int = 1,
        num_stops: int = 2,
        weather_severity: int = 0,
        departure_hour: int = 8,
    ) -> Dict[str, Any]:
        x = np.array([[float(distance_km), int(traffic_level), int(num_stops), int(weather_severity), int(departure_hour)]])
        pred_min = float(self.model.predict(x)[0])
        return {
            "predicted_duration_min": round(max(12.0, pred_min), 1),
            "error_band_min": [round(max(10.0, pred_min - 5.5), 1), round(pred_min + 5.5, 1)],
            "model_version": self.MODEL_VERSION,
        }


class ColdChainMonitoringAndRouting:
    MODEL_VERSION = "iforest-vrptw-v2.0"

    def __init__(self, random_state: int = settings.random_seed):
        self.iforest = IsolationForest(
            n_estimators=150,
            contamination=0.015,
            max_samples="auto",
            random_state=random_state,
            n_jobs=-1,
        )
        self.eta_model = ColdChainETAModel(random_state=random_state)
        self.metrics: Dict[str, Any] = {}

    def train_and_evaluate(self, csv_path: Path = DATA_DIR / "coldchain_iot_telemetry.csv") -> Dict[str, Any]:
        df = pd.read_csv(csv_path)
        X = df[TEL_FEATURES].values
        y = df["is_anomaly"].values

        # Normal-Only Train (70%) + Mixed Val (15%) / Test (15%)
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

        # Train XGBoost ETA & benchmark both CVRP and VRPTW
        eta_m = self.eta_model.train_and_evaluate()
        cvrp_bench = self.solve_cvrp_demo()
        vrptw_bench = self.solve_vrptw(scenario="NORMAL")

        self.metrics = {
            "enterprise": "ColdChain Logistics",
            "model": "Isolation Forest + XGBoost ETA + Google OR-Tools VRPTW/CVRP",
            "model_version": self.MODEL_VERSION,
            "tomato_safe_temp_c": f"{settings.tomato_safe_temp_min_c}-{settings.tomato_safe_temp_max_c}",
            "train_normal_rows": int(len(X_train)),
            "val_rows": int(len(X_val)),
            "test_rows": int(len(X_test)),
            "anomaly_precision_pct": round(prec * 100.0, 2),
            "anomaly_recall_pct": round(rec * 100.0, 2),
            "anomaly_f1_pct": round(f1 * 100.0, 2),
            "anomaly_roc_auc": round(auc, 4),
            "eta_mae_min": eta_m["test_mae_min"],
            "eta_mape_pct": eta_m["test_mape_pct"],
            "eta_beats_baseline": eta_m["beats_baseline"],
            "cvrp_naive_distance_km": cvrp_bench["naive_distance_km"],
            "cvrp_optimized_distance_km": cvrp_bench["optimized_distance_km"],
            "cvrp_distance_reduction_pct": cvrp_bench["distance_reduction_pct"],
            "vrptw_optimized_distance_km": vrptw_bench["optimized_distance_km"],
            "vrptw_time_window_violations": vrptw_bench["time_window_violations"],
            "target_route_reduction": ">= 10.0%",
            "target_met": (f1 >= 0.90 and cvrp_bench["distance_reduction_pct"] >= 10.0),
            "train_time_ms": round(train_ms, 1),
            "avg_inference_ms": round(inf_ms, 4),
        }
        return self.metrics

    def detect_anomalies(self, readings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Isolation Forest + Standardized Tomato SOP Threshold (7.0-12.0 C)."""
        X = np.array([[float(r["temp_c"]), float(r["humidity_pct"]), float(r["power_kw"])] for r in readings])
        preds = self.iforest.predict(X)
        scores = -self.iforest.decision_function(X)
        affected_zones = []
        max_score = 0.0
        t_min = settings.tomato_safe_temp_min_c
        t_max = settings.tomato_safe_temp_max_c

        for idx, (p, s) in enumerate(zip(preds, scores)):
            temp = float(readings[idx]["temp_c"])
            if p == -1 or temp > t_max or temp < t_min:
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
            "safe_temp_band_c": [t_min, t_max],
            "previous_capacity_kg": 3000.0,
            "effective_capacity_kg": effective_cap,
            "capacity_drop_pct": round(((3000.0 - effective_cap) / 3000.0) * 100.0, 1),
            "anomaly_score": round(max_score, 3),
        }

    def solve_vrptw(
        self,
        scenario: str = "NORMAL",
        demands_kg: Optional[List[int]] = None,
        vehicle_capacities: Optional[List[int]] = None,
        traffic_level: int = 1,
        external_time_windows: Optional[Dict[str, tuple[int, int]]] = None,
    ) -> Dict[str, Any]:
        """Solve Capacitated Vehicle Routing Problem with Time Windows (VRPTW) via Google OR-Tools + XGBoost ETA."""
        dist_matrix = [
            [0, 42, 28, 19, 48, 54],   # 0: Koperasi_Hub
            [42, 0, 31, 34, 14, 26],   # 1: SuperMart_DC
            [28, 31, 0, 16, 36, 39],   # 2: FreshFood_Plant
            [19, 34, 16, 0, 38, 35],   # 3: ColdChain_WH01
            [48, 14, 36, 38, 0, 22],   # 4: SuperMart_B2
            [54, 26, 39, 35, 22, 0],   # 5: Partner3PL_WH
        ]
        # Scenario adjustments (road traffic / vehicle breakdown / cold storage drop)
        time_mult = 1.45 if scenario == "ROAD_DISRUPTION" else (1.15 if traffic_level == 2 else 1.0)
        if scenario == "VEHICLE_BREAKDOWN":
            caps = [2500, 2500]  # V003 down, 2 larger reefers handle consolidated load
            vehicle_ids = ["V001 (Reefer 7-12°C)", "V004 (Reefer 7-12°C)"]
        else:
            caps = vehicle_capacities if vehicle_capacities is not None else [2000, 2000, 1500]
            vehicle_ids = [f"V00{i+1} (Reefer 7-12°C)" for i in range(len(caps))]

        demands = demands_kg if demands_kg is not None else (
            [0, 1200, 1800, 0, 800, 700] if scenario == "COLD_STORAGE_DROP" else [0, 1200, 1500, 500, 800, 500]
        )
        # Time windows in minutes from 08:00 WIB (0 = 08:00, 240 = 12:00, 360 = 14:00)
        time_windows = [
            (0, 420),    # 0: Depot 08:00-15:00
            (30, 260),   # 1: SuperMart_DC (deadline 12:20)
            (15, 220),   # 2: FreshFood_Plant (FEFO H003 priority <= 11:40)
            (0, 300),    # 3: ColdChain_WH01
            (40, 320),   # 4: SuperMart_B2
            (30, 340),   # 5: Partner3PL_WH
        ]
        # Dynamic Cross-Enterprise Dock Window Handshake from FreshFood & SuperMart
        synced_nodes: List[str] = []
        if external_time_windows:
            name_to_idx = {meta["name"]: idx for idx, meta in enumerate(COLDCHAIN_NODE_META)}
            for node_name, win in external_time_windows.items():
                if node_name in name_to_idx:
                    lo_m, hi_m = int(win[0]), int(win[1])
                    if 0 <= lo_m < hi_m <= 420:
                        time_windows[name_to_idx[node_name]] = (lo_m, hi_m)
                        synced_nodes.append(node_name)
        service_time_min = [0, 15, 15, 10, 12, 12]
        # Travel time matrix (minutes) at avg 40 km/h scaled by scenario
        time_matrix = [
            [int(round((d / 40.0) * 60.0 * time_mult)) + (service_time_min[i] if i != j else 0) for j, d in enumerate(row)]
            for i, row in enumerate(dist_matrix)
        ]

        naive_km = sum(2 * dist_matrix[0][i] for i in range(1, len(demands)) if demands[i] > 0)

        manager = pywrapcp.RoutingIndexManager(len(dist_matrix), len(caps), 0)
        routing = pywrapcp.RoutingModel(manager)

        def dist_cb(from_i, to_i):
            return dist_matrix[manager.IndexToNode(from_i)][manager.IndexToNode(to_i)]

        dist_idx = routing.RegisterTransitCallback(dist_cb)
        routing.SetArcCostEvaluatorOfAllVehicles(dist_idx)

        def demand_cb(from_i):
            return demands[manager.IndexToNode(from_i)]

        dem_idx = routing.RegisterUnaryTransitCallback(demand_cb)
        routing.AddDimensionWithVehicleCapacity(dem_idx, 0, caps, True, "Capacity")

        def time_cb(from_i, to_i):
            return time_matrix[manager.IndexToNode(from_i)][manager.IndexToNode(to_i)]

        time_idx = routing.RegisterTransitCallback(time_cb)
        routing.AddDimension(time_idx, 45, 420, False, "Time")
        time_dim = routing.GetDimensionOrDie("Time")
        for loc_idx, (tw_start, tw_end) in enumerate(time_windows):
            if loc_idx == 0:
                continue
            index = manager.NodeToIndex(loc_idx)
            time_dim.CumulVar(index).SetRange(tw_start, tw_end)

        # Allow dropping zero-demand nodes cleanly
        for node_i in range(1, len(demands)):
            if demands[node_i] == 0:
                routing.AddDisjunction([manager.NodeToIndex(node_i)], 0)

        params = pywrapcp.DefaultRoutingSearchParameters()
        params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        params.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        params.time_limit.seconds = 2

        sol = routing.SolveWithParameters(params)
        routes = []
        opt_km = 0
        tw_violations = 0

        if sol:
            for v in range(len(caps)):
                idx = routing.Start(v)
                r_nodes = []
                r_coords = []
                r_dist = 0
                r_load = 0
                while not routing.IsEnd(idx):
                    node = manager.IndexToNode(idx)
                    meta = COLDCHAIN_NODE_META[node]
                    arr_min = sol.Min(time_dim.CumulVar(idx))
                    if arr_min > time_windows[node][1]:
                        tw_violations += 1
                    r_nodes.append(meta["name"])
                    r_coords.append({"name": meta["name"], "lat": meta["lat"], "lon": meta["lon"], "arrival_min": arr_min})
                    r_load += demands[node]
                    prev = idx
                    idx = sol.Value(routing.NextVar(idx))
                    r_dist += routing.GetArcCostForVehicle(prev, idx, v)
                end_node = manager.IndexToNode(idx)
                end_meta = COLDCHAIN_NODE_META[end_node]
                r_nodes.append(end_meta["name"])
                r_coords.append({"name": end_meta["name"], "lat": end_meta["lat"], "lon": end_meta["lon"], "arrival_min": sol.Min(time_dim.CumulVar(idx))})
                if r_load > 0:
                    eff_traffic = 2 if scenario == "ROAD_DISRUPTION" else traffic_level
                    eta_pred = self.eta_model.predict_eta_minutes(
                        distance_km=float(r_dist),
                        traffic_level=eff_traffic,
                        num_stops=max(1, len(r_nodes) - 2),
                    )
                    routes.append({
                        "truck": vehicle_ids[v],
                        "stops": r_nodes,
                        "coords": r_coords,
                        "load_kg": r_load,
                        "capacity_kg": caps[v],
                        "utilization_pct": round((r_load / caps[v]) * 100.0, 1),
                        "distance_km": r_dist,
                        "predicted_eta_min": eta_pred["predicted_duration_min"],
                        "eta_band_min": eta_pred["error_band_min"],
                        "temp_compliance_c": f"{settings.tomato_safe_temp_min_c}-{settings.tomato_safe_temp_max_c}°C",
                    })
                    opt_km += r_dist
        else:
            opt_km = naive_km
            tw_violations = 1

        reduction = ((naive_km - opt_km) / max(naive_km, 1)) * 100.0
        return {
            "solver": "Google OR-Tools VRPTW + XGBoost ETA",
            "scenario": scenario,
            "feasible": sol is not None,
            "routes": routes,
            "naive_distance_km": float(naive_km),
            "optimized_distance_km": float(opt_km),
            "distance_reduction_pct": round(reduction, 2),
            "time_window_violations": tw_violations,
            "transport_cost_rp": float(opt_km * 9500),
            "node_coordinates": COLDCHAIN_NODE_META,
            "dock_windows_synced_nodes": synced_nodes,
        }

    @staticmethod
    def solve_cvrp_demo(
        demands_kg: List[int] | None = None,
        vehicle_capacities: List[int] | None = None,
    ) -> Dict[str, Any]:
        """Backward-compatible CVRP solver benchmark."""
        dist_matrix = [
            [0, 42, 28, 19, 48, 54],
            [42, 0, 31, 34, 14, 26],
            [28, 31, 0, 16, 36, 39],
            [19, 34, 16, 0, 38, 35],
            [48, 14, 36, 38, 0, 22],
            [54, 26, 39, 35, 22, 0],
        ]
        node_names = [m["name"] for m in COLDCHAIN_NODE_META]
        demands = demands_kg if demands_kg is not None else [0, 1200, 1500, 500, 800, 500]
        caps = vehicle_capacities if vehicle_capacities is not None else [2000, 2000, 1500]

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
            pickle.dump({"iforest": self.iforest, "eta_model": self.eta_model, "metrics": self.metrics}, f)

    @classmethod
    def load(cls, path: Path = ARTIFACTS_DIR / "coldchain_iforest.pkl") -> "ColdChainMonitoringAndRouting":
        inst = cls()
        with open(path, "rb") as f:
            data = pickle.load(f)
        inst.iforest = data["iforest"]
        if "eta_model" in data:
            inst.eta_model = data["eta_model"]
        else:
            inst.eta_model.train_and_evaluate()
        inst.metrics = data["metrics"]
        return inst
