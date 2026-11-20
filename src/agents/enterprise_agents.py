"""Five Independent Enterprise Agents (AGT-01 through AGT-05) with Heterogeneous ML + LLM Backbones."""
from __future__ import annotations

from typing import Any, Dict, List

from src.agents.base import BaseEnterpriseAgent
from src.llm.router import HeterogeneousLLMRouter
from src.models.agrofarm_rf import AgroFarmYieldModel
from src.models.coldchain_iforest_cvrp import ColdChainMonitoringAndRouting
from src.models.freshfood_cnn import FreshFoodVisualGradingModel
from src.models.koperasi_lgbm import KoperasiPriceModel
from src.models.supermart_xgb import SuperMartDemandModel
from src.protocols.fipa_epcis import (
    A2AMessage,
    AgentCard,
    EPCISEvent,
    FIPAPerformative,
    HarvestBatch,
    SensorElement,
    SensorReport,
    now_wib_iso,
)


class AgroFarmAgent(BaseEnterpriseAgent):
    """AGT-01: Qwen 2.5 14B Instruct + Random Forest Regression (PostgreSQL)."""

    def __init__(self, router: HeterogeneousLLMRouter, model: AgroFarmYieldModel):
        super().__init__("AGT-01", router)
        self.model = model
        # Strictly private internal policy (NEVER shared via API)
        self._private_hpp_per_kg = 4800.0
        self._max_autonomous_deferral_hours = 48

    def card(self) -> AgentCard:
        return self.get_agent_card(
            endpoint="/api/v1/agrofarm",
            capabilities=["predict_yield_rf", "evaluate_harvest_deferral"],
            private_fields=["production_cost_per_kg", "farmer_personal_id", "plot_gps_private"],
            autonomy="Semi-Otonom (penundaan > 48 jam butuh konfirmasi Farm Manager)",
        )

    def forecast_harvest(self, conversation_id: str, plot_records: List[Dict[str, Any]], use_showcase_volumes: bool = False) -> A2AMessage:
        preds = self.model.predict_batch(plot_records)
        if use_showcase_volumes:
            for p, rec in zip(preds, plot_records):
                p["predicted_kg"] = float(rec["actual_yield_kg"])

        reasoning = self.router.invoke_structured(
            self.agent_id,
            "forecast_harvest_and_schedule",
            {"plots": preds},
            lambda ctx: {
                "thought": "Ran Random Forest Regression on active tomato plots; stripping private HPP before sharing.",
                "total_supply_kg": round(sum(x["predicted_kg"] for x in ctx["plots"]), 1),
                "batches": ctx["plots"],
                "production_cost_per_kg": self._private_hpp_per_kg,  # Intentionally tested against outbound firewall!
            },
        )
        epcis = EPCISEvent(
            type="ObjectEvent",
            action="ADD",
            bizStep="urn:epcglobal:cbv:bizstep:commissioning",
            disposition="urn:epcglobal:cbv:disp:active",
            readPoint={"id": "urn:epc:id:sgln:8991234.00001.FARM01"},
            epcList=[f"urn:epc:id:lgtin:8991234.0001.{b['lot_id']}" for b in preds],
        )
        return self.build_safe_message(conversation_id, "AGT-06:GlobalOrchestrator", FIPAPerformative.INFORM, reasoning, epcis_event=epcis)

    def respond_harvest_deferral(self, conversation_id: str, defer_hours: int, lot_id: str) -> A2AMessage:
        def _resolve(ctx: Dict[str, Any]) -> Dict[str, Any]:
            if ctx["defer_hours"] <= self._max_autonomous_deferral_hours:
                return {
                    "decision": "ACCEPT_PROPOSAL",
                    "lot_id": ctx["lot_id"],
                    "deferred_hours": ctx["defer_hours"],
                    "field_ripeness_risk": "LOW",
                    "reason": "Penundaan <= 48 jam aman di blok lahan Grade A tanpa penurunan kelas mutu.",
                }
            return {
                "decision": "COUNTER_PROPOSE",
                "lot_id": ctx["lot_id"],
                "max_safe_deferral_hours": 48,
                "reason_code": "EXCEEDS_AUTONOMOUS_DEFERRAL_LIMIT",
            }

        res = self.router.invoke_structured(
            self.agent_id, "evaluate_harvest_deferral", {"defer_hours": defer_hours, "lot_id": lot_id}, _resolve
        )
        perf = FIPAPerformative.ACCEPT_PROPOSAL if res["decision"] == "ACCEPT_PROPOSAL" else FIPAPerformative.COUNTER_PROPOSE
        return self.build_safe_message(conversation_id, "AGT-06:GlobalOrchestrator", perf, res)


class KoperasiAgent(BaseEnterpriseAgent):
    """AGT-02: Claude 3.5 Sonnet + LightGBM Price Forecaster + Contract Net Auction (MySQL)."""

    def __init__(self, router: HeterogeneousLLMRouter, model: KoperasiPriceModel):
        super().__init__("AGT-02", router)
        self.model = model
        # Strictly private floor prices per grade (Rp/kg) — NEVER shared!
        self._private_floor_prices = {"A": 9000.0, "B": 6200.0, "C": 3400.0}

    def card(self) -> AgentCard:
        return self.get_agent_card(
            endpoint="/api/v1/koperasi",
            capabilities=["aggregate_farmer_lots", "predict_market_price_lgbm", "run_contract_net_auction"],
            private_fields=["floor_price_rp", "coop_margin_rp", "farmer_payout_detail"],
            autonomy="Otonom Terbatas (harga >= floor_price privat; diskon > 15% butuh persetujuan Cooperative Manager)",
        )

    def aggregate_and_quote(self, conversation_id: str, batches: List[Dict[str, Any]], use_showcase_prices: bool = False) -> A2AMessage:
        showcase_prices = {"A": 10000.0, "B": 7000.0, "C": 4000.0}
        quoted = []
        for b in batches:
            g = b["grade"]
            ask = showcase_prices[g] if use_showcase_prices else self.model.predict_price(grade=g, qty_kg=b["predicted_kg"], shelf_life_days=b["shelf_life_days"])
            quoted.append({
                "lot_id": b["lot_id"],
                "qty_kg": b["predicted_kg"],
                "grade": g,
                "shelf_life_days": b["shelf_life_days"],
                "ask_price_rp": ask,
            })

        res = self.router.invoke_structured(
            self.agent_id,
            "aggregate_and_quote_ask_prices",
            {"quoted": quoted},
            lambda ctx: {
                "thought": "Consolidated farmer lots and generated LightGBM market reference ask prices.",
                "aggregated_lots": ctx["quoted"],
                "floor_price_rp": self._private_floor_prices,  # Filtered by outbound security firewall!
            },
        )
        epcis = EPCISEvent(
            type="AggregationEvent",
            action="ADD",
            bizStep="urn:epcglobal:cbv:bizstep:packing",
            disposition="urn:epcglobal:cbv:disp:in_progress",
            readPoint={"id": "urn:epc:id:sgln:8991234.00002.KOOP01"},
        )
        return self.build_safe_message(conversation_id, "AGT-06:GlobalOrchestrator", FIPAPerformative.INFORM, res, epcis_event=epcis)

    def evaluate_proposal(self, conversation_id: str, proposed_allocations: List[Dict[str, Any]], unallocated: Dict[str, float], round_num: int, offered_price_override: Dict[str, float] | None = None) -> A2AMessage:
        """Verify local policy: reject if unsold > 5% or offered price breaches private floor price."""
        offered_price_override = offered_price_override or {}

        def _resolve(ctx: Dict[str, Any]) -> Dict[str, Any]:
            total_qty = sum(a["qty_kg"] for a in ctx["allocations"]) + sum(ctx["unallocated"].values())
            unsold_qty = sum(ctx["unallocated"].values())
            unsold_pct = (unsold_qty / max(total_qty, 1.0)) * 100.0

            # Check private floor price violation
            for a in ctx["allocations"]:
                grade = a["grade"]
                offer_p = ctx["price_override"].get(a["lot_id"], a.get("agreed_price_rp", self._private_floor_prices[grade] + 600.0))
                if offer_p < self._private_floor_prices[grade]:
                    return {
                        "decision": "REJECT_PROPOSAL",
                        "reason_code": "BELOW_FARMER_VIABILITY_THRESHOLD",
                        "conflict_lot": a["lot_id"],
                        "requested_counter_price_rp": self._private_floor_prices[grade] + 300.0,
                        "unsold_pct": round(unsold_pct, 2),
                    }

            if unsold_pct > 5.0:
                return {
                    "decision": "COUNTER_PROPOSE",
                    "reason_code": "UNSOLD_INVENTORY_EXCEEDS_5PCT",
                    "unsold_pct": round(unsold_pct, 2),
                    "requested_actions": ["REQUEST_OVERTIME_SLOT", "REQUEST_ALT_BUYER_OR_3PL"],
                }

            return {
                "decision": "ACCEPT_PROPOSAL",
                "unsold_pct": round(unsold_pct, 2),
                "note": "Seluruh lot memenuhi ambang kelayakan petani dan target unsold <= 5%.",
            }

        res = self.router.invoke_structured(
            self.agent_id,
            f"evaluate_allocation_round_{round_num}",
            {"allocations": proposed_allocations, "unallocated": unallocated, "price_override": offered_price_override},
            _resolve,
        )
        perf_map = {
            "ACCEPT_PROPOSAL": FIPAPerformative.ACCEPT_PROPOSAL,
            "COUNTER_PROPOSE": FIPAPerformative.COUNTER_PROPOSE,
            "REJECT_PROPOSAL": FIPAPerformative.REJECT_PROPOSAL,
        }
        return self.build_safe_message(
            conversation_id,
            "AGT-06:GlobalOrchestrator",
            perf_map[res["decision"]],
            res,
            protocol="FIPA-CONTRACT-NET",
            negotiation_round=round_num,
        )

    def negotiate_p2p_with_buyers(
        self,
        conversation_id: str,
        lot_id: str,
        grade: str,
        qty_kg: float,
        bids: List[Dict[str, Any]],
        round_num: int,
    ) -> A2AMessage:
        floor_p = self._private_floor_prices.get(grade, 3400.0)
        # Allow up to 8% emergency discount in round >= 2 to prevent perishable spoilage
        effective_floor = floor_p * (0.92 if round_num >= 2 else 1.0)
        auction_res = self.model.evaluate_contract_net_bids(lot_id, qty_kg, effective_floor, bids)

        res = self.router.invoke_structured(
            self.agent_id,
            f"contract_net_auction_round_{round_num}",
            {"lot_id": lot_id, "qty_kg": qty_kg, "auction_result": auction_res},
            lambda ctx: ctx["auction_result"],
        )
        perf = FIPAPerformative.ACCEPT_PROPOSAL if res["status"] == "ACCEPT_PROPOSAL" else FIPAPerformative.REJECT_PROPOSAL
        return self.build_safe_message(
            conversation_id,
            "AGT-06:GlobalOrchestrator",
            perf,
            res,
            protocol="FIPA-CONTRACT-NET",
            negotiation_round=round_num,
        )


class FreshFoodAgent(BaseEnterpriseAgent):
    """AGT-03: Gemini 2.5 Flash (Multimodal) + 2D-Conv CNN + Food Safety Guardrail + FEFO Scheduler (MongoDB)."""

    def __init__(self, router: HeterogeneousLLMRouter, model: FreshFoodVisualGradingModel):
        super().__init__("AGT-03", router)
        self.model = model
        self.regular_capacity_kg = 2000.0
        self.overtime_capacity_kg = 500.0
        self.overtime_surcharge_rp = 800.0

    def card(self) -> AgentCard:
        return self.get_agent_card(
            endpoint="/api/v1/freshfood",
            capabilities=["classify_tomato_cnn", "verify_food_safety_lab", "schedule_factory_fefo"],
            private_fields=["secret_recipe_formula", "internal_line_cost_rp"],
            autonomy="Kritis-Terproteksi (Penolakan food safety mutlak; overtime > 500 kg wajib persetujuan Factory Manager)",
        )

    def inspect_and_report_capacity(
        self,
        conversation_id: str,
        lots: List[Dict[str, Any]],
        failed_food_safety_lots: List[str] | None = None,
    ) -> A2AMessage:
        failed_set = set(failed_food_safety_lots or [])
        qc_results = []
        for lot in lots:
            is_failed = lot["lot_id"] in failed_set
            lab = {
                "ph_level": 4.95 if is_failed else 4.32,
                "brix_pct": 4.9,
                "pesticide_residue_ppm": 0.08 if is_failed else 0.015,
                "microbial_pass": not is_failed,
            }
            defect = 0.24 if is_failed else (0.02 if lot["grade"] == "A" else (0.08 if lot["grade"] == "B" else 0.14))
            safety = self.model.verify_food_safety_hard_block(lab, defect)
            qc_results.append({
                "lot_id": lot["lot_id"],
                "cnn_grade": lot["grade"],
                "cnn_confidence": 0.94,
                "defect_ratio": defect,
                "food_safety_approved": safety["food_safety_approved"],
                "hard_block_triggered": safety["hard_block_triggered"],
                "violation_reasons": safety["violation_reasons"],
            })

        res = self.router.invoke_structured(
            self.agent_id,
            "multimodal_qc_inspection_and_capacity",
            {"qc_results": qc_results},
            lambda ctx: {
                "thought": "Verified CNN visual grades and food safety lab metrics with multimodal VLM.",
                "regular_capacity_kg": self.regular_capacity_kg,
                "overtime_available_kg": self.overtime_capacity_kg,
                "overtime_surcharge_rp_per_kg": self.overtime_surcharge_rp,
                "qc_reports": ctx["qc_results"],
            },
        )
        epcis = EPCISEvent(
            type="TransformationEvent",
            action="OBSERVE",
            bizStep="urn:epcglobal:cbv:bizstep:inspecting",
            disposition="urn:epcglobal:cbv:disp:conformant",
            readPoint={"id": "urn:epc:id:sgln:8991234.00003.PLANT01"},
        )
        return self.build_safe_message(conversation_id, "AGT-06:GlobalOrchestrator", FIPAPerformative.INFORM, res, epcis_event=epcis)

    def respond_overtime_cfp(self, conversation_id: str, lot_id: str, grade: str, qty_kg: float, round_num: int) -> A2AMessage:
        def _resolve(ctx: Dict[str, Any]) -> Dict[str, Any]:
            grant_qty = min(float(ctx["qty_kg"]), self.overtime_capacity_kg)
            base_price = 7000.0 if ctx["grade"] == "B" else 4000.0
            # Cost sharing: factory absorbs 50% of Rp800 overtime surcharge in round >= 1
            surcharge_share = 400.0 if ctx["round_num"] == 1 else 250.0
            return {
                "buyer_id": "FreshFood_OT",
                "lot_id": ctx["lot_id"],
                "grade": ctx["grade"],
                "qty_kg": grant_qty,
                "proposed_slot": "OVERTIME_SHIFT_TODAY",
                "base_buy_price_rp": base_price,
                "overtime_surcharge_share_rp": surcharge_share,
                "offer_price_rp": base_price - surcharge_share,
                "food_safety_verified": True,
            }

        res = self.router.invoke_structured(
            self.agent_id,
            f"overtime_cfp_response_round_{round_num}",
            {"lot_id": lot_id, "grade": grade, "qty_kg": qty_kg, "round_num": round_num},
            _resolve,
        )
        return self.build_safe_message(
            conversation_id, "AGT-02:KoperasiTani", FIPAPerformative.PROPOSE, res, protocol="FIPA-CONTRACT-NET", negotiation_round=round_num
        )


class ColdChainAgent(BaseEnterpriseAgent):
    """AGT-04: Llama 3.1 8B Instruct (Edge) + Isolation Forest + Google OR-Tools CVRP (TimescaleDB)."""

    def __init__(self, router: HeterogeneousLLMRouter, model: ColdChainMonitoringAndRouting):
        super().__init__("AGT-04", router)
        self.model = model
        self.normal_capacity_kg = 3000.0
        self.backup_3pl_capacity_kg = 1500.0

    def card(self) -> AgentCard:
        return self.get_agent_card(
            endpoint="/api/v1/coldchain",
            capabilities=["detect_temp_anomaly_iforest", "optimize_cvrp_ortools", "query_3pl_backup_capacity"],
            private_fields=["other_client_gps", "internal_fleet_lease_rp", "logistics_margin_rp"],
            autonomy="Reaktif-Otonom (Alert instan otomatis; kontrak sewa 3PL diverifikasi Warehouse Manager)",
        )

    def check_telemetry_and_capacity(self, conversation_id: str, inject_cold_failure: bool = False) -> A2AMessage:
        if inject_cold_failure:
            readings = [
                {"zone_id": "Z-1", "temp_c": 9.3, "humidity_pct": 88.2, "power_kw": 14.3},
                {"zone_id": "Z-2", "temp_c": 14.8, "humidity_pct": 79.0, "power_kw": 2.1},
                {"zone_id": "Z-3", "temp_c": 15.3, "humidity_pct": 77.4, "power_kw": 1.8},
            ]
        else:
            readings = [
                {"zone_id": "Z-1", "temp_c": 9.2, "humidity_pct": 88.5, "power_kw": 14.2},
                {"zone_id": "Z-2", "temp_c": 9.5, "humidity_pct": 87.9, "power_kw": 14.5},
                {"zone_id": "Z-3", "temp_c": 9.4, "humidity_pct": 88.1, "power_kw": 14.4},
            ]

        anom = self.model.detect_anomalies(readings)
        cvrp = self.model.solve_cvrp_demo()

        res = self.router.invoke_structured(
            self.agent_id,
            "edge_telemetry_and_cvrp_snapshot",
            {"anomaly": anom, "cvrp_summary": {"opt_km": cvrp["optimized_distance_km"], "reduction_pct": cvrp["distance_reduction_pct"]}},
            lambda ctx: {
                "event_type": "COLD_STORAGE_FAILURE" if ctx["anomaly"]["anomaly_detected"] else "NORMAL_OPERATION",
                "previous_capacity_kg": ctx["anomaly"]["previous_capacity_kg"],
                "effective_capacity_kg": ctx["anomaly"]["effective_capacity_kg"],
                "capacity_drop_pct": ctx["anomaly"]["capacity_drop_pct"],
                "affected_zones": ctx["anomaly"]["affected_zones"],
                "anomaly_score": ctx["anomaly"]["anomaly_score"],
                "recommended_3pl_backup_kg": self.backup_3pl_capacity_kg if ctx["anomaly"]["anomaly_detected"] else 0.0,
                "cvrp_optimized_km": ctx["cvrp_summary"]["opt_km"],
                "cvrp_distance_reduction_pct": ctx["cvrp_summary"]["reduction_pct"],
            },
        )
        max_temp = max(r["temp_c"] for r in readings)
        epcis = EPCISEvent(
            type="ObjectEvent",
            action="OBSERVE",
            bizStep="urn:epcglobal:cbv:bizstep:storing",
            disposition="urn:epcglobal:cbv:disp:non_sellable_other" if anom["anomaly_detected"] else "urn:epcglobal:cbv:disp:active",
            readPoint={"id": "urn:epc:id:sgln:8991234.00004.WH-CC01"},
            sensorElementList=[
                SensorElement(
                    sensorMetadata={"deviceID": "SENS-Z1-Z3", "time": now_wib_iso()},
                    sensorReport=[
                        SensorReport(
                            value=max_temp,
                            exception="HIGH_TEMP_ALARM" if anom["anomaly_detected"] else None,
                        )
                    ],
                )
            ],
        )
        return self.build_safe_message(conversation_id, "AGT-06:GlobalOrchestrator", FIPAPerformative.INFORM, res, epcis_event=epcis)


class SuperMartAgent(BaseEnterpriseAgent):
    """AGT-05: Mistral Small 3 (24B) + XGBoost Demand Forecaster + Newsvendor PO (MySQL)."""

    def __init__(self, router: HeterogeneousLLMRouter, model: SuperMartDemandModel):
        super().__init__("AGT-05", router)
        self.model = model
        # Strictly private ceiling price (Rp/kg)
        self._private_ceiling_price_grade_a = 10500.0
        self._private_ceiling_price_grade_b_surge = 6800.0

    def card(self) -> AgentCard:
        return self.get_agent_card(
            endpoint="/api/v1/supermart",
            capabilities=["forecast_demand_xgboost", "compute_purchase_order", "validate_procurement_offer"],
            private_fields=["ceiling_price_rp", "retail_margin_pct", "customer_pii"],
            autonomy="Otonom Terbatas (PO otomatis jika <= ceiling_price; substitusi Grade B butuh persetujuan Purchasing Manager)",
        )

    def forecast_and_plan_po(self, conversation_id: str, demand_override_kg: float | None = None, demand_surge: bool = False) -> A2AMessage:
        if demand_override_kg is not None:
            pred_demand = float(demand_override_kg)
        else:
            pred_demand = self.model.forecast_total_chain_demand(day_of_week=5 if demand_surge else 2, is_promo=1 if demand_surge else 0)
            if demand_surge:
                pred_demand = max(pred_demand, 2800.0)

        po = self.model.compute_newsvendor_po(pred_demand)

        res = self.router.invoke_structured(
            self.agent_id,
            "demand_forecast_and_po_planning",
            {"po": po, "demand_surge": demand_surge},
            lambda ctx: {
                "demand_forecast_kg": ctx["po"]["forecast_demand_kg"],
                "recommended_po_kg": ctx["po"]["recommended_po_kg"],
                "demand_surge_flag": ctx["demand_surge"],
                "grade_b_substitution_allowed": ctx["demand_surge"],
                "max_grade_b_share_pct": 30.0 if ctx["demand_surge"] else 0.0,
                "ceiling_price_rp": self._private_ceiling_price_grade_a,  # Blocked by outbound firewall!
            },
        )
        epcis = EPCISEvent(
            type="TransactionEvent",
            action="OBSERVE",
            bizStep="urn:epcglobal:cbv:bizstep:ordering",
            disposition="urn:epcglobal:cbv:disp:in_progress",
            readPoint={"id": "urn:epc:id:sgln:8991234.00005.SM-DC"},
        )
        return self.build_safe_message(conversation_id, "AGT-06:GlobalOrchestrator", FIPAPerformative.INFORM, res, epcis_event=epcis)
