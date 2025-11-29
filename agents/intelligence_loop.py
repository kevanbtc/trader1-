"""
RECURSIVE INTELLIGENCE LOOP
Self-upgrading feedback mechanism for trading system

This module processes trading intelligence through the Universal Ingestor Framework
and generates targeted questions for continuous system improvement.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum


class StructureType(Enum):
    ORDERBOOK = "orderbook"
    FLOW = "flow"
    VOLATILITY = "volatility"
    CORRELATION = "correlation"
    LIQUIDITY = "liquidity"
    TIMING = "timing"
    OTHER = "other"


class EdgeType(Enum):
    TIMING = "timing"
    INFORMATION = "information"
    POSITIONING = "positioning"
    EXECUTION = "execution"
    LIQUIDITY = "liquidity"
    MICROSTRUCTURE = "microstructure"
    STRUCTURAL_FLOW = "structural_flow"
    PSYCHOLOGY = "psychology"


class DirectiveType(Enum):
    HEURISTIC = "heuristic"
    MONITOR = "monitor"
    DETECTOR = "detector"
    SIGNAL = "signal"


class Confidence(Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class StructuralExtraction:
    """Layer 1: Structural components of trading intelligence"""
    intel_id: str
    timestamp: str
    structure_type: StructureType
    actors: List[str]
    pattern_description: str
    edge_type: EdgeType
    edge_description: str
    raw_intel: str


@dataclass
class OperatingRule:
    """Layer 2: Machine-executable trading rules"""
    directive_id: str
    directive_type: DirectiveType
    rule: Dict[str, Any]
    monitoring: Dict[str, Any]
    detection: Dict[str, Any]
    prediction: Dict[str, Any]


@dataclass
class ValidationAnalysis:
    """Layer 3: Risk and validation framework"""
    validation_id: str
    failure_modes: List[Dict[str, Any]]
    robustness: Dict[str, Any]
    false_signal_analysis: Dict[str, Any]
    data_requirements: Dict[str, Any]


@dataclass
class SystemIntegration:
    """Layer 4: Integration into execution systems"""
    integration_id: str
    mcp_agents: List[Dict[str, Any]]
    n8n_workflows: List[Dict[str, Any]]
    trading_ai: Dict[str, Any]
    data_tracking: Dict[str, Any]
    execution: Dict[str, Any]


@dataclass
class Question:
    """Individual question for recursive improvement"""
    id: str
    question: str
    answer_required: bool
    answer_type: str
    answer: Optional[str] = None


@dataclass
class RecursiveQuestions:
    """Layer 5: Questions for continuous improvement"""
    questions_id: str
    mandatory_questions: List[Question]
    conditional_questions: List[Question]


class IntelligenceLoop:
    """
    Main class for processing trading intelligence through the
    Universal Trading Intel Ingestor Framework
    """
    
    def __init__(self):
        self.processed_intel: List[Dict] = []
        self.learning_history: List[Dict] = []
        
    def generate_intel_id(self, descriptor: str) -> str:
        """Generate unique intel ID"""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        descriptor_clean = descriptor.upper().replace(" ", "_")[:20]
        return f"INTEL_{timestamp}_{descriptor_clean}"
    
    def layer1_structural_extraction(self, raw_intel: str, metadata: Dict) -> StructuralExtraction:
        """
        Layer 1: Extract structural components from raw trading intelligence
        
        This would typically use LLM processing to identify:
        - Market structure components
        - Actor identification
        - Mechanical rules/behaviors
        - Edge location
        """
        
        intel_id = self.generate_intel_id(metadata.get("descriptor", "PATTERN"))
        
        extraction = StructuralExtraction(
            intel_id=intel_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            structure_type=StructureType(metadata.get("structure_type", "other")),
            actors=metadata.get("actors", ["retail", "mm"]),
            pattern_description=metadata.get("pattern_description", ""),
            edge_type=EdgeType(metadata.get("edge_type", "timing")),
            edge_description=metadata.get("edge_description", ""),
            raw_intel=raw_intel
        )
        
        return extraction
    
    def layer2_operating_rules(self, extraction: StructuralExtraction) -> List[OperatingRule]:
        """
        Layer 2: Convert structural insights into operating rules
        
        Generates:
        - Trading heuristics
        - Monitoring requirements
        - Detection patterns
        - Predictive signals
        """
        
        rules = []
        
        # Example rule generation (would be LLM-powered in production)
        directive_id = f"DIR_{extraction.intel_id}_001"
        
        rule = OperatingRule(
            directive_id=directive_id,
            directive_type=DirectiveType.HEURISTIC,
            rule={
                "if_conditions": [
                    "condition extracted from pattern"
                ],
                "then_action": "anticipated outcome or action",
                "confidence": Confidence.MEDIUM.value,
                "timeframe": "5m"
            },
            monitoring={
                "data_sources": ["orderbook", "flow"],
                "frequency": "1s",
                "thresholds": {}
            },
            detection={
                "conditions": [],
                "sequence_required": True,
                "confirmations": []
            },
            prediction={
                "expected_outcome": "price movement or behavior",
                "historical_success_rate": 0.0,
                "expected_magnitude": "20-50 bps",
                "expected_duration": "5-15 minutes"
            }
        )
        
        rules.append(rule)
        return rules
    
    def layer3_validation(self, rule: OperatingRule) -> ValidationAnalysis:
        """
        Layer 3: Analyze risk and validation requirements
        """
        
        validation_id = f"VAL_{rule.directive_id}"
        
        analysis = ValidationAnalysis(
            validation_id=validation_id,
            failure_modes=[
                {
                    "condition": "low liquidity environment",
                    "likelihood": "MEDIUM",
                    "mitigation": "add minimum volume filter"
                }
            ],
            robustness={
                "frequency": "frequent",
                "asset_scope": "major_coins",
                "time_decay": "unknown"
            },
            false_signal_analysis={
                "estimated_fpr": 0.3,
                "filters": ["volume_confirmation", "trend_alignment"],
                "confirmations": ["orderbook_confirmation"]
            },
            data_requirements={
                "required_sources": ["orderbook_l2", "trade_flow"],
                "historical_available": False,
                "backtest_feasible": True
            }
        )
        
        return analysis
    
    def layer4_system_integration(self, rule: OperatingRule) -> SystemIntegration:
        """
        Layer 4: Map directives to execution systems
        """
        
        integration_id = f"INT_{rule.directive_id}"
        
        integration = SystemIntegration(
            integration_id=integration_id,
            mcp_agents=[
                {
                    "agent": "market_monitor",
                    "role": "monitor",
                    "permissions": ["read_orderbook", "read_trades"],
                    "endpoints": ["/api/orderbook", "/api/trades"]
                }
            ],
            n8n_workflows=[
                {
                    "workflow_id": "WF_PATTERN_DETECTOR",
                    "trigger": "pattern detected",
                    "actions": ["log_signal", "notify_telegram"]
                }
            ],
            trading_ai={
                "model_update_required": True,
                "signal_weight": 0.3,
                "correlated_signals": []
            },
            data_tracking={
                "new_features": ["pattern_strength", "confirmation_count"],
                "labels": ["pattern_success", "pattern_failure"],
                "analysis_needed": ["historical_backtest", "regime_correlation"]
            },
            execution={
                "venues": ["BINANCE_SPOT"],
                "order_types": ["LIMIT", "MARKET"],
                "latency_requirement_ms": 500
            }
        )
        
        return integration
    
    def layer5_recursive_questions(self, extraction: StructuralExtraction) -> RecursiveQuestions:
        """
        Layer 5: Generate targeted questions for clarification and improvement
        """
        
        questions_id = f"Q_{extraction.intel_id}"
        
        mandatory = [
            Question(
                id="Q1",
                question="What timeframe does this insight hold strongest on? (1m / 3m / 5m / 15m / 1h / 4h / daily)",
                answer_required=True,
                answer_type="timeframe"
            ),
            Question(
                id="Q2",
                question="Is this pattern driven more by spot flow, derivative open interest, or ETF arbitrage?",
                answer_required=True,
                answer_type="flow_type"
            ),
            Question(
                id="Q3",
                question="What *invalidates* this pattern? What breaks it?",
                answer_required=True,
                answer_type="text"
            ),
            Question(
                id="Q4",
                question="Is the behavior more common during liquidity hunts or during trending legs?",
                answer_required=True,
                answer_type="market_phase"
            ),
            Question(
                id="Q5",
                question="Does this require orderbook data, funding rate data, CVD/Delta, or options flow to detect properly?",
                answer_required=True,
                answer_type="data_source"
            ),
            Question(
                id="Q6",
                question="What conditions amplify this effect — volatility? low liquidity? big news windows?",
                answer_required=True,
                answer_type="text"
            ),
            Question(
                id="Q7",
                question="Is this pattern universal across assets or isolated to Bitcoin/ETH?",
                answer_required=True,
                answer_type="asset_scope"
            ),
            Question(
                id="Q8",
                question="Does your system have the data sources needed to implement this, or do we need to add one?",
                answer_required=True,
                answer_type="infrastructure"
            ),
            Question(
                id="Q9",
                question="What is the *intended output* of this rule — signal? filter? automatic trade? warning?",
                answer_required=True,
                answer_type="output_type"
            ),
            Question(
                id="Q10",
                question="Is this a microstructure edge, structural flow edge, or psychology edge?",
                answer_required=True,
                answer_type="edge_classification"
            )
        ]
        
        # Conditional questions based on context
        conditional = []
        
        if "option" in extraction.raw_intel.lower() or "derivative" in extraction.raw_intel.lower():
            conditional.append(Question(
                id="QC1",
                question="What strike/expiry windows are most relevant?",
                answer_required=False,
                answer_type="text"
            ))
        
        if "event" in extraction.raw_intel.lower() or "news" in extraction.raw_intel.lower():
            conditional.append(Question(
                id="QC2",
                question="How far in advance can this be detected?",
                answer_required=False,
                answer_type="text"
            ))
        
        if "liquidity" in extraction.raw_intel.lower():
            conditional.append(Question(
                id="QC3",
                question="What minimum size threshold makes this meaningful?",
                answer_required=False,
                answer_type="text"
            ))
        
        questions = RecursiveQuestions(
            questions_id=questions_id,
            mandatory_questions=mandatory,
            conditional_questions=conditional
        )
        
        return questions
    
    def process_intel(self, raw_intel: str, metadata: Dict) -> Dict[str, Any]:
        """
        Complete processing pipeline: runs all 5 layers
        
        Args:
            raw_intel: Raw trading intelligence (text)
            metadata: Metadata dict with keys like:
                - descriptor: short description
                - structure_type: orderbook|flow|volatility|etc
                - actors: list of market participants
                - edge_type: timing|information|etc
                
        Returns:
            Complete processed intelligence package
        """
        
        # Layer 1: Structural Extraction
        extraction = self.layer1_structural_extraction(raw_intel, metadata)
        
        # Layer 2: Operating Rules
        operating_rules = self.layer2_operating_rules(extraction)
        
        # Layer 3: Validation for each rule
        validations = [self.layer3_validation(rule) for rule in operating_rules]
        
        # Layer 4: System Integration for each rule
        integrations = [self.layer4_system_integration(rule) for rule in operating_rules]
        
        # Layer 5: Recursive Questions
        questions = self.layer5_recursive_questions(extraction)
        
        # Synthesize complete package
        package = {
            "intel_id": extraction.intel_id,
            "timestamp": extraction.timestamp,
            "layer1_extraction": asdict(extraction),
            "layer2_rules": [asdict(r) for r in operating_rules],
            "layer3_validations": [asdict(v) for v in validations],
            "layer4_integrations": [asdict(i) for i in integrations],
            "layer5_questions": asdict(questions),
            "status": "awaiting_clarification"
        }
        
        self.processed_intel.append(package)
        return package
    
    def answer_questions(self, intel_id: str, answers: Dict[str, str]) -> Dict[str, Any]:
        """
        Process answers to recursive questions and refine the intelligence
        
        Args:
            intel_id: Intel package ID
            answers: Dict mapping question IDs to answers
            
        Returns:
            Refined intelligence package
        """
        
        # Find the intel package
        package = next((p for p in self.processed_intel if p["intel_id"] == intel_id), None)
        if not package:
            raise ValueError(f"Intel package {intel_id} not found")
        
        # Update questions with answers
        questions = package["layer5_questions"]
        for q in questions["mandatory_questions"]:
            if q["id"] in answers:
                q["answer"] = answers[q["id"]]
        
        for q in questions["conditional_questions"]:
            if q["id"] in answers:
                q["answer"] = answers[q["id"]]
        
        # Refine rules based on answers
        # (In production, this would use LLM to update rules intelligently)
        
        # Update status
        package["status"] = "refined"
        package["refinement_timestamp"] = datetime.now(timezone.utc).isoformat()
        package["answers_provided"] = answers
        
        # Log to learning history
        self.learning_history.append({
            "intel_id": intel_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "answers": answers,
            "refined_package": package
        })
        
        return package
    
    def deploy_intelligence(self, intel_id: str) -> Dict[str, Any]:
        """
        Deploy refined intelligence to live systems
        
        Returns deployment manifest with all integration points
        """
        
        package = next((p for p in self.processed_intel if p["intel_id"] == intel_id), None)
        if not package:
            raise ValueError(f"Intel package {intel_id} not found")
        
        if package["status"] != "refined":
            raise ValueError(f"Intel package {intel_id} must be refined before deployment")
        
        deployment = {
            "intel_id": intel_id,
            "deployment_timestamp": datetime.now(timezone.utc).isoformat(),
            "directives": package["layer2_rules"],
            "integrations": package["layer4_integrations"],
            "monitoring_requirements": [r["monitoring"] for r in package["layer2_rules"]],
            "deployment_status": "deployed"
        }
        
        package["status"] = "deployed"
        package["deployment_timestamp"] = deployment["deployment_timestamp"]
        
        return deployment
    
    def observe_and_learn(self, intel_id: str, observations: Dict[str, Any]) -> Dict[str, Any]:
        """
        Complete the recursive loop: observe outcomes and learn
        
        Args:
            intel_id: Intel package ID
            observations: Observed metrics and outcomes
            
        Returns:
            Learning summary with next iteration improvements
        """
        
        learning = {
            "intel_id": intel_id,
            "observation_timestamp": datetime.now(timezone.utc).isoformat(),
            "observations": observations,
            "validated_patterns": [],
            "degrading_patterns": [],
            "confidence_updates": [],
            "recommended_adjustments": [],
            "next_iteration_focus": []
        }
        
        # Analyze observations
        # (In production, this would use LLM and statistical analysis)
        
        # Example learning outcomes
        if observations.get("success_rate", 0) > 0.6:
            learning["validated_patterns"].append({
                "pattern": intel_id,
                "confidence_increase": 0.2,
                "recommendation": "increase signal weight"
            })
        
        if observations.get("false_positive_rate", 1.0) > 0.5:
            learning["degrading_patterns"].append({
                "pattern": intel_id,
                "issue": "high false positive rate",
                "recommendation": "add additional filters"
            })
        
        self.learning_history.append(learning)
        
        return learning
    
    def export_master_rulebook(self, output_path: str = None) -> Dict[str, Any]:
        """
        Generate master rulebook from all processed intelligence
        """
        
        rulebook = {
            "version": "1.0.0",
            "generated": datetime.now(timezone.utc).isoformat(),
            "total_intel_packages": len(self.processed_intel),
            "deployed_packages": len([p for p in self.processed_intel if p["status"] == "deployed"]),
            "intelligence": self.processed_intel,
            "learning_history": self.learning_history
        }
        
        if output_path:
            with open(output_path, 'w') as f:
                json.dump(rulebook, f, indent=2)
        
        return rulebook


# Example usage
if __name__ == "__main__":
    loop = IntelligenceLoop()
    
    # Process sample intelligence
    raw_intel = """
    Observed pattern: When BTC spot volume spikes >2x average within 5 minutes
    while orderbook imbalance shows >70% buy side pressure, price typically
    continues upward for 15-30 minutes. Success rate highest during US trading hours.
    Pattern breaks in low liquidity Asian hours.
    """
    
    metadata = {
        "descriptor": "BTC_VOLUME_SPIKE",
        "structure_type": "flow",
        "actors": ["retail", "institutions"],
        "pattern_description": "Volume spike with orderbook imbalance predicts continuation",
        "edge_type": "timing",
        "edge_description": "Early detection of momentum before price fully reflects flow"
    }
    
    # Run through pipeline
    package = loop.process_intel(raw_intel, metadata)
    print(f"Processed: {package['intel_id']}")
    print(f"Questions generated: {len(package['layer5_questions']['mandatory_questions'])}")
    
    # Answer questions
    answers = {
        "Q1": "5m",
        "Q2": "spot flow",
        "Q3": "Pattern breaks when liquidity drops below 50% of average",
        "Q4": "trending legs",
        "Q5": "orderbook data and trade flow required",
        "Q6": "Amplified during high volatility and US trading hours",
        "Q7": "Pattern strongest on BTC, also works on ETH",
        "Q8": "Need to add real-time orderbook imbalance calculation",
        "Q9": "signal",
        "Q10": "microstructure edge"
    }
    
    refined = loop.answer_questions(package['intel_id'], answers)
    print(f"Refined: {refined['status']}")
    
    # Deploy
    deployment = loop.deploy_intelligence(package['intel_id'])
    print(f"Deployed at: {deployment['deployment_timestamp']}")
    
    # Observe and learn
    observations = {
        "success_rate": 0.68,
        "false_positive_rate": 0.22,
        "avg_profit_per_signal": 45,  # bps
        "total_signals": 156
    }
    
    learning = loop.observe_and_learn(package['intel_id'], observations)
    print(f"Learning captured: {len(learning['validated_patterns'])} validated patterns")
    
    # Export master rulebook
    rulebook = loop.export_master_rulebook("master_rulebook.json")
    print(f"Master rulebook exported: {rulebook['total_intel_packages']} packages")
