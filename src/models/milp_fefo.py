"""Global Optimization Engine: MILP Solver (PuLP/CBC) with FEFO Shelf-Life Spoilage Penalty (Bab 6.2)."""
from __future__ import annotations

import time
from typing import Any, Dict, List

import pulp

from src.protocols.fipa_epcis import HarvestBatch

CHANNELS = ["SuperMart", "FreshFood_Reg", "FreshFood_OT", "ColdStorage", "Partner3PL", "AltBuyer"]


def solve_milp_fefo(
    batches: List[HarvestBatch],
    demand_supermart_kg: float = 2000.0,
    cap_freshfood_reg_kg: float = 2000.0,
    cap_freshfood_ot_kg: float = 500.0,
    cap_cold_storage_kg: float = 3000.0,
    cap_3pl_kg: float = 0.0,
    cap_alt_buyer_kg: float = 0.0,
    allow_grade_b_to_supermart: bool = False,
    allow_overtime: bool = True,
    allow_3pl: bool = False,
    overtime_fixed_cost_rp: float = 250000.0,
    thirdpl_fixed_cost_rp: float = 400000.0,
    base_spoilage_penalty_rp: float = 18000.0,
) -> Dict[str, Any]:
    """Implements exact MILP-FEFO equations from Bab 6.2 using PuLP CBC solver."""
    t0 = time.perf_counter()

    prob = pulp.LpProblem("AgriChain_Global_MILP_FEFO", pulp.LpMaximize)

    # Decision variables
    x = {
        (b.lot_id, j): pulp.LpVariable(f"x_{b.lot_id}_{j}", lowBound=0, cat="Continuous")
        for b in batches
        for j in CHANNELS
    }
    u = {b.lot_id: pulp.LpVariable(f"u_{b.lot_id}", lowBound=0, cat="Continuous") for b in batches}
    z_ot = pulp.LpVariable("z_overtime", cat="Binary")
    z_3pl = pulp.LpVariable("z_3pl", cat="Binary")

    # Economic revenue r_ij and cost c_ij per kg (realistic Indonesian tomato supply chain Rp/kg)
    # Costs include production/acquisition + processing + storage + transport
    def rev_cost(b: HarvestBatch, j: str) -> tuple[float, float]:
        if j == "SuperMart":
            r = 14500.0 if b.grade == "A" else 11200.0  # 20% discount if Grade B substituted during surge
            c = 5000.0 + 420.0                          # farm prod + direct refrigerated haul
        elif j == "FreshFood_Reg":
            r = 11500.0 if b.grade == "B" else (9200.0 if b.grade == "C" else 12000.0)
            c = 4700.0 + 1800.0 + 300.0                 # prod + processing + haul
        elif j == "FreshFood_OT":
            r = 11500.0 if b.grade == "B" else (9200.0 if b.grade == "C" else 12000.0)
            c = 4700.0 + 2600.0 + 300.0                 # +Rp800/kg overtime surcharge
        elif j == "ColdStorage":
            # Stored for D+1 processing/sale (retains value minus storage holding cost)
            r = 10800.0 if b.grade == "B" else 13500.0
            c = 4800.0 + 1800.0 + 650.0 + 380.0         # prod + D+1 proc + cold storage + 2-leg transport
        elif j == "Partner3PL":
            r = 10600.0 if b.grade == "B" else 13200.0
            c = 4800.0 + 1800.0 + 1150.0 + 620.0        # higher 3PL storage + longer transport
        else:  # AltBuyer (secondary wholesale market)
            r = 8500.0 if b.grade == "A" else (6400.0 if b.grade == "B" else 4300.0)
            c = 4600.0 + 480.0
        return r, c

    # Objective function (Eq 6.1): Maximize Net Ecosystem Value - FEFO spoilage penalty - fixed activation costs
    obj_terms = []
    for b in batches:
        for j in CHANNELS:
            r_ij, c_ij = rev_cost(b, j)
            obj_terms.append((r_ij - c_ij) * x[(b.lot_id, j)])
        sl = max(1, b.shelf_life_days)
        obj_terms.append(-(base_spoilage_penalty_rp / sl) * u[b.lot_id])

    obj_terms.append(-overtime_fixed_cost_rp * z_ot)
    obj_terms.append(-thirdpl_fixed_cost_rp * z_3pl)
    prob += pulp.lpSum(obj_terms), "Global_Net_Ecosystem_Value"

    # Constraints
    M = 1e6
    for b in batches:
        # (1) Mass conservation
        prob += pulp.lpSum(x[(b.lot_id, j)] for j in CHANNELS) + u[b.lot_id] == b.qty_kg, f"Mass_{b.lot_id}"

        # (2) Grade & Food Safety compatibility (Hard Block if not food_safety_approved)
        s_i = 1 if b.food_safety_approved else 0
        for j in CHANNELS:
            if j == "SuperMart":
                a_ij = 1 if (b.grade == "A" or (allow_grade_b_to_supermart and b.grade == "B")) else 0
            elif j in ("FreshFood_Reg", "FreshFood_OT"):
                a_ij = 1 if b.grade in ("B", "C") else 0
            elif j in ("ColdStorage", "Partner3PL"):
                a_ij = 1 if b.grade in ("A", "B") else 0
            else:  # AltBuyer
                a_ij = 1 if b.grade in ("A", "B", "C") else 0

            prob += x[(b.lot_id, j)] <= M * a_ij * s_i, f"Compat_{b.lot_id}_{j}"

        # (6) FEFO transit storage ban: SL_i <= 2 MUST NOT sit in ColdStorage or 3PL
        if b.shelf_life_days <= 2:
            prob += x[(b.lot_id, "ColdStorage")] + x[(b.lot_id, "Partner3PL")] == 0, f"FEFO_NoTransit_{b.lot_id}"

    # (3) SuperMart demand cap
    prob += pulp.lpSum(x[(b.lot_id, "SuperMart")] for b in batches) <= demand_supermart_kg, "Cap_SuperMart"
    # If Grade B substitution allowed during surge, cap Grade B at <= 30% of SuperMart demand (System Prompt AGT-05)
    if allow_grade_b_to_supermart:
        prob += (
            pulp.lpSum(x[(b.lot_id, "SuperMart")] for b in batches if b.grade == "B") <= 0.30 * demand_supermart_kg,
            "Cap_SuperMart_GradeB_30pct",
        )

    # (4) FreshFood regular & overtime capacities
    prob += pulp.lpSum(x[(b.lot_id, "FreshFood_Reg")] for b in batches) <= cap_freshfood_reg_kg, "Cap_FF_Reg"
    ot_cap = cap_freshfood_ot_kg if allow_overtime else 0.0
    prob += pulp.lpSum(x[(b.lot_id, "FreshFood_OT")] for b in batches) <= ot_cap * z_ot, "Cap_FF_OT"

    # (5) ColdChain dynamic storage & 3PL capacities
    prob += pulp.lpSum(x[(b.lot_id, "ColdStorage")] for b in batches) <= cap_cold_storage_kg, "Cap_ColdStorage"
    tpl_cap = cap_3pl_kg if allow_3pl else 0.0
    prob += pulp.lpSum(x[(b.lot_id, "Partner3PL")] for b in batches) <= tpl_cap * z_3pl, "Cap_3PL"

    # Secondary wholesale market cap
    prob += pulp.lpSum(x[(b.lot_id, "AltBuyer")] for b in batches) <= cap_alt_buyer_kg, "Cap_AltBuyer"

    solver = pulp.PULP_CBC_CMD(msg=False)
    status_code = prob.solve(solver)
    solve_ms = (time.perf_counter() - t0) * 1000.0

    allocations: List[Dict[str, Any]] = []
    unallocated: Dict[str, float] = {}
    total_qty = sum(b.qty_kg for b in batches)
    total_loss_kg = 0.0
    total_cost = 0.0
    total_rev = 0.0

    for b in batches:
        u_val = round(float(pulp.value(u[b.lot_id]) or 0.0), 2)
        unallocated[b.lot_id] = u_val
        total_loss_kg += u_val
        for j in CHANNELS:
            val = round(float(pulp.value(x[(b.lot_id, j)]) or 0.0), 2)
            if val > 0.01:
                r_ij, c_ij = rev_cost(b, j)
                total_rev += r_ij * val
                total_cost += c_ij * val
                allocations.append({
                    "lot_id": b.lot_id,
                    "grade": b.grade,
                    "shelf_life_days": b.shelf_life_days,
                    "channel": j,
                    "qty_kg": val,
                    "unit_cost_rp": c_ij,
                    "unit_revenue_rp": r_ij,
                })

    ot_active = bool(round(float(pulp.value(z_ot) or 0.0)) == 1)
    tpl_active = bool(round(float(pulp.value(z_3pl) or 0.0)) == 1)
    if ot_active:
        total_cost += overtime_fixed_cost_rp
    if tpl_active:
        total_cost += thirdpl_fixed_cost_rp

    sm_fulfilled = sum(a["qty_kg"] for a in allocations if a["channel"] == "SuperMart")
    ff_used = sum(a["qty_kg"] for a in allocations if a["channel"] in ("FreshFood_Reg", "FreshFood_OT"))
    cc_used = sum(a["qty_kg"] for a in allocations if a["channel"] == "ColdStorage")

    flr_pct = (total_loss_kg / max(total_qty, 1.0)) * 100.0
    total_demand_target = demand_supermart_kg + cap_freshfood_reg_kg
    ofr_pct = min(100.0, ((sm_fulfilled + min(ff_used, cap_freshfood_reg_kg)) / max(total_demand_target, 1.0)) * 100.0)

    return {
        "solver_status": pulp.LpStatus[status_code],
        "solve_time_ms": round(solve_ms, 2),
        "allocations": allocations,
        "unallocated_kg": unallocated,
        "total_supply_kg": round(total_qty, 1),
        "total_loss_kg": round(total_loss_kg, 2),
        "food_loss_rate_pct": round(flr_pct, 2),
        "order_fulfillment_rate_pct": round(ofr_pct, 2),
        "total_supply_chain_cost_rp": round(total_cost, 0),
        "total_ecosystem_revenue_rp": round(total_rev, 0),
        "net_ecosystem_profit_rp": round(total_rev - total_cost, 0),
        "overtime_activated": ot_active,
        "third_pl_activated": tpl_active,
        "freshfood_used_kg": round(ff_used, 1),
        "coldstorage_used_kg": round(cc_used, 1),
        "supermart_fulfilled_kg": round(sm_fulfilled, 1),
    }
