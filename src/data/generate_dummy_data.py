"""Synthetic Multi-Enterprise Dummy Dataset Generator (Bab 4).

Generates causally coherent datasets across 5 heterogeneous enterprises:
1. AgroFarm (PostgreSQL schema): 1,200 historical harvest rows + 90 active lots
2. Koperasi Tani (MySQL schema): 1,500 market price & negotiation rows
3. FreshFood Processing (MongoDB JSON): 3,000 QC inspection docs + synthetic RGB tomato images
4. ColdChain Logistics (TimescaleDB schema): 10,000 IoT telemetry rows + 500 delivery routes
5. SuperMart (MySQL schema): 3,285 POS retail sales rows (1,095 days x 3 stores)
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw

from config.settings import DATA_DIR, settings


def generate_agrofarm_data(rng: np.random.Generator, out_dir: Path) -> Dict[str, int]:
    """Generate 1,200 historical rows + 90 active harvest batches (PostgreSQL schema)."""
    n_hist = 1200
    start_date = datetime(2023, 11, 20)
    plots = ["PLT-01", "PLT-02", "PLT-03", "PLT-04", "PLT-05"]

    rows = []
    private_rows = []
    for idx in range(n_hist):
        dt = start_date + timedelta(days=int(idx * 1095 / n_hist))
        day_of_year = dt.timetuple().tm_yday
        seasonal_rain = 18.0 + 14.0 * np.sin(2 * np.pi * (day_of_year - 30) / 365.0)
        plot_id = plots[idx % len(plots)]
        area_ha = float(np.round(rng.uniform(0.65, 1.45), 2))
        avg_temp_c = float(np.round(25.5 - 1.5 * np.sin(2 * np.pi * day_of_year / 365.0) + rng.normal(0, 1.3), 1))
        rainfall_mm = float(np.round(max(0.0, seasonal_rain + rng.normal(0, 6.0)), 1))
        soil_moisture_pct = float(np.round(np.clip(52.0 + 0.55 * rainfall_mm + rng.normal(0, 4.5), 38.0, 88.0), 1))
        fertilizer_kg_ha = float(np.round(rng.uniform(140.0, 210.0), 1))
        crop_age_days = int(rng.integers(70, 86))

        # Agronomic yield model (non-linear interaction of temp, moisture, fertilizer, area)
        temp_factor = np.exp(-0.5 * ((avg_temp_c - 24.8) / 4.2) ** 2)
        moist_factor = np.exp(-0.5 * ((soil_moisture_pct - 66.0) / 14.0) ** 2)
        fert_factor = 0.78 + 0.35 * ((fertilizer_kg_ha - 140.0) / 70.0)
        base_yield_per_ha = 1780.0 * temp_factor * moist_factor * fert_factor
        actual_yield_kg = float(np.round(max(450.0, area_ha * base_yield_per_ha + rng.normal(0, 75.0)), 1))

        # Grade mix correlation with stress (temp/rain)
        stress = max(0.0, (avg_temp_c - 26.0) * 0.12 + max(0.0, rainfall_mm - 24.0) * 0.015)
        a_share = float(np.clip(0.55 - stress + rng.normal(0, 0.06), 0.15, 0.85))
        b_share = float(np.clip(0.32 + 0.4 * stress + rng.normal(0, 0.04), 0.10, 0.60))
        c_share = max(0.05, 1.0 - a_share - b_share)
        norm = a_share + b_share + c_share
        a_pct, b_pct = int(round(100 * a_share / norm)), int(round(100 * b_share / norm))
        c_pct = 100 - a_pct - b_pct

        lot_id = f"HIST-{idx+1:04d}"
        rows.append({
            "lot_id": lot_id,
            "harvest_date": dt.strftime("%Y-%m-%d"),
            "plot_id": plot_id,
            "area_ha": area_ha,
            "avg_temp_c": avg_temp_c,
            "soil_moisture_pct": soil_moisture_pct,
            "rainfall_mm": rainfall_mm,
            "fertilizer_kg_ha": fertilizer_kg_ha,
            "crop_age_days": crop_age_days,
            "actual_yield_kg": actual_yield_kg,
            "predicted_grade_mix": f"A:{a_pct}%, B:{b_pct}%, C:{c_pct}%",
        })
        private_rows.append({
            "lot_id": lot_id,
            "production_cost_per_kg": float(np.round(rng.uniform(4200, 5600), 0)),
            "farmer_personal_id": f"FRM-{100 + (idx % 35)}",
            "plot_gps_private": f"-6.{70 + (idx % 9):02d}, 107.{55 + (idx % 9):02d}",
        })

    df_hist = pd.DataFrame(rows)
    df_hist.to_csv(out_dir / "agrofarm_harvest_history.csv", index=False)
    pd.DataFrame(private_rows).to_csv(out_dir / "agrofarm_private_costs.csv", index=False)

    # 90 active lots starting with exact PRD showcase lots H001, H002, H003
    active_rows = [
        {"lot_id": "H001", "harvest_date": "2026-11-20", "plot_id": "PLT-01", "area_ha": 1.20, "avg_temp_c": 24.5,
         "soil_moisture_pct": 68.2, "rainfall_mm": 12.4, "fertilizer_kg_ha": 185.0, "crop_age_days": 75,
         "actual_yield_kg": 2000.0, "grade": "A", "shelf_life_days": 5},
        {"lot_id": "H002", "harvest_date": "2026-11-20", "plot_id": "PLT-02", "area_ha": 0.95, "avg_temp_c": 26.1,
         "soil_moisture_pct": 62.5, "rainfall_mm": 18.0, "fertilizer_kg_ha": 170.0, "crop_age_days": 78,
         "actual_yield_kg": 1500.0, "grade": "B", "shelf_life_days": 3},
        {"lot_id": "H003", "harvest_date": "2026-11-20", "plot_id": "PLT-03", "area_ha": 0.70, "avg_temp_c": 28.4,
         "soil_moisture_pct": 54.0, "rainfall_mm": 32.5, "fertilizer_kg_ha": 150.0, "crop_age_days": 82,
         "actual_yield_kg": 1000.0, "grade": "C", "shelf_life_days": 2},
    ]
    grades = ["A", "B", "C"]
    sl_map = {"A": 5, "B": 3, "C": 2}
    for k in range(4, 91):
        g = grades[(k - 1) % 3]
        dt = datetime(2026, 11, 20) + timedelta(days=(k - 1) // 3)
        active_rows.append({
            "lot_id": f"H{k:03d}",
            "harvest_date": dt.strftime("%Y-%m-%d"),
            "plot_id": plots[k % len(plots)],
            "area_ha": float(np.round(rng.uniform(0.7, 1.3), 2)),
            "avg_temp_c": float(np.round(rng.uniform(23.5, 29.0), 1)),
            "soil_moisture_pct": float(np.round(rng.uniform(52.0, 74.0), 1)),
            "rainfall_mm": float(np.round(rng.uniform(8.0, 35.0), 1)),
            "fertilizer_kg_ha": float(np.round(rng.uniform(150.0, 195.0), 1)),
            "crop_age_days": int(rng.integers(72, 84)),
            "actual_yield_kg": float(np.round(rng.uniform(900.0, 2200.0), 0)),
            "grade": g,
            "shelf_life_days": sl_map[g],
        })
    pd.DataFrame(active_rows).to_csv(out_dir / "agrofarm_active_lots.csv", index=False)
    return {"agrofarm_history": len(df_hist), "agrofarm_active": len(active_rows)}


def generate_koperasi_data(rng: np.random.Generator, out_dir: Path) -> Dict[str, int]:
    """Generate 1,500 market price & negotiation history rows (MySQL schema)."""
    n_rows = 1500
    start_date = datetime(2023, 11, 20)
    grades = ["A", "B", "C"]
    base_prices = {"A": 10000.0, "B": 7000.0, "C": 4000.0}
    sl_map = {"A": 5, "B": 3, "C": 2}
    buyers = {"A": "SuperMart", "B": "FreshFood", "C": "FreshFood"}

    rows = []
    for idx in range(n_rows):
        dt = start_date + timedelta(days=int(idx * 1095 / n_rows))
        month = dt.month
        season = "Wet" if month in (10, 11, 12, 1, 2, 3) else "Dry"
        season_mult = 1.08 if season == "Wet" else 0.94
        grade = grades[idx % 3]
        regional_supply_ton = float(np.round(rng.uniform(18.0, 52.0), 1))
        supply_effect = -38.0 * (regional_supply_ton - 35.0)
        qty_kg = float(np.round(rng.uniform(500.0, 2200.0), 0))
        shelf_life = sl_map[grade]

        market_ref = float(np.round(max(2500.0, base_prices[grade] * season_mult + supply_effect + rng.normal(0, 280.0)), -2))
        floor_price = float(np.round(market_ref * rng.uniform(0.86, 0.91), -2))
        buyer = buyers[grade] if rng.random() > 0.12 else "AltBuyer-01"
        init_bid = float(np.round(market_ref * rng.uniform(0.84, 0.99), -2))
        rounds = int(rng.integers(1, 4))
        if buyer == "AltBuyer-01" and init_bid < floor_price * 0.96:
            status = "REJECTED"
            final_price = np.nan
            rounds = 3
        else:
            status = "AGREED"
            final_price = float(np.round(max(floor_price, 0.5 * (market_ref + init_bid)), -2))

        rows.append({
            "tx_id": f"TX-{idx+1:04d}",
            "tx_date": dt.strftime("%Y-%m-%d"),
            "lot_id": f"LOT-{idx+1:04d}",
            "grade": grade,
            "season": season,
            "month": month,
            "regional_supply_ton": regional_supply_ton,
            "qty_kg": qty_kg,
            "shelf_life_days": shelf_life,
            "market_ref_price_rp": market_ref,
            "floor_price_rp": floor_price,  # Strictly Private
            "buyer_id": buyer,
            "initial_bid_rp": init_bid,
            "final_agreed_rp": final_price,
            "rounds": rounds,
            "status": status,
        })

    df = pd.DataFrame(rows)
    df.to_csv(out_dir / "koperasi_market_negotiations.csv", index=False)
    return {"koperasi_negotiations": len(df)}


def _synthesize_tomato_rgb(rng: np.random.Generator, grade: str, size: int = 32) -> np.ndarray:
    """Synthesize a realistic 32x32 RGB tomato image reflecting grade visual characteristics."""
    img = Image.new("RGB", (size, size), (242, 245, 240))
    draw = ImageDraw.Draw(img)

    if grade == "A":
        radius = int(rng.integers(11, 14))
        base_col = (int(rng.integers(195, 232)), int(rng.integers(32, 58)), int(rng.integers(25, 45)))
        n_defects = 0 if rng.random() > 0.15 else 1
    elif grade == "B":
        radius = int(rng.integers(9, 12))
        base_col = (int(rng.integers(175, 212)), int(rng.integers(60, 105)), int(rng.integers(28, 52)))
        n_defects = int(rng.integers(1, 3))
    elif grade == "C":
        radius = int(rng.integers(7, 10))
        base_col = (int(rng.integers(150, 195)), int(rng.integers(85, 130)), int(rng.integers(32, 62)))
        n_defects = int(rng.integers(3, 6))
    else:  # Reject
        radius = int(rng.integers(6, 10))
        base_col = (int(rng.integers(95, 145)), int(rng.integers(75, 115)), int(rng.integers(35, 65)))
        n_defects = int(rng.integers(6, 12))

    cx, cy = size // 2 + int(rng.integers(-1, 2)), size // 2 + int(rng.integers(-1, 2))
    draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=base_col)
    # Green stem calyx
    draw.ellipse([cx - 2, cy - radius - 1, cx + 2, cy - radius + 2], fill=(42, 118, 45))

    for _ in range(n_defects):
        dx = int(rng.integers(-max(1, radius - 2), max(2, radius - 1)))
        dy = int(rng.integers(-max(1, radius - 2), max(2, radius - 1)))
        dr = int(rng.integers(1, 3))
        draw.ellipse([cx + dx - dr, cy + dy - dr, cx + dx + dr, cy + dy + dr], fill=(68, 48, 34))

    arr = np.asarray(img, dtype=np.float32)
    noise = rng.normal(0, 6.0, arr.shape)
    return np.clip(arr + noise, 0, 255).astype(np.uint8)


def generate_freshfood_data(rng: np.random.Generator, out_dir: Path) -> Dict[str, int]:
    """Generate 3,000 MongoDB QC inspection documents + synthetic RGB image tensor dataset."""
    n_docs = 3000
    grades = ["A", "B", "C", "Reject"]
    probs = [0.38, 0.34, 0.20, 0.08]
    start_dt = datetime(2025, 11, 20, 7, 0)

    docs: List[Dict] = []
    images = np.zeros((n_docs, 32, 32, 3), dtype=np.uint8)
    labels = []

    sample_img_dir = out_dir / "generated_images"
    sample_img_dir.mkdir(parents=True, exist_ok=True)

    for idx in range(n_docs):
        grade = str(rng.choice(grades, p=probs))
        arr = _synthesize_tomato_rgb(rng, grade, size=32)
        images[idx] = arr
        labels.append(grade)

        if idx < 12:
            Image.fromarray(arr).resize((128, 128)).save(sample_img_dir / f"tomato_{idx+1:03d}_grade_{grade}.png")

        if grade == "A":
            diam = float(np.round(rng.uniform(58.5, 70.0), 1))
            ripe = float(np.round(rng.uniform(0.76, 0.90), 2))
            defect = float(np.round(rng.uniform(0.005, 0.045), 3))
            sl = 5
            route = "FRESH_RETAIL"
        elif grade == "B":
            diam = float(np.round(rng.uniform(50.5, 57.8), 1))
            ripe = float(np.round(rng.uniform(0.85, 0.95), 2))
            defect = float(np.round(rng.uniform(0.055, 0.118), 3))
            sl = 3
            route = "STANDARD_SAUCE_PROCESSING"
        elif grade == "C":
            diam = float(np.round(rng.uniform(42.0, 49.8), 1))
            ripe = float(np.round(rng.uniform(0.92, 0.98), 2))
            defect = float(np.round(rng.uniform(0.122, 0.195), 3))
            sl = 2
            route = "IMMEDIATE_SAUCE_PROCESSING_FEFO"
        else:
            diam = float(np.round(rng.uniform(36.0, 52.0), 1))
            ripe = float(np.round(rng.uniform(0.94, 1.00), 2))
            defect = float(np.round(rng.uniform(0.21, 0.42), 3))
            sl = 0
            route = "REJECT_COMPOST"

        ph = float(np.round(rng.uniform(4.05, 4.58) if grade != "Reject" else rng.uniform(4.65, 5.2), 2))
        brix = float(np.round(rng.uniform(4.4, 5.8), 1))
        pest = float(np.round(rng.uniform(0.005, 0.045) if grade != "Reject" else rng.uniform(0.055, 0.12), 3))
        microbial_pass = bool(grade != "Reject" and (rng.random() > 0.03 if grade == "C" else True))
        food_safety_ok = bool(microbial_pass and pest <= 0.05 and 4.0 <= ph <= 4.6 and defect <= 0.20)
        if not food_safety_ok:
            route = "REJECT_FOOD_SAFETY_HARD_BLOCK"

        ts = start_dt + timedelta(hours=int(idx * 3))
        docs.append({
            "inspection_id": f"QC-{ts.strftime('%Y%m%d')}-{idx+1:04d}",
            "lot_id": f"QC-LOT-{idx+1:04d}",
            "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%S+07:00"),
            "image_index": idx,
            "visual_metrics": {
                "avg_diameter_mm": diam,
                "color_ripeness_idx": ripe,
                "surface_defect_ratio": defect,
                "ground_truth_grade": grade,
            },
            "food_safety_lab": {
                "ph_level": ph,
                "brix_pct": brix,
                "pesticide_residue_ppm": pest,
                "microbial_pass": microbial_pass,
                "food_safety_approved": food_safety_ok,
            },
            "estimated_shelf_life_days": sl,
            "recommended_route": route,
        })

    with open(out_dir / "freshfood_tomato_qc.json", "w", encoding="utf-8") as f:
        json.dump(docs, f, indent=2)
    np.savez_compressed(out_dir / "freshfood_tomato_images.npz", images=images, labels=np.array(labels))
    return {"freshfood_qc_docs": len(docs), "freshfood_rgb_images": len(images)}


def generate_coldchain_data(rng: np.random.Generator, out_dir: Path) -> Dict[str, int]:
    """Generate 10,000 TimescaleDB IoT telemetry rows (15-min interval) + 500 delivery routes."""
    n_rows = 10000
    start_ts = datetime(2026, 8, 8, 0, 0)
    zones = ["Z-1", "Z-2", "Z-3"]

    rows = []
    # Inject ~3.5% realistic compressor failure episodes (contiguous blocks)
    anomaly_mask = np.zeros(n_rows, dtype=int)
    fault_starts = rng.choice(np.arange(7200, n_rows - 40), size=16, replace=False)
    for fs in fault_starts:
        dur = int(rng.integers(8, 28))
        anomaly_mask[fs : fs + dur] = 1

    for idx in range(n_rows):
        ts = start_ts + timedelta(minutes=15 * idx)
        zone = zones[idx % 3]
        is_anom = int(anomaly_mask[idx])
        if is_anom == 0:
            temp_c = float(np.round(np.clip(9.4 + rng.normal(0, 0.75), 7.2, 11.8), 1))
            hum_pct = float(np.round(np.clip(88.0 + rng.normal(0, 1.8), 82.0, 93.0), 1))
            power_kw = float(np.round(np.clip(14.3 + rng.normal(0, 0.6), 12.0, 16.5), 1))
            usable_cap = 1000.0
            note = "Normal"
        else:
            temp_c = float(np.round(rng.uniform(13.6, 17.2), 1))
            hum_pct = float(np.round(rng.uniform(70.0, 80.5), 1))
            power_kw = float(np.round(rng.uniform(1.2, 4.5), 1))
            usable_cap = 0.0
            note = "Compressor Fault"

        used_cap = float(np.round(rng.uniform(350.0, 900.0), 0))
        rows.append({
            "ts": ts.strftime("%Y-%m-%d %H:%M"),
            "facility_id": "WH-CC01",
            "zone_id": zone,
            "temp_c": temp_c,
            "humidity_pct": hum_pct,
            "power_kw": power_kw,
            "usable_cap_kg": usable_cap,
            "used_cap_kg": used_cap,
            "is_anomaly": is_anom,
            "event_note": note,
        })

    df_tel = pd.DataFrame(rows)
    df_tel.to_csv(out_dir / "coldchain_iot_telemetry.csv", index=False)

    # 500 delivery route records across 6 supply chain nodes
    nodes = ["Koperasi_Hub", "SuperMart_DC", "FreshFood_Plant", "ColdChain_WH01", "Partner3PL_WH", "AltMarket_Hub"]
    dist_lookup = {
        ("Koperasi_Hub", "SuperMart_DC"): 42.5,
        ("Koperasi_Hub", "FreshFood_Plant"): 28.0,
        ("Koperasi_Hub", "ColdChain_WH01"): 18.5,
        ("ColdChain_WH01", "FreshFood_Plant"): 16.0,
        ("ColdChain_WH01", "SuperMart_DC"): 34.0,
        ("Koperasi_Hub", "Partner3PL_WH"): 54.0,
        ("Koperasi_Hub", "AltMarket_Hub"): 47.0,
        ("FreshFood_Plant", "SuperMart_DC"): 31.0,
    }
    pairs = list(dist_lookup.keys())
    trucks = [("TRK-01", 2000.0, 9500.0), ("TRK-02", 2000.0, 9500.0), ("TRK-03", 1500.0, 8800.0), ("TRK-EXT", 2000.0, 12500.0)]
    route_rows = []
    for r in range(500):
        orig, dest = pairs[r % len(pairs)]
        base_km = dist_lookup[(orig, dest)]
        dist_km = float(np.round(base_km + rng.normal(0, 1.5), 1))
        trk_id, trk_cap, c_km = trucks[r % len(trucks)]
        route_rows.append({
            "route_id": f"RT-{r+1:03d}",
            "origin_node": orig,
            "dest_node": dest,
            "distance_km": max(8.0, dist_km),
            "est_duration_min": int(round(max(15.0, dist_km * 1.55 + rng.normal(0, 4.0)))),
            "truck_id": trk_id,
            "truck_cap_kg": trk_cap,
            "cost_per_km_rp": c_km,
            "reefer_temp_c": float(np.round(rng.uniform(8.5, 10.2), 1)),
        })
    df_rt = pd.DataFrame(route_rows)
    df_rt.to_csv(out_dir / "coldchain_delivery_routes.csv", index=False)
    return {"coldchain_telemetry": len(df_tel), "coldchain_routes": len(df_rt)}


def generate_supermart_data(rng: np.random.Generator, out_dir: Path) -> Dict[str, int]:
    """Generate 3,285 retail POS rows (1,095 days x 3 stores, MySQL schema)."""
    start_date = datetime(2023, 11, 21)
    stores = [("SM-01", 680.0), ("SM-02", 650.0), ("SM-03", 620.0)]

    rows = []
    for day in range(1095):
        dt = start_date + timedelta(days=day)
        doy = dt.timetuple().tm_yday
        dow = dt.weekday()
        is_weekend = 1 if dow >= 5 else 0
        season_flag = "Wet" if dt.month in (10, 11, 12, 1, 2, 3) else "Dry"
        season_mult = 1.05 + 0.08 * np.sin(2 * np.pi * doy / 365.0)

        for store_id, base_dem in stores:
            is_promo = 1 if (rng.random() < (0.28 if is_weekend else 0.12)) else 0
            price_rp = float(13000.0 if is_promo else (14500.0 if season_flag == "Wet" else 14000.0))
            price_elast = (14500.0 - price_rp) * 0.045
            weekend_uplift = 1.24 if is_weekend else 1.0
            promo_uplift = 1.18 if is_promo else 1.0
            demand = base_dem * season_mult * weekend_uplift * promo_uplift + price_elast + rng.normal(0, 32.0)
            demand_kg = float(np.round(max(250.0, demand), 1))
            opening_stock = float(np.round(demand_kg * rng.uniform(0.92, 1.12), 1))
            stockout = float(np.round(max(0.0, demand_kg - opening_stock), 1))
            spoilage = float(np.round(max(0.0, (opening_stock - demand_kg) * 0.18), 1))

            rows.append({
                "sales_date": dt.strftime("%Y-%m-%d"),
                "store_id": store_id,
                "sku_grade": "Grade_A",
                "day_of_week": dow,
                "month": dt.month,
                "price_rp": price_rp,
                "is_promo": is_promo,
                "is_weekend": is_weekend,
                "season_flag": season_flag,
                "opening_stock_kg": opening_stock,
                "demand_sold_kg": demand_kg,
                "stockout_kg": stockout,
                "spoilage_kg": spoilage,
            })

    df = pd.DataFrame(rows)
    df.to_csv(out_dir / "supermart_pos_sales.csv", index=False)
    return {"supermart_pos_sales": len(df)}


def generate_all(seed: int | None = None) -> Dict[str, int]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed if seed is not None else settings.random_seed)
    summary: Dict[str, int] = {}
    summary.update(generate_agrofarm_data(rng, DATA_DIR))
    summary.update(generate_koperasi_data(rng, DATA_DIR))
    summary.update(generate_freshfood_data(rng, DATA_DIR))
    summary.update(generate_coldchain_data(rng, DATA_DIR))
    summary.update(generate_supermart_data(rng, DATA_DIR))
    summary["total_records"] = sum(v for k, v in summary.items() if k != "freshfood_rgb_images")

    with open(DATA_DIR / "dataset_manifest.json", "w", encoding="utf-8") as f:
        json.dump({"seed": seed if seed is not None else settings.random_seed, "counts": summary}, f, indent=2)
    return summary


if __name__ == "__main__":
    counts = generate_all()
    print("Generated AgriChain Dummy Datasets:")
    for k, v in counts.items():
        print(f"  - {k}: {v:,}")
