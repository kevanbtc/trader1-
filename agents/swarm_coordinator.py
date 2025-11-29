"""
🐝 SWARM INTELLIGENCE COORDINATOR
Multi-agent orchestration system for DeFi trading
Each agent has specialized role with optimized prompts for decision-making
"""

import asyncio
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


class AgentRole(Enum):
    """Specialized agent roles in the swarm"""
    SCOUT = "scout"  # Discovers opportunities
    ANALYST = "analyst"  # Deep analysis of opportunities
    STRATEGIST = "strategist"  # Plans execution strategy
    RISK_MANAGER = "risk_manager"  # Validates safety
    EXECUTOR = "executor"  # Executes trades
    MONITOR = "monitor"  # Post-trade monitoring


@dataclass
class AgentPrompt:
    """Enhanced prompt template for agent decision-making"""
    role: AgentRole
    system_prompt: str
    decision_template: str
    success_criteria: List[str]
    failure_patterns: List[str]
    confidence_threshold: float


@dataclass
class SwarmDecision:
    """Collective decision from swarm intelligence"""
    action: str  # EXECUTE, SKIP, WAIT, INVESTIGATE
    confidence: float  # 0-100 aggregate confidence
    agent_votes: Dict[AgentRole, Tuple[str, float, str]]  # role: (vote, confidence, reasoning)
    consensus_level: float  # How aligned are agents (0-1)
    dissenting_opinions: List[str]
    execution_plan: Optional[Dict] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


class SwarmAgent:
    """
    Individual agent with specialized prompt-driven intelligence
    """
    
    def __init__(self, role: AgentRole, prompt: AgentPrompt):
        self.role = role
        self.prompt = prompt
        self.memory: List[Dict] = []  # Recent decisions and outcomes
        self.performance_score = 0.5  # Track agent accuracy (0-1)
        self.decisions_made = 0
        self.correct_predictions = 0
        
    async def analyze(self, opportunity: Dict, market_context: Dict) -> Tuple[str, float, str]:
        """
        Agent analyzes opportunity using role-specific prompt
        Returns: (decision, confidence, reasoning)
        """
        
        # Role-specific analysis
        if self.role == AgentRole.SCOUT:
            return await self._scout_analysis(opportunity, market_context)
        elif self.role == AgentRole.ANALYST:
            return await self._analyst_deep_dive(opportunity, market_context)
        elif self.role == AgentRole.STRATEGIST:
            return await self._strategist_planning(opportunity, market_context)
        elif self.role == AgentRole.RISK_MANAGER:
            return await self._risk_assessment(opportunity, market_context)
        elif self.role == AgentRole.EXECUTOR:
            return await self._executor_validation(opportunity, market_context)
        elif self.role == AgentRole.MONITOR:
            return await self._monitor_evaluation(opportunity, market_context)
        
        return ("ABSTAIN", 0.5, "Unknown role")
    
    async def _scout_analysis(self, opp: Dict, ctx: Dict) -> Tuple[str, float, str]:
        """
        SCOUT: First-line filter - Is this worth investigating?
        Prompt: "You are a SCOUT agent. Your job is to quickly filter opportunities.
        Focus on: spread size, liquidity depth, gas efficiency, market timing.
        Be AGGRESSIVE in finding opportunities but flag risks."
        """
        spread_bps = opp.get('profit_bps', 0)
        net_profit = opp.get('net_profit_usd', 0)
        
        # Quick filters
        if spread_bps < 10:
            return ("SKIP", 0.3, "Spread too small (<10 BPS)")
        
        if net_profit < 5:
            return ("SKIP", 0.4, "Net profit too low (<$5)")
        
        # High-value opportunity
        if spread_bps > 50 and net_profit > 50:
            return ("INVESTIGATE", 0.85, f"High-value: {spread_bps} BPS, ${net_profit:.2f} net - SCOUT APPROVED")
        
        # Medium opportunity
        if spread_bps > 20 and net_profit > 15:
            return ("INVESTIGATE", 0.70, f"Medium potential: {spread_bps} BPS - needs analysis")
        
        # Marginal
        return ("INVESTIGATE", 0.55, f"Marginal opportunity - borderline case")
    
    async def _analyst_deep_dive(self, opp: Dict, ctx: Dict) -> Tuple[str, float, str]:
        """
        ANALYST: Deep technical analysis
        Prompt: "You are an ANALYST agent specializing in technical analysis.
        Evaluate: price action, volume profile, historical patterns, order book depth.
        Be SKEPTICAL - look for hidden risks. Demand statistical evidence."
        """
        spread_bps = opp.get('profit_bps', 0)
        buy_price = opp.get('buy_price', 0)
        sell_price = opp.get('sell_price', 0)
        
        # Check for price anomalies
        if spread_bps > 100:
            # Suspicious - likely stale data or calculation error
            return ("REJECT", 0.85, f"Suspicious spread ({spread_bps} BPS) - likely stale/error")
        
        # Volume analysis (if available)
        liquidity_score = ctx.get('liquidity_score', 0.5)
        if liquidity_score < 0.3:
            return ("REJECT", 0.70, "Insufficient liquidity - slippage risk high")
        
        # Historical pattern check
        recent_spreads = ctx.get('recent_spreads', [])
        if recent_spreads:
            avg_spread = np.mean(recent_spreads)
            if spread_bps > avg_spread * 3:
                return ("CAUTION", 0.60, f"Spread 3x higher than average ({avg_spread:.1f} BPS) - anomaly detected")
        
        # Technical validation passed
        if spread_bps > 25 and liquidity_score > 0.7:
            return ("APPROVE", 0.80, f"Technical analysis confirms: {spread_bps} BPS with good liquidity")
        
        return ("APPROVE", 0.65, "Technical indicators acceptable but not exceptional")
    
    async def _strategist_planning(self, opp: Dict, ctx: Dict) -> Tuple[str, float, str]:
        """
        STRATEGIST: Execution planning
        Prompt: "You are a STRATEGIST agent responsible for execution planning.
        Consider: optimal timing, position sizing, gas optimization, MEV protection.
        Think TACTICALLY - plan the perfect execution sequence."
        """
        net_profit = opp.get('net_profit_usd', 0)
        gas_cost = opp.get('gas_cost_usd', 0)
        
        # Calculate profit margin
        if gas_cost > 0:
            profit_margin = (net_profit / (net_profit + gas_cost)) * 100
        else:
            profit_margin = 100
        
        # Position sizing recommendation
        if net_profit > 100:
            position_size = "LARGE"
            confidence = 0.90
            reasoning = f"High-profit opportunity (${net_profit:.2f}) - recommend LARGE position"
        elif net_profit > 50:
            position_size = "MEDIUM"
            confidence = 0.75
            reasoning = f"Good profit (${net_profit:.2f}) - recommend MEDIUM position"
        elif net_profit > 20:
            position_size = "SMALL"
            confidence = 0.65
            reasoning = f"Modest profit (${net_profit:.2f}) - recommend SMALL position"
        else:
            return ("SKIP", 0.40, f"Profit too low (${net_profit:.2f}) for execution costs")
        
        # Gas efficiency check
        if profit_margin < 50:
            return ("CAUTION", 0.55, f"Gas cost is {100-profit_margin:.1f}% of profit - tight margins")
        
        # Timing analysis
        current_hour = datetime.utcnow().hour
        if 2 <= current_hour <= 6:  # Low-activity hours
            reasoning += " | Optimal timing (low competition)"
            confidence += 0.05
        
        return ("APPROVE", confidence, reasoning)
    
    async def _risk_assessment(self, opp: Dict, ctx: Dict) -> Tuple[str, float, str]:
        """
        RISK_MANAGER: Conservative risk validation
        Prompt: "You are a RISK_MANAGER agent. Your PRIMARY goal is CAPITAL PRESERVATION.
        Evaluate: position sizing, leverage, correlation risk, liquidation risk, circuit breakers.
        Be CONSERVATIVE - reject anything that risks significant capital."
        """
        net_profit = opp.get('net_profit_usd', 0)
        spread_bps = opp.get('profit_bps', 0)
        
        # Portfolio risk checks
        portfolio_exposure = ctx.get('total_exposure_usd', 0)
        max_position = ctx.get('max_position_usd', 3000)
        
        # Check position sizing
        if net_profit > max_position * 0.1:  # If potential profit >10% of max position
            # Could be over-sizing
            return ("CAUTION", 0.60, f"Large position risk - profit ${net_profit:.2f} vs max ${max_position}")
        
        # Drawdown check
        current_drawdown = ctx.get('current_drawdown_pct', 0)
        if current_drawdown < -10:  # Already down 10%
            return ("REJECT", 0.80, f"Portfolio drawdown at {current_drawdown:.1f}% - halt new positions")
        
        # Consecutive losses check
        consecutive_losses = ctx.get('consecutive_losses', 0)
        if consecutive_losses >= 3:
            return ("REJECT", 0.75, f"Circuit breaker: {consecutive_losses} consecutive losses")
        
        # Volatility spike detection
        market_volatility = ctx.get('volatility_score', 0.5)
        if market_volatility > 0.8:
            return ("CAUTION", 0.65, f"High market volatility ({market_volatility:.2f}) - reduce exposure")
        
        # Risk assessment passed
        if spread_bps < 30 or net_profit < 15:
            return ("APPROVE", 0.60, "Risk acceptable but returns marginal")
        
        return ("APPROVE", 0.85, "Risk assessment PASSED - proceed with confidence")
    
    async def _executor_validation(self, opp: Dict, ctx: Dict) -> Tuple[str, float, str]:
        """
        EXECUTOR: Pre-execution final checks
        Prompt: "You are an EXECUTOR agent responsible for trade execution.
        Verify: on-chain conditions, gas prices, slippage limits, deadlines.
        Be PRECISE - ensure all parameters are optimal before execution."
        """
        # Gas price check
        current_gas_gwei = ctx.get('gas_price_gwei', 0.1)
        max_gas_gwei = ctx.get('max_gas_gwei', 1.0)
        
        if current_gas_gwei > max_gas_gwei:
            return ("DELAY", 0.70, f"Gas too high ({current_gas_gwei:.4f} vs {max_gas_gwei} max) - wait for better conditions")
        
        # Network congestion check
        network_congestion = ctx.get('network_congestion', 0.3)
        if network_congestion > 0.7:
            return ("DELAY", 0.65, f"Network congestion ({network_congestion:.1%}) - execution risk high")
        
        # Slippage validation
        expected_slippage = ctx.get('expected_slippage_bps', 10)
        if expected_slippage > 50:
            return ("REJECT", 0.75, f"Slippage too high ({expected_slippage} BPS) - execution infeasible")
        
        # All systems go
        return ("EXECUTE", 0.95, f"Execution conditions OPTIMAL - gas {current_gas_gwei:.4f} Gwei, low congestion")
    
    async def _monitor_evaluation(self, opp: Dict, ctx: Dict) -> Tuple[str, float, str]:
        """
        MONITOR: Post-trade analysis
        Prompt: "You are a MONITOR agent tracking trade performance.
        Analyze: actual vs expected profit, slippage, execution quality, pattern success.
        Be ANALYTICAL - identify what worked and what didn't for future improvement."
        """
        # This would typically analyze completed trades
        # For now, provide forward-looking monitoring recommendation
        
        spread_bps = opp.get('profit_bps', 0)
        priority = opp.get('priority', 'MEDIUM')
        
        # Set monitoring intensity
        if priority == 'CRITICAL' or spread_bps > 50:
            return ("MONITOR_CLOSE", 0.90, "High-value trade - enable real-time monitoring")
        elif spread_bps > 20:
            return ("MONITOR_NORMAL", 0.75, "Standard monitoring - track execution quality")
        else:
            return ("MONITOR_LIGHT", 0.60, "Low-priority - basic tracking only")
    
    def update_performance(self, was_correct: bool):
        """Update agent performance score based on prediction accuracy"""
        self.decisions_made += 1
        if was_correct:
            self.correct_predictions += 1
        
        # Calculate weighted performance score (recent bias)
        if self.decisions_made > 0:
            accuracy = self.correct_predictions / self.decisions_made
            # Weight recent performance more heavily
            self.performance_score = 0.7 * accuracy + 0.3 * self.performance_score


class SwarmCoordinator:
    """
    Orchestrates swarm of specialized agents
    Aggregates decisions using weighted voting with consensus detection
    """
    
    def __init__(self):
        # Initialize agent swarm
        self.agents: List[SwarmAgent] = self._initialize_swarm()
        self.decision_history: List[SwarmDecision] = []
        self.consensus_threshold = 0.70  # 70% agreement required
        
    def _initialize_swarm(self) -> List[SwarmAgent]:
        """Create swarm with specialized agents"""
        
        # Define agent prompts
        scout_prompt = AgentPrompt(
            role=AgentRole.SCOUT,
            system_prompt="Fast opportunity filter. Be aggressive in discovery.",
            decision_template="Is this worth investigating? Quick assessment.",
            success_criteria=["High spread", "Good liquidity", "Low gas"],
            failure_patterns=["Tiny spread", "No profit", "High gas"],
            confidence_threshold=0.55
        )
        
        analyst_prompt = AgentPrompt(
            role=AgentRole.ANALYST,
            system_prompt="Deep technical analysis. Be skeptical of anomalies.",
            decision_template="Technical validation. Look for hidden risks.",
            success_criteria=["Clean price action", "Good volume", "Normal patterns"],
            failure_patterns=["Stale data", "Low liquidity", "Anomalous spread"],
            confidence_threshold=0.65
        )
        
        strategist_prompt = AgentPrompt(
            role=AgentRole.STRATEGIST,
            system_prompt="Execution planning. Think tactically.",
            decision_template="How should we execute this? Optimal strategy.",
            success_criteria=["Good timing", "Right position size", "Low competition"],
            failure_patterns=["Bad timing", "Over-sizing", "High competition"],
            confidence_threshold=0.65
        )
        
        risk_prompt = AgentPrompt(
            role=AgentRole.RISK_MANAGER,
            system_prompt="Capital preservation first. Be conservative.",
            decision_template="Is this safe? Risk vs reward analysis.",
            success_criteria=["Low risk", "Good reward", "Safe position size"],
            failure_patterns=["High risk", "Poor reward", "Over-exposure"],
            confidence_threshold=0.70
        )
        
        executor_prompt = AgentPrompt(
            role=AgentRole.EXECUTOR,
            system_prompt="Execution validation. Be precise.",
            decision_template="Ready to execute? Check all parameters.",
            success_criteria=["Low gas", "Good conditions", "Optimal timing"],
            failure_patterns=["High gas", "Congestion", "Bad conditions"],
            confidence_threshold=0.75
        )
        
        monitor_prompt = AgentPrompt(
            role=AgentRole.MONITOR,
            system_prompt="Performance tracking. Be analytical.",
            decision_template="How should we monitor this? Set tracking intensity.",
            success_criteria=["Clear metrics", "Good tracking", "Pattern identified"],
            failure_patterns=["Poor data", "No tracking", "Unknown pattern"],
            confidence_threshold=0.60
        )
        
        # Create agent instances
        return [
            SwarmAgent(AgentRole.SCOUT, scout_prompt),
            SwarmAgent(AgentRole.ANALYST, analyst_prompt),
            SwarmAgent(AgentRole.STRATEGIST, strategist_prompt),
            SwarmAgent(AgentRole.RISK_MANAGER, risk_prompt),
            SwarmAgent(AgentRole.EXECUTOR, executor_prompt),
            SwarmAgent(AgentRole.MONITOR, monitor_prompt)
        ]
    
    async def evaluate_opportunity(self, opportunity: Dict, market_context: Dict) -> SwarmDecision:
        """
        Swarm evaluation of trading opportunity
        Each agent votes based on specialized role
        """
        
        # Collect votes from all agents
        votes: Dict[AgentRole, Tuple[str, float, str]] = {}
        
        for agent in self.agents:
            decision, confidence, reasoning = await agent.analyze(opportunity, market_context)
            votes[agent.role] = (decision, confidence, reasoning)
        
        # Aggregate decisions
        execute_votes = []
        skip_votes = []
        caution_votes = []
        
        for role, (decision, confidence, reasoning) in votes.items():
            weighted_confidence = confidence * (0.5 + agent.performance_score * 0.5)  # Weight by performance
            
            if decision in ["EXECUTE", "APPROVE", "INVESTIGATE"]:
                execute_votes.append((role, weighted_confidence, reasoning))
            elif decision in ["SKIP", "REJECT"]:
                skip_votes.append((role, weighted_confidence, reasoning))
            elif decision in ["CAUTION", "DELAY", "WAIT"]:
                caution_votes.append((role, weighted_confidence, reasoning))
        
        # Calculate aggregate confidence
        total_votes = len(execute_votes) + len(skip_votes) + len(caution_votes)
        
        if total_votes == 0:
            return SwarmDecision(
                action="ABSTAIN",
                confidence=0,
                agent_votes=votes,
                consensus_level=0,
                dissenting_opinions=["No votes cast"]
            )
        
        execute_confidence = sum(c for _, c, _ in execute_votes) / total_votes if execute_votes else 0
        skip_confidence = sum(c for _, c, _ in skip_votes) / total_votes if skip_votes else 0
        caution_confidence = sum(c for _, c, _ in caution_votes) / total_votes if caution_votes else 0
        
        # Determine consensus
        max_confidence = max(execute_confidence, skip_confidence, caution_confidence)
        consensus_level = max_confidence / (execute_confidence + skip_confidence + caution_confidence) if max_confidence > 0 else 0
        
        # Make decision
        if execute_confidence > skip_confidence and execute_confidence > caution_confidence:
            if consensus_level >= self.consensus_threshold:
                action = "EXECUTE"
                final_confidence = execute_confidence * 100
                dissenting = [r for r, _, reason in skip_votes + caution_votes]
            else:
                action = "INVESTIGATE"  # Not enough consensus
                final_confidence = execute_confidence * 80
                dissenting = [f"Low consensus: {consensus_level:.0%}"]
        elif skip_confidence > execute_confidence:
            action = "SKIP"
            final_confidence = skip_confidence * 100
            dissenting = [r for r, _, reason in execute_votes]
        else:
            action = "WAIT"
            final_confidence = caution_confidence * 100
            dissenting = ["Mixed signals - need more data"]
        
        # Create decision
        decision = SwarmDecision(
            action=action,
            confidence=final_confidence,
            agent_votes=votes,
            consensus_level=consensus_level,
            dissenting_opinions=[str(d) for d in dissenting]
        )
        
        self.decision_history.append(decision)
        
        return decision
    
    def get_swarm_stats(self) -> Dict:
        """Get swarm performance statistics"""
        return {
            'total_decisions': len(self.decision_history),
            'agent_performance': {
                agent.role.value: {
                    'accuracy': agent.performance_score,
                    'decisions': agent.decisions_made,
                    'correct': agent.correct_predictions
                }
                for agent in self.agents
            },
            'recent_consensus': np.mean([d.consensus_level for d in self.decision_history[-20:]]) if len(self.decision_history) >= 20 else 0,
            'action_distribution': {
                'EXECUTE': sum(1 for d in self.decision_history if d.action == 'EXECUTE'),
                'SKIP': sum(1 for d in self.decision_history if d.action == 'SKIP'),
                'WAIT': sum(1 for d in self.decision_history if d.action == 'WAIT'),
            }
        }


# Example usage
async def demo_swarm():
    """Demo swarm intelligence"""
    print("=" * 80)
    print("🐝 SWARM INTELLIGENCE COORDINATOR")
    print("=" * 80)
    
    coordinator = SwarmCoordinator()
    
    # Test opportunity
    opportunity = {
        'profit_bps': 527,
        'net_profit_usd': 73.92,
        'buy_price': 2950,
        'sell_price': 3105,
        'gas_cost_usd': 0.15,
        'priority': 'CRITICAL'
    }
    
    market_context = {
        'liquidity_score': 0.85,
        'recent_spreads': [300, 350, 400, 450, 500],
        'gas_price_gwei': 0.01,
        'network_congestion': 0.2,
        'total_exposure_usd': 5000,
        'max_position_usd': 3000,
        'current_drawdown_pct': -2.5,
        'consecutive_losses': 1,
        'volatility_score': 0.4,
        'max_gas_gwei': 1.0,
        'expected_slippage_bps': 15
    }
    
    decision = await coordinator.evaluate_opportunity(opportunity, market_context)
    
    print(f"\n🎯 SWARM DECISION: {decision.action}")
    print(f"💪 Confidence: {decision.confidence:.1f}/100")
    print(f"🤝 Consensus: {decision.consensus_level:.0%}")
    print(f"\n📊 Agent Votes:")
    for role, (vote, conf, reasoning) in decision.agent_votes.items():
        print(f"  {role.value.upper()}: {vote} ({conf:.0%}) - {reasoning}")
    
    if decision.dissenting_opinions:
        print(f"\n⚠️  Dissenting: {', '.join(decision.dissenting_opinions)}")
    
    print(f"\n📈 Swarm Stats:")
    stats = coordinator.get_swarm_stats()
    print(f"  Total Decisions: {stats['total_decisions']}")
    print(f"  Action Distribution: {stats['action_distribution']}")


if __name__ == "__main__":
    asyncio.run(demo_swarm())
