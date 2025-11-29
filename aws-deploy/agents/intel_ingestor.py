"""
Universal Trading Intel Ingestor Framework (v1.0.0)

Transforms raw trading intelligence into actionable directives across 5 layers:
1) Structural Extraction
2) Translation into Operating Rules
3) Risk and Validation
4) System-Level Integration
5) Recursive Upgrade Questions

Provides a single entry point `process_intelligence(raw, context=None)` that returns
all layer artifacts plus a synthesized master package.

This module is self-contained and does not require external services. It uses
lightweight heuristics to populate fields when inputs are free-form.
"""

from __future__ import annotations

import re
import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


# =========================
# Utilities
# =========================

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slugify(text: str, max_len: int = 18) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").upper()
    return s[:max_len] or "INSIGHT"


def _gen_intel_id(text: str) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"INTEL_{ts}_{_slugify(text)}"


def _gen_id(prefix: str, suffix: str) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{prefix}_{ts}_{_slugify(suffix)}"


# =========================
# Layer 1: Structural Extraction
# =========================

STRUCTURE_TYPES = ["orderbook", "flow", "volatility", "correlation", "other"]
ACTOR_CATALOG = {
    "retail": ["retail", "small orders"],
    "mm": ["market maker", "mm", "liquidity provider"],
    "institutions": ["institution", "fund", "desk", "bank"],
    "etf_arb": ["etf", "arb", "etf arbitrage"],
    "algos": ["algo", "algorithm", "bot", "hft"],
}
EDGE_TYPES = ["timing", "information", "positioning", "execution", "liquidity"]


def _guess_structure_type(text: str) -> str:
    t = text.lower()
    if any(k in t for k in ["book", "depth", "bid", "ask", "liquidity pocket", "stop hunt"]):
        return "orderbook"
    if any(k in t for k in ["inflow", "outflow", "cvd", "delta", "funding", "open interest", "oi"]):
        return "flow"
    if any(k in t for k in ["volatility", "vol", "range", "chop", "trend"]):
        return "volatility"
    if any(k in t for k in ["correlat", "pairs", "beta", "lag"]):
        return "correlation"
    return "other"


def _extract_actors(text: str) -> List[str]:
    t = text.lower()
    actors: List[str] = []
    for key, cues in ACTOR_CATALOG.items():
        if any(cue in t for cue in cues):
            actors.append(key)
    # Default to algos if nothing detected (DeFi arbitrage context)
    return actors or ["algos"]


def _guess_edge_type(text: str) -> str:
    t = text.lower()
    if any(k in t for k in ["timing", "session", "time of day", "latency"]):
        return "timing"
    if any(k in t for k in ["insider", "news", "information", "lead/lag"]):
        return "information"
    if any(k in t for k in ["positioning", "crowded", "skew", "liquidation"]):
        return "positioning"
    if any(k in t for k in ["execution", "mev", "routing", "slippage"]):
        return "execution"
    if any(k in t for k in ["provide liquidity", "lp", "maker rebate"]):
        return "liquidity"
    return "execution"


def extract_structural(raw: Any) -> Dict[str, Any]:
    if isinstance(raw, dict):
        text = raw.get("text") or raw.get("description") or json.dumps(raw)
    else:
        text = str(raw or "")
    intel_id = _gen_intel_id(text[:40])
    return {
        "intel_id": intel_id,
        "timestamp": _now_iso(),
        "structure_type": _guess_structure_type(text),
        "actors": _extract_actors(text),
        "pattern_description": text.strip()[:2000],
        "edge_type": _guess_edge_type(text),
        "edge_description": "Edge inferred from described behavior and detected structure",
    }


# =========================
# Layer 2: Operating Rules
# =========================

def _directive_template(intel_id: str, idx: int, d_type: str) -> Dict[str, Any]:
    return {
        "directive_id": f"DIR_{intel_id}_{idx}",
        "directive_type": d_type,
        "rule": {
            "if_conditions": [],
            "then_action": "",
            "confidence": "MEDIUM",
            "timeframe": "5m",
        },
        "monitoring": {
            "data_sources": [],
            "frequency": "1m",
            "thresholds": {},
        },
        "detection": {
            "conditions": [],
            "sequence_required": False,
            "confirmations": [],
        },
        "prediction": {
            "expected_outcome": "",
            "historical_success_rate": 0.5,
            "expected_magnitude": "bps",
            "expected_duration": "15m",
        },
    }


def translate_to_directives(structure: Dict[str, Any]) -> List[Dict[str, Any]]:
    intel_id = structure["intel_id"]
    stype = structure.get("structure_type", "other")
    edge = structure.get("edge_type", "execution")

    directives: List[Dict[str, Any]] = []

    # Heuristic
    d1 = _directive_template(intel_id, 1, "heuristic")
    d1["rule"]["if_conditions"] = [f"{stype}_signal_active", f"edge={edge}"]
    d1["rule"]["then_action"] = "anticipate mean-revert micro-move if spread widens > 10 bps"
    d1["rule"]["confidence"] = "MEDIUM"
    d1["rule"]["timeframe"] = "5m"
    d1["monitoring"]["data_sources"] = ["orderbook", "flow", "funding", "cvd"]
    d1["monitoring"]["frequency"] = "tick" if stype == "orderbook" else "5s"
    d1["monitoring"]["thresholds"] = {"spread_bps": 10, "slippage_bps": 25}
    d1["detection"]["conditions"] = ["spread_bps >= 10", "liquidity_score >= 0.6"]
    d1["prediction"]["expected_outcome"] = "Short-lived spread normalization"

    # Monitor
    d2 = _directive_template(intel_id, 2, "monitor")
    d2["rule"]["if_conditions"] = ["volatility_rising", "gas<1gwei"]
    d2["rule"]["then_action"] = "tighten execution window"
    d2["monitoring"]["data_sources"] = ["gas", "dex_liquidity", "mempool"]
    d2["monitoring"]["frequency"] = "1s"
    d2["monitoring"]["thresholds"] = {"gas_gwei_max": 1.0}
    d2["detection"]["conditions"] = ["net_profit_usd > 5", "profit_bps >= 15"]
    d2["prediction"]["expected_outcome"] = "Higher win rate in low gas regime"

    # Detector
    d3 = _directive_template(intel_id, 3, "detector")
    d3["rule"]["if_conditions"] = ["consensus_sources>=3", "confidence>=0.6"]
    d3["rule"]["then_action"] = "mark as EXECUTABLE"
    d3["monitoring"]["data_sources"] = ["chainlink", "coingecko", "1inch"]
    d3["detection"]["conditions"] = ["max_deviation_pct<=5", "sources_agreed>=3"]
    d3["detection"]["sequence_required"] = True
    d3["prediction"]["expected_outcome"] = "Low false-positive rate"

    # Signal
    d4 = _directive_template(intel_id, 4, "signal")
    d4["rule"]["if_conditions"] = ["regime!=high_vol_crisis", "kill_switch_off"]
    d4["rule"]["then_action"] = "emit BUY_SELL_ARBITRAGE signal"
    d4["rule"]["confidence"] = "HIGH"
    d4["rule"]["timeframe"] = "1m"
    d4["prediction"]["expected_outcome"] = "Executable arbitrage within 60s"

    directives.extend([d1, d2, d3, d4])
    return directives


# =========================
# Layer 3: Risk & Validation
# =========================

def build_validation_for_directive(d: Dict[str, Any]) -> Dict[str, Any]:
    did = d["directive_id"]
    return {
        "validation_id": f"VAL_{did}",
        "failure_modes": [
            {"condition": "oracle stale or disagreeing", "likelihood": "MEDIUM", "mitigation": "require 3+ agreeing sources"},
            {"condition": "gas spike reduces profit", "likelihood": "MEDIUM", "mitigation": "gas cap, postpone"},
            {"condition": "liquidity dries up", "likelihood": "LOW", "mitigation": "min liquidity filter"},
        ],
        "robustness": {
            "frequency": "occasional",
            "asset_scope": "major_coins",
            "time_decay": "degrading",
        },
        "false_signal_analysis": {
            "estimated_fpr": 0.2,
            "filters": ["min sources 3", "max deviation 5%"],
            "confirmations": ["chainlink match", "dex liquidity > 50k"],
        },
        "data_requirements": {
            "required_sources": ["chainlink", "1inch", "coingecko", "dex quotes"],
            "historical_available": True,
            "backtest_feasible": True,
        },
    }


def build_validations(directives: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [build_validation_for_directive(d) for d in directives]


# =========================
# Layer 4: System-Level Integration
# =========================

def build_integration_for_directive(d: Dict[str, Any]) -> Dict[str, Any]:
    did = d["directive_id"]
    intel_id = did.split("DIR_")[-1].split("_")[0]
    return {
        "integration_id": f"INT_{did}",
        "mcp_agents": [
            {
                "agent": "price_validator",
                "role": "monitor",
                "permissions": ["read:quotes", "read:oracle"],
                "endpoints": ["/prices/chainlink", "/prices/1inch", "/prices/coingecko"],
            },
            {"agent": "execution_engine", "role": "execute", "permissions": ["trade:paper"], "endpoints": ["/trade/submit"]},
        ],
        "n8n_workflows": [
            {"workflow_id": "WF_ALERTS", "trigger": "validation_failed", "actions": ["send_telegram", "log_event"]}
        ],
        "trading_ai": {
            "model_update_required": False,
            "signal_weight": 0.6,
            "correlated_signals": ["gas_spike", "liquidity_drop"],
        },
        "data_tracking": {
            "new_features": ["sources_agreed", "max_deviation_pct", "gas_gwei"],
            "labels": ["exec_approved", "exec_skipped"],
            "analysis_needed": ["win_rate_by_consensus", "profit_vs_gas"],
        },
        "execution": {
            "venues": ["UNISWAP_V3", "SUSHISWAP"],
            "order_types": ["market_onchain"],
            "latency_requirement_ms": 1500,
        },
    }


def build_integrations(directives: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [build_integration_for_directive(d) for d in directives]


# =========================
# Layer 5: Recursive Upgrade Questions
# =========================

MANDATORY_QUESTIONS = [
    ("Q1", "What timeframe does this insight hold strongest on? (1m / 3m / 15m / 1h / 4h / daily)", "timeframe"),
    ("Q2", "Is this pattern driven more by spot flow, derivative open interest, or ETF arbitrage?", "flow_type"),
    ("Q3", "What invalidates this pattern? What breaks it?", "text"),
    ("Q4", "Is the behavior more common during liquidity hunts or during trending legs?", "text"),
    ("Q5", "Does this require orderbook data, funding rate data, CVD/Delta, or options flow to detect properly?", "text"),
    ("Q6", "What conditions amplify this effect — volatility? low liquidity? big news windows?", "text"),
    ("Q7", "Is this pattern universal across assets or isolated to Bitcoin/ETH?", "text"),
    ("Q8", "Does your system have the data sources needed to implement this, or do we need to add one?", "text"),
    ("Q9", "What is the intended output of this rule — signal? filter? automatic trade? warning?", "text"),
    ("Q10", "Is this a microstructure edge, structural flow edge, or psychology edge?", "text"),
]


def build_questions_for_intel(intel_id: str, structural: Dict[str, Any], directives: List[Dict[str, Any]]) -> Dict[str, Any]:
    text = structural.get("pattern_description", "")
    conds: List[Dict[str, Any]] = []
    t = text.lower()
    # Conditional triggers
    if any(k in t for k in ["option", "derivative", "oi", "open interest"]):
        conds.append({
            "id": "QC1",
            "question": "What strike/expiry windows are most relevant?",
            "trigger": "derivatives context detected",
            "answer_required": False,
        })
    if any(k in t for k in ["news", "event", "cpi", "fed", "announcement"]):
        conds.append({
            "id": "QC2",
            "question": "How far in advance can this be detected?",
            "trigger": "event-driven context",
            "answer_required": False,
        })
    if any(k in t for k in ["liquidity", "thin", "depth"]):
        conds.append({
            "id": "QC3",
            "question": "What minimum size threshold makes this meaningful?",
            "trigger": "liquidity-based context",
            "answer_required": False,
        })
    if "correlat" in t:
        conds.append({
            "id": "QC4",
            "question": "What is the lag structure between the correlated assets?",
            "trigger": "correlation context",
            "answer_required": False,
        })
    if any(k in t for k in ["asia", "europe", "us session"]):
        conds.append({
            "id": "QC5",
            "question": "Is this session-specific (Asia/Europe/US)?",
            "trigger": "time-dependent wording",
            "answer_required": False,
        })

    return {
        "questions_id": f"Q_{intel_id}",
        "mandatory_questions": [
            {"id": qid, "question": q, "answer_required": True, "answer_type": atype}
            for (qid, q, atype) in MANDATORY_QUESTIONS
        ],
        "conditional_questions": conds,
    }


# =========================
# Synthesis & Orchestrator
# =========================

def synthesize_master(structure: Dict[str, Any], directives: List[Dict[str, Any]],
                      validations: List[Dict[str, Any]], integrations: List[Dict[str, Any]],
                      questions: Dict[str, Any]) -> Dict[str, Any]:
    intel_id = structure["intel_id"]
    return {
        "master_id": _gen_id("MASTER", intel_id),
        "summary": {
            "structure": structure["structure_type"],
            "edge": structure["edge_type"],
            "actors": structure["actors"],
            "headline": structure["pattern_description"][:140],
        },
        "machine": {
            "structure": structure,
            "directives": directives,
            "validations": validations,
            "integrations": integrations,
            "questions": questions,
        },
        "human_readable": f"Insight {intel_id}: {structure['pattern_description'][:280]}",
    }


def process_intelligence(raw: Any, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Process a piece of trading intelligence through all 5 layers.

    Returns a dict with keys:
    - structural (Layer 1)
    - directives (Layer 2)
    - validations (Layer 3)
    - integrations (Layer 4)
    - questions (Layer 5)
    - master (Synthesis)
    """
    structural = extract_structural(raw)
    directives = translate_to_directives(structural)
    validations = build_validations(directives)
    integrations = build_integrations(directives)
    questions = build_questions_for_intel(structural["intel_id"], structural, directives)
    master = synthesize_master(structural, directives, validations, integrations, questions)
    return {
        "structural": structural,
        "directives": directives,
        "validations": validations,
        "integrations": integrations,
        "questions": questions,
        "master": master,
    }


# Simple self-test
if __name__ == "__main__":
    sample = "Spread widens during low-gas Asia session; MMs thin books causing transient 20-40bps inefficiencies."
    pkg = process_intelligence(sample)
    print(json.dumps(pkg, indent=2))
