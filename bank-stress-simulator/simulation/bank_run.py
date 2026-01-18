"""
Bank Run Simulation Engine

Models the dynamics of bank runs with lessons from the 2023 crisis:
- SVB: $42B withdrawn in one day (March 9, 2023)
- Signature: Contagion-driven run
- First Republic: Slow-motion confidence erosion

Key factors modeled:
1. Deposit composition (insured vs uninsured)
2. Depositor behavior (retail vs institutional)
3. Information cascade (social media, news)
4. Coordination games (depositors watching each other)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Tuple
from enum import Enum
import random
import math

from models.bank import Bank, Deposit, DepositType


class RunTrigger(Enum):
    """Events that can trigger a bank run"""
    EARNINGS_MISS = "earnings_miss"
    CAPITAL_RAISE_ANNOUNCEMENT = "capital_raise"  # What killed SVB
    RATING_DOWNGRADE = "rating_downgrade"
    REGULATORY_ACTION = "regulatory_action"
    PEER_FAILURE = "peer_failure"  # Contagion
    SOCIAL_MEDIA_PANIC = "social_media"
    ANALYST_REPORT = "analyst_report"
    LIQUIDITY_SQUEEZE = "liquidity_squeeze"


@dataclass
class DepositorAgent:
    """
    Agent-based model of depositor behavior.

    Different depositor types have different:
    - Information access
    - Coordination ability
    - Run propensity
    """
    depositor_id: str
    deposit_amount: float
    is_insured: bool
    depositor_type: str  # "retail", "corporate", "vc_backed", "financial"
    sophistication: float  # 0-1, affects information processing speed
    network_connections: int  # Affects coordination
    run_threshold: float  # Probability threshold to trigger withdrawal

    def evaluate_run_decision(
        self,
        news_severity: float,
        peer_run_rate: float,
        bank_health_signal: float,
        hours_since_trigger: float
    ) -> Tuple[bool, float]:
        """
        Decide whether to run based on available information.

        Returns (will_run, withdrawal_fraction)
        """
        # Base probability from news
        news_impact = news_severity * self.sophistication

        # Peer behavior (coordination game)
        # More connected depositors are more influenced by peer behavior
        peer_impact = peer_run_rate * (1 + 0.1 * self.network_connections)

        # Bank health signal (capital ratios, etc.)
        health_impact = (1 - bank_health_signal) * 0.3

        # Time pressure - urgency increases over time
        time_factor = min(1.0, hours_since_trigger / 24)  # Maxes out at 24 hours

        # Uninsured depositors are much more sensitive
        insurance_multiplier = 2.5 if not self.is_insured else 1.0

        # VC/startup depositors are highly coordinated (the SVB factor)
        if self.depositor_type == "vc_backed":
            coordination_boost = 1.5
        elif self.depositor_type == "financial":
            coordination_boost = 1.3
        else:
            coordination_boost = 1.0

        # Calculate total run probability
        run_probability = (
            (news_impact + peer_impact + health_impact) *
            insurance_multiplier *
            coordination_boost *
            (0.5 + 0.5 * time_factor)
        )

        # Clamp to [0, 1]
        run_probability = max(0.0, min(1.0, run_probability))

        # Decision
        will_run = run_probability > self.run_threshold

        # How much to withdraw (uninsured want everything out)
        if will_run:
            if not self.is_insured:
                withdrawal_fraction = 1.0  # Get everything out
            else:
                withdrawal_fraction = 0.5 + random.random() * 0.3  # Partial withdrawal
        else:
            withdrawal_fraction = 0.0

        return will_run, withdrawal_fraction


@dataclass
class RunSimulationState:
    """State of a bank run simulation at a point in time"""
    hour: float
    total_deposits: float
    remaining_deposits: float
    cumulative_outflows: float
    outflow_rate_per_hour: float
    available_liquidity: float
    bank_is_solvent: bool
    bank_is_liquid: bool
    peer_run_rate: float
    news_severity: float
    depositors_who_ran: int
    total_depositors: int


class BankRunSimulator:
    """
    Simulates bank run dynamics hour-by-hour.

    Based on the Diamond-Dybvig model with extensions for:
    - Heterogeneous depositors
    - Information cascades
    - Modern communication (social media speed)
    """

    def __init__(self, bank: Bank):
        self.bank = bank
        self.depositor_agents = self._create_depositor_agents()

    def _create_depositor_agents(self) -> List[DepositorAgent]:
        """Create agent-based model of depositors"""
        agents = []
        agent_id = 0

        for deposit in self.bank.deposits:
            # Create multiple agents per deposit category
            # Number based on deposit size (more $ = more agents)
            if "retail" in deposit.name.lower():
                # Many small retail depositors
                num_agents = int(deposit.amount / 100_000)  # One agent per $100K
                avg_deposit = deposit.amount / max(1, num_agents)
            else:
                # Fewer large institutional depositors
                num_agents = int(deposit.amount / 10_000_000)  # One agent per $10M
                avg_deposit = deposit.amount / max(1, num_agents)

            num_agents = max(1, min(num_agents, 1000))  # Cap for performance

            for _ in range(num_agents):
                # Assign characteristics based on depositor type
                if deposit.depositor_type == "retail":
                    sophistication = 0.2 + random.random() * 0.3
                    network_connections = random.randint(1, 10)
                    run_threshold = 0.5 + random.random() * 0.3
                elif deposit.depositor_type == "corporate":
                    sophistication = 0.5 + random.random() * 0.3
                    network_connections = random.randint(5, 30)
                    run_threshold = 0.3 + random.random() * 0.3
                elif deposit.depositor_type == "financial":
                    sophistication = 0.8 + random.random() * 0.2
                    network_connections = random.randint(20, 100)
                    run_threshold = 0.2 + random.random() * 0.2  # Hair trigger
                else:  # VC/startup
                    sophistication = 0.7 + random.random() * 0.3
                    network_connections = random.randint(50, 200)  # Highly networked
                    run_threshold = 0.15 + random.random() * 0.15  # Very quick to run

                agents.append(DepositorAgent(
                    depositor_id=f"agent_{agent_id}",
                    deposit_amount=avg_deposit,
                    is_insured=deposit.is_insured,
                    depositor_type=deposit.depositor_type,
                    sophistication=sophistication,
                    network_connections=network_connections,
                    run_threshold=run_threshold,
                ))
                agent_id += 1

        return agents

    def simulate_run(
        self,
        trigger: RunTrigger,
        trigger_severity: float = 0.5,  # 0-1 scale
        max_hours: int = 72,
        fhlb_access: bool = True,
        fed_discount_window: bool = True,
    ) -> List[RunSimulationState]:
        """
        Simulate a bank run hour-by-hour.

        Parameters:
        - trigger: What started the run
        - trigger_severity: How bad is the news (0-1)
        - max_hours: How long to simulate
        - fhlb_access: Can bank access FHLB advances?
        - fed_discount_window: Can bank access Fed discount window?
        """
        # Initial state
        total_deposits = sum(a.deposit_amount for a in self.depositor_agents)
        remaining_deposits = total_deposits

        # Available liquidity (HQLA + credit lines)
        base_liquidity = self.bank.hqla_total
        fhlb_capacity = self.bank.fhlb_advances * 2 if fhlb_access else 0  # Can draw more
        fed_capacity = self.bank.total_assets * 0.1 if fed_discount_window else 0

        available_liquidity = base_liquidity + fhlb_capacity + fed_capacity

        # Track which agents have already run
        agents_who_ran = set()

        # News severity decays over time unless new information
        news_severity = trigger_severity

        # Trigger-specific initial severity
        severity_boost = {
            RunTrigger.CAPITAL_RAISE_ANNOUNCEMENT: 0.3,  # SVB's fatal mistake
            RunTrigger.PEER_FAILURE: 0.4,
            RunTrigger.RATING_DOWNGRADE: 0.2,
            RunTrigger.REGULATORY_ACTION: 0.5,
            RunTrigger.SOCIAL_MEDIA_PANIC: 0.35,
        }
        news_severity += severity_boost.get(trigger, 0)
        news_severity = min(1.0, news_severity)

        states = []

        for hour in range(max_hours):
            # Calculate bank health signal (what depositors can observe)
            capital_ratio = self.bank.cet1_ratio
            bank_health = min(1.0, capital_ratio / 0.10)  # 10% = healthy

            # Current peer run rate
            peer_run_rate = len(agents_who_ran) / len(self.depositor_agents)

            # Each agent decides whether to run
            hourly_outflow = 0.0
            new_runners = 0

            for agent in self.depositor_agents:
                if agent.depositor_id in agents_who_ran:
                    continue  # Already withdrew

                will_run, withdrawal_frac = agent.evaluate_run_decision(
                    news_severity=news_severity,
                    peer_run_rate=peer_run_rate,
                    bank_health_signal=bank_health,
                    hours_since_trigger=hour,
                )

                if will_run:
                    withdrawal = agent.deposit_amount * withdrawal_frac
                    hourly_outflow += withdrawal
                    agents_who_ran.add(agent.depositor_id)
                    new_runners += 1

            # Update state
            remaining_deposits -= hourly_outflow
            available_liquidity -= hourly_outflow

            # Check solvency and liquidity
            bank_is_liquid = available_liquidity > 0
            bank_is_solvent = self.bank.capital.total_capital > 0

            # News severity can increase if bank appears to be failing
            if not bank_is_liquid:
                news_severity = min(1.0, news_severity + 0.2)
            elif hourly_outflow > total_deposits * 0.05:  # >5% outflow in an hour
                news_severity = min(1.0, news_severity + 0.1)
            else:
                # News decays slowly
                news_severity = max(0.1, news_severity * 0.98)

            states.append(RunSimulationState(
                hour=hour,
                total_deposits=total_deposits,
                remaining_deposits=remaining_deposits,
                cumulative_outflows=total_deposits - remaining_deposits,
                outflow_rate_per_hour=hourly_outflow,
                available_liquidity=available_liquidity,
                bank_is_solvent=bank_is_solvent,
                bank_is_liquid=bank_is_liquid,
                peer_run_rate=peer_run_rate,
                news_severity=news_severity,
                depositors_who_ran=len(agents_who_ran),
                total_depositors=len(self.depositor_agents),
            ))

            # Stop if bank fails
            if not bank_is_liquid:
                break

        return states

    def analyze_run_vulnerability(self) -> Dict:
        """
        Analyze how vulnerable the bank is to runs under different triggers.
        """
        results = {}

        for trigger in RunTrigger:
            for severity in [0.3, 0.5, 0.7]:
                # Run simulation
                states = self.simulate_run(
                    trigger=trigger,
                    trigger_severity=severity,
                    max_hours=72,
                )

                final_state = states[-1]
                failure_hour = None

                for state in states:
                    if not state.bank_is_liquid:
                        failure_hour = state.hour
                        break

                key = f"{trigger.value}_{severity}"
                results[key] = {
                    "trigger": trigger.value,
                    "severity": severity,
                    "survives_72_hours": final_state.bank_is_liquid,
                    "failure_hour": failure_hour,
                    "peak_hourly_outflow": max(s.outflow_rate_per_hour for s in states),
                    "total_outflows": final_state.cumulative_outflows,
                    "pct_deposits_fled": final_state.cumulative_outflows / final_state.total_deposits,
                    "final_liquidity": final_state.available_liquidity,
                }

        return results

    def svb_scenario(self) -> List[RunSimulationState]:
        """
        Recreate the SVB-style run scenario.

        Timeline:
        - Wednesday 3/8: Capital raise announced after hours
        - Thursday 3/9: $42B withdrawn
        - Friday 3/10: FDIC takes over

        Key factors:
        - High uninsured deposit concentration (94%)
        - Highly networked VC depositors
        - Social media coordination
        - Interest rate losses on securities
        """
        return self.simulate_run(
            trigger=RunTrigger.CAPITAL_RAISE_ANNOUNCEMENT,
            trigger_severity=0.7,
            max_hours=48,
            fhlb_access=True,  # They tried
            fed_discount_window=True,  # Too slow to help
        )

    def generate_run_report(
        self,
        trigger: RunTrigger = RunTrigger.CAPITAL_RAISE_ANNOUNCEMENT,
        severity: float = 0.5
    ) -> Dict:
        """Generate comprehensive run analysis report"""
        # Run main simulation
        states = self.simulate_run(trigger, severity)

        # Find critical moments
        max_outflow_hour = max(states, key=lambda s: s.outflow_rate_per_hour)

        # Calculate depositor demographics
        total_agents = len(self.depositor_agents)
        uninsured_agents = sum(1 for a in self.depositor_agents if not a.is_insured)
        vc_agents = sum(1 for a in self.depositor_agents if a.depositor_type == "vc_backed")

        return {
            "bank_name": self.bank.name,
            "trigger": trigger.value,
            "trigger_severity": severity,
            "depositor_profile": {
                "total_agents": total_agents,
                "uninsured_agents": uninsured_agents,
                "uninsured_pct": uninsured_agents / total_agents,
                "vc_backed_agents": vc_agents,
                "vc_backed_pct": vc_agents / total_agents,
            },
            "simulation_results": {
                "duration_hours": len(states),
                "survived": states[-1].bank_is_liquid,
                "failure_hour": next(
                    (s.hour for s in states if not s.bank_is_liquid),
                    None
                ),
                "peak_outflow_hour": max_outflow_hour.hour,
                "peak_outflow_amount": max_outflow_hour.outflow_rate_per_hour,
                "total_outflows": states[-1].cumulative_outflows,
                "final_remaining_deposits": states[-1].remaining_deposits,
                "final_liquidity": states[-1].available_liquidity,
                "final_peer_run_rate": states[-1].peer_run_rate,
            },
            "hourly_timeline": [
                {
                    "hour": s.hour,
                    "outflows": s.outflow_rate_per_hour,
                    "cumulative_outflows": s.cumulative_outflows,
                    "remaining_deposits": s.remaining_deposits,
                    "liquidity": s.available_liquidity,
                    "peer_run_rate": s.peer_run_rate,
                    "bank_is_liquid": s.bank_is_liquid,
                }
                for s in states
            ],
            "vulnerability_analysis": self.analyze_run_vulnerability(),
        }
