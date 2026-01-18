"""
Financial Contagion Network Model

Models how stress propagates through the banking system via:
1. Direct exposures (interbank lending, derivatives counterparties)
2. Indirect exposures (common asset holdings, fire sales)
3. Information contagion (confidence spillovers)

Based on research from:
- Eisenberg & Noe (2001) - Systemic Risk in Financial Systems
- Allen & Gale (2000) - Financial Contagion
- Acharya (2009) - A Theory of Systemic Risk

The 2023 crisis showed how quickly contagion can spread:
SVB (3/10) → Signature (3/12) → First Republic (ongoing) → Credit Suisse (3/19)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple, Optional
from enum import Enum
import random
import math

from models.bank import Bank, create_sample_regional_bank, create_sample_gsib


class ContagionChannel(Enum):
    """Channels through which contagion spreads"""
    INTERBANK_CREDIT = "interbank_credit"      # Direct lending exposures
    DERIVATIVES = "derivatives"                 # Counterparty credit risk
    COMMON_ASSETS = "common_assets"            # Fire sale externalities
    FUNDING_MARKET = "funding_market"          # Wholesale funding dry-up
    CONFIDENCE = "confidence"                   # Pure information contagion
    DEPOSIT_FLIGHT = "deposit_flight"          # Coordinated depositor behavior


@dataclass
class BankNode:
    """A bank in the contagion network"""
    bank: Bank
    is_failed: bool = False
    failure_round: Optional[int] = None
    stress_level: float = 0.0  # 0-1, cumulative stress
    capital_ratio: float = 0.0
    liquidity_ratio: float = 0.0

    # Exposures to other banks
    credit_exposures: Dict[str, float] = field(default_factory=dict)
    funding_dependence: Dict[str, float] = field(default_factory=dict)

    # Common asset holdings (for fire sale modeling)
    asset_portfolio: Dict[str, float] = field(default_factory=dict)

    def __post_init__(self):
        self.capital_ratio = self.bank.cet1_ratio
        self.liquidity_ratio = self.bank.lcr_ratio

    def apply_loss(self, loss: float, channel: ContagionChannel) -> bool:
        """
        Apply a loss to the bank and check if it fails.
        Returns True if bank fails.
        """
        # Convert loss to capital impact
        if channel in [ContagionChannel.INTERBANK_CREDIT, ContagionChannel.DERIVATIVES]:
            # Direct credit losses hit capital
            self.bank.capital.retained_earnings -= loss

        elif channel == ContagionChannel.COMMON_ASSETS:
            # Fire sale losses hit securities portfolio
            for asset in self.bank.assets:
                if "bond" in asset.name.lower() or "securities" in asset.name.lower():
                    asset.market_value *= (1 - loss / self.bank.total_assets)

        elif channel in [ContagionChannel.FUNDING_MARKET, ContagionChannel.DEPOSIT_FLIGHT]:
            # Funding stress forces asset liquidation at discount
            liquidation_cost = loss * 0.2  # 20% haircut
            self.bank.capital.retained_earnings -= liquidation_cost

        elif channel == ContagionChannel.CONFIDENCE:
            # Confidence loss increases stress level
            self.stress_level += 0.2

        # Update ratios
        self.capital_ratio = self.bank.cet1_ratio
        self.liquidity_ratio = self.bank.lcr_ratio

        # Check failure conditions
        # PCA: Critically undercapitalized if CET1 < 2%
        if self.capital_ratio < 0.02:
            self.is_failed = True
            return True

        # Liquidity failure
        if self.liquidity_ratio < 0.5:  # Severe liquidity stress
            self.stress_level += 0.3

        if self.stress_level >= 1.0:
            self.is_failed = True
            return True

        return False


class ContagionNetwork:
    """
    Network model of interconnected banks.

    Simulates cascading failures through multiple channels.
    """

    def __init__(self):
        self.nodes: Dict[str, BankNode] = {}
        self.adjacency_matrix: Dict[str, Dict[str, float]] = {}
        self.failure_history: List[Dict] = []

    def add_bank(self, bank: Bank) -> None:
        """Add a bank to the network"""
        node = BankNode(bank=bank)
        self.nodes[bank.name] = node

    def add_exposure(
        self,
        from_bank: str,
        to_bank: str,
        amount: float,
        channel: ContagionChannel
    ) -> None:
        """Add a directed exposure between banks"""
        if from_bank not in self.adjacency_matrix:
            self.adjacency_matrix[from_bank] = {}

        key = f"{to_bank}_{channel.value}"
        self.adjacency_matrix[from_bank][key] = amount

        # Also track in the node
        if channel == ContagionChannel.INTERBANK_CREDIT:
            self.nodes[from_bank].credit_exposures[to_bank] = amount
        elif channel == ContagionChannel.FUNDING_MARKET:
            self.nodes[from_bank].funding_dependence[to_bank] = amount

    def generate_random_network(
        self,
        num_regional: int = 8,
        num_gsib: int = 4,
        interconnection_density: float = 0.3
    ) -> None:
        """Generate a realistic bank network"""
        # Create banks
        for i in range(num_regional):
            bank = create_sample_regional_bank(f"Regional Bank {i+1}")
            # Add some variation
            scale = 0.5 + random.random()
            bank.total_assets *= scale
            for asset in bank.assets:
                asset.book_value *= scale
                asset.market_value *= scale
            for deposit in bank.deposits:
                deposit.amount *= scale
            self.add_bank(bank)

        for i in range(num_gsib):
            bank = create_sample_gsib(f"Global Bank {i+1}")
            self.add_bank(bank)

        # Create exposures
        bank_names = list(self.nodes.keys())

        for from_bank in bank_names:
            for to_bank in bank_names:
                if from_bank == to_bank:
                    continue

                if random.random() < interconnection_density:
                    # Interbank credit exposure (2-5% of assets)
                    from_node = self.nodes[from_bank]
                    exposure_pct = 0.02 + random.random() * 0.03
                    amount = from_node.bank.total_assets * exposure_pct
                    self.add_exposure(
                        from_bank, to_bank, amount,
                        ContagionChannel.INTERBANK_CREDIT
                    )

                if random.random() < interconnection_density * 0.5:
                    # Funding dependence (1-3% of liabilities)
                    from_node = self.nodes[from_bank]
                    dependence_pct = 0.01 + random.random() * 0.02
                    amount = from_node.bank.total_deposits * dependence_pct
                    self.add_exposure(
                        from_bank, to_bank, amount,
                        ContagionChannel.FUNDING_MARKET
                    )

    def calculate_centrality(self) -> Dict[str, float]:
        """
        Calculate systemic importance based on network centrality.

        Uses a simplified version of eigenvector centrality.
        """
        centrality = {name: 0.0 for name in self.nodes}

        # Sum of exposures (in and out)
        for from_bank, exposures in self.adjacency_matrix.items():
            total_exposure = sum(exposures.values())
            centrality[from_bank] += total_exposure

            for key, amount in exposures.items():
                to_bank = key.split("_")[0]
                if to_bank in centrality:
                    centrality[to_bank] += amount

        # Normalize
        max_centrality = max(centrality.values()) if centrality.values() else 1
        return {k: v / max_centrality for k, v in centrality.items()}

    def simulate_cascade(
        self,
        initial_failure: str,
        max_rounds: int = 10,
        loss_given_default: float = 0.45,  # LGD for senior unsecured
        confidence_spillover: float = 0.2,
    ) -> Dict:
        """
        Simulate cascading failures from an initial shock.

        Parameters:
        - initial_failure: Name of bank that fails first
        - max_rounds: Maximum simulation rounds
        - loss_given_default: Recovery rate assumption (1 - LGD)
        - confidence_spillover: How much confidence stress spreads
        """
        if initial_failure not in self.nodes:
            raise ValueError(f"Bank {initial_failure} not in network")

        # Reset state
        for node in self.nodes.values():
            node.is_failed = False
            node.failure_round = None
            node.stress_level = 0.0

        # Trigger initial failure
        self.nodes[initial_failure].is_failed = True
        self.nodes[initial_failure].failure_round = 0

        self.failure_history = [{
            "round": 0,
            "failed_bank": initial_failure,
            "channel": "initial_shock",
            "loss": 0,
        }]

        failed_banks = {initial_failure}
        new_failures = {initial_failure}

        for round_num in range(1, max_rounds + 1):
            if not new_failures:
                break

            round_failures = set()

            # Process each failed bank's impact
            for failed_bank in new_failures:
                failed_node = self.nodes[failed_bank]

                # Propagate losses to creditors
                for creditor_name, node in self.nodes.items():
                    if creditor_name in failed_banks:
                        continue

                    # Credit losses
                    credit_exposure = node.credit_exposures.get(failed_bank, 0)
                    if credit_exposure > 0:
                        loss = credit_exposure * loss_given_default

                        if node.apply_loss(loss, ContagionChannel.INTERBANK_CREDIT):
                            node.failure_round = round_num
                            round_failures.add(creditor_name)
                            self.failure_history.append({
                                "round": round_num,
                                "failed_bank": creditor_name,
                                "channel": "interbank_credit",
                                "loss": loss,
                                "triggered_by": failed_bank,
                            })

                    # Funding stress
                    funding_dependence = node.funding_dependence.get(failed_bank, 0)
                    if funding_dependence > 0:
                        # Funding gap must be filled at premium
                        funding_cost = funding_dependence * 0.1
                        if node.apply_loss(funding_cost, ContagionChannel.FUNDING_MARKET):
                            if creditor_name not in round_failures:
                                node.failure_round = round_num
                                round_failures.add(creditor_name)
                                self.failure_history.append({
                                    "round": round_num,
                                    "failed_bank": creditor_name,
                                    "channel": "funding_market",
                                    "loss": funding_cost,
                                    "triggered_by": failed_bank,
                                })

                # Confidence contagion (affects similar banks more)
                for other_name, other_node in self.nodes.items():
                    if other_name in failed_banks or other_name in round_failures:
                        continue

                    # Similar asset size = more confidence spillover
                    size_similarity = 1 - abs(
                        math.log10(other_node.bank.total_assets) -
                        math.log10(failed_node.bank.total_assets)
                    ) / 3

                    confidence_loss = confidence_spillover * max(0, size_similarity)
                    other_node.stress_level += confidence_loss

                    if other_node.stress_level >= 1.0:
                        other_node.is_failed = True
                        other_node.failure_round = round_num
                        round_failures.add(other_name)
                        self.failure_history.append({
                            "round": round_num,
                            "failed_bank": other_name,
                            "channel": "confidence",
                            "loss": 0,
                            "triggered_by": failed_bank,
                        })

            failed_banks.update(round_failures)
            new_failures = round_failures

        return self._generate_cascade_report(initial_failure, failed_banks)

    def _generate_cascade_report(
        self,
        initial_failure: str,
        failed_banks: Set[str]
    ) -> Dict:
        """Generate report on cascade simulation"""
        total_assets_failed = sum(
            self.nodes[name].bank.total_assets
            for name in failed_banks
        )
        total_assets_system = sum(
            node.bank.total_assets
            for node in self.nodes.values()
        )

        # Count failures by channel
        channel_counts = {}
        for event in self.failure_history:
            channel = event["channel"]
            channel_counts[channel] = channel_counts.get(channel, 0) + 1

        # Identify most vulnerable banks (high stress but didn't fail)
        vulnerable = [
            {"bank": name, "stress_level": node.stress_level}
            for name, node in self.nodes.items()
            if not node.is_failed and node.stress_level > 0.3
        ]
        vulnerable.sort(key=lambda x: x["stress_level"], reverse=True)

        return {
            "initial_failure": initial_failure,
            "total_banks": len(self.nodes),
            "failed_banks": list(failed_banks),
            "num_failures": len(failed_banks),
            "cascade_rounds": max(e["round"] for e in self.failure_history),
            "total_assets_failed": total_assets_failed,
            "pct_system_assets_failed": total_assets_failed / total_assets_system,
            "failures_by_channel": channel_counts,
            "failure_timeline": self.failure_history,
            "vulnerable_survivors": vulnerable[:5],
            "centrality_scores": self.calculate_centrality(),
        }

    def analyze_systemic_risk(self) -> Dict:
        """
        Comprehensive systemic risk analysis.

        Tests what happens if each bank fails.
        """
        results = {}

        for bank_name in self.nodes:
            # Save state
            original_state = {
                name: (node.is_failed, node.stress_level)
                for name, node in self.nodes.items()
            }

            # Run cascade
            cascade = self.simulate_cascade(bank_name)

            results[bank_name] = {
                "total_failures_triggered": cascade["num_failures"],
                "pct_system_affected": cascade["pct_system_assets_failed"],
                "cascade_rounds": cascade["cascade_rounds"],
                "is_systemically_important": cascade["pct_system_assets_failed"] > 0.1,
            }

            # Restore state
            for name, (failed, stress) in original_state.items():
                self.nodes[name].is_failed = failed
                self.nodes[name].stress_level = stress
                self.nodes[name].failure_round = None

        # Rank by systemic importance
        rankings = sorted(
            results.items(),
            key=lambda x: x[1]["pct_system_affected"],
            reverse=True
        )

        return {
            "bank_risk_profiles": results,
            "systemic_importance_ranking": [
                {"bank": name, **data}
                for name, data in rankings
            ],
            "most_systemic_bank": rankings[0][0] if rankings else None,
            "network_stats": {
                "total_banks": len(self.nodes),
                "total_exposures": sum(
                    len(exp) for exp in self.adjacency_matrix.values()
                ),
                "avg_interconnection": sum(
                    len(exp) for exp in self.adjacency_matrix.values()
                ) / len(self.nodes) if self.nodes else 0,
            },
        }

    def model_2023_crisis(self) -> Dict:
        """
        Model a scenario similar to the March 2023 banking crisis.

        SVB fails → Signature fails → First Republic under pressure → contagion spreads
        """
        # Create a network resembling the 2023 situation
        self.nodes.clear()
        self.adjacency_matrix.clear()

        # Create banks with profiles similar to 2023 failures
        svb_like = create_sample_regional_bank("Silicon Valley Bank")
        # High uninsured deposits, long duration securities
        svb_like.total_assets = 210_000_000_000
        self.add_bank(svb_like)

        signature_like = create_sample_regional_bank("Signature Bank")
        signature_like.total_assets = 110_000_000_000
        self.add_bank(signature_like)

        frc_like = create_sample_regional_bank("First Republic Bank")
        frc_like.total_assets = 230_000_000_000
        self.add_bank(frc_like)

        # Add some regional peers
        for i, name in enumerate(["PacWest", "Western Alliance", "Zions"]):
            bank = create_sample_regional_bank(name)
            bank.total_assets = 50_000_000_000 + i * 20_000_000_000
            self.add_bank(bank)

        # Add G-SIBs (more stable)
        for name in ["JPMorgan", "Bank of America", "Wells Fargo"]:
            bank = create_sample_gsib(name)
            self.add_bank(bank)

        # Create exposures (regional banks more interconnected with each other)
        regionals = ["Silicon Valley Bank", "Signature Bank", "First Republic Bank",
                     "PacWest", "Western Alliance", "Zions"]
        gsibs = ["JPMorgan", "Bank of America", "Wells Fargo"]

        for r1 in regionals:
            for r2 in regionals:
                if r1 != r2:
                    # Funding market linkages
                    self.add_exposure(r1, r2,
                                      self.nodes[r1].bank.total_assets * 0.01,
                                      ContagionChannel.FUNDING_MARKET)

            # Regionals have some exposure to G-SIBs
            for g in gsibs:
                self.add_exposure(r1, g,
                                  self.nodes[r1].bank.total_assets * 0.02,
                                  ContagionChannel.INTERBANK_CREDIT)

        # Simulate SVB failure triggering cascade
        return self.simulate_cascade(
            initial_failure="Silicon Valley Bank",
            max_rounds=5,
            loss_given_default=0.40,
            confidence_spillover=0.35,  # High confidence contagion in 2023
        )
