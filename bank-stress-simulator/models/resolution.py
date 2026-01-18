"""
Resolution Planning Module

Models FDIC resolution strategies including:
- Least-Cost Resolution (LCR) analysis
- Bridge Bank operations
- Purchase & Assumption (P&A) transactions
- Systemic Risk Exception determination
- Depositor preference and creditor hierarchy

Key regulatory references:
- Federal Deposit Insurance Act (12 USC 1821-1824)
- Dodd-Frank Title II (Orderly Liquidation Authority)
- FDIC regulations on resolution (12 CFR 360)

Based on lessons from 2023 resolutions:
- SVB → Silicon Valley Bridge Bank → First Citizens P&A
- Signature → Signature Bridge Bank → NY Community Bank P&A
- First Republic → JPMorgan P&A (loss-share)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum
import math

from models.bank import Bank


class ResolutionMethod(Enum):
    """FDIC resolution methods"""
    PURCHASE_ASSUMPTION = "p_and_a"           # Sell to healthy bank
    BRIDGE_BANK = "bridge_bank"               # Temporary FDIC-operated bank
    DEPOSIT_PAYOFF = "deposit_payoff"         # Pay insured deposits, liquidate
    OPEN_BANK_ASSISTANCE = "open_bank"        # Keep open with FDIC support (rare)
    ORDERLY_LIQUIDATION = "ola"               # Dodd-Frank Title II for SIFIs


class ClaimPriority(Enum):
    """Creditor hierarchy in FDIC receivership"""
    ADMIN_EXPENSES = 1          # Receiver costs
    SECURED_CLAIMS = 2          # Collateralized
    DEPOSITOR_DOMESTIC = 3      # Depositor preference (US deposits)
    GENERAL_UNSECURED = 4       # Senior unsecured debt
    SUBORDINATED = 5            # Sub debt
    EQUITY = 6                  # Shareholders (usually wiped out)


@dataclass
class Claim:
    """A claim against the failed bank"""
    holder: str
    amount: float
    priority: ClaimPriority
    is_insured_deposit: bool = False
    collateral_value: float = 0.0  # For secured claims


@dataclass
class ResolutionCost:
    """Breakdown of resolution costs"""
    insured_deposit_coverage: float
    uninsured_deposit_coverage: float
    asset_losses: float
    administrative_costs: float
    loss_share_commitment: float
    total_cost: float
    cost_to_dif: float  # Cost to Deposit Insurance Fund


@dataclass
class BidderProfile:
    """Profile of a potential acquirer"""
    name: str
    total_assets: float
    cet1_ratio: float
    can_absorb_deposits: bool
    premium_offered: float  # % premium over book value
    loss_share_request: float  # % of losses they want FDIC to cover
    cherry_picking: bool  # Only wants good assets


class ResolutionPlanner:
    """
    Resolution planning and cost estimation engine.

    Models the decision process FDIC undertakes when a bank fails.
    """

    def __init__(self, bank: Bank):
        self.bank = bank
        self.claims = self._build_claims_list()

    def _build_claims_list(self) -> List[Claim]:
        """Build the creditor claims list"""
        claims = []

        # Administrative expenses (estimated at 2% of assets)
        claims.append(Claim(
            holder="Administrative",
            amount=self.bank.total_assets * 0.02,
            priority=ClaimPriority.ADMIN_EXPENSES,
        ))

        # Secured claims (FHLB, repo)
        claims.append(Claim(
            holder="FHLB Advances",
            amount=self.bank.fhlb_advances,
            priority=ClaimPriority.SECURED_CLAIMS,
            collateral_value=self.bank.fhlb_advances,  # Fully collateralized
        ))
        claims.append(Claim(
            holder="Repo Funding",
            amount=self.bank.repo_funding,
            priority=ClaimPriority.SECURED_CLAIMS,
            collateral_value=self.bank.repo_funding,
        ))

        # Deposits (with domestic depositor preference)
        for deposit in self.bank.deposits:
            claims.append(Claim(
                holder=deposit.name,
                amount=deposit.amount,
                priority=ClaimPriority.DEPOSITOR_DOMESTIC,
                is_insured_deposit=deposit.is_insured,
            ))

        # Subordinated debt
        claims.append(Claim(
            holder="Subordinated Debt",
            amount=self.bank.capital.subordinated_debt,
            priority=ClaimPriority.SUBORDINATED,
        ))

        # Equity (will be wiped out)
        claims.append(Claim(
            holder="Common Equity",
            amount=self.bank.capital.common_stock + self.bank.capital.retained_earnings,
            priority=ClaimPriority.EQUITY,
        ))

        return claims

    def calculate_asset_recovery(
        self,
        liquidation_discount: float = 0.15,
        is_going_concern: bool = True
    ) -> Dict[str, float]:
        """
        Calculate expected recovery value of assets.

        Going concern sale typically achieves better recovery than
        piecemeal liquidation.
        """
        if is_going_concern:
            discount = liquidation_discount * 0.5  # Lower discount in P&A
        else:
            discount = liquidation_discount

        total_book = sum(a.book_value for a in self.bank.assets)
        total_market = sum(a.market_value for a in self.bank.assets)

        # Different asset classes have different recovery rates
        recovery_by_class = {}
        total_recovery = 0.0

        for asset in self.bank.assets:
            # Cash recovers at 100%
            if "cash" in asset.name.lower():
                recovery_rate = 1.0
            # Securities at market value minus liquidity discount
            elif any(x in asset.name.lower() for x in ["treasury", "bond", "securities"]):
                recovery_rate = (asset.market_value / asset.book_value) * (1 - discount * 0.5)
            # Loans at book minus credit losses and discount
            elif "loan" in asset.name.lower():
                recovery_rate = 1 - discount
            # Other assets
            else:
                recovery_rate = 1 - discount * 1.5

            recovery = asset.book_value * recovery_rate
            recovery_by_class[asset.name] = {
                "book_value": asset.book_value,
                "market_value": asset.market_value,
                "recovery_rate": recovery_rate,
                "recovery_value": recovery,
            }
            total_recovery += recovery

        return {
            "total_book_value": total_book,
            "total_market_value": total_market,
            "total_recovery": total_recovery,
            "overall_recovery_rate": total_recovery / total_book if total_book > 0 else 0,
            "by_asset_class": recovery_by_class,
        }

    def apply_waterfall(
        self,
        available_funds: float
    ) -> Dict[str, Dict[str, float]]:
        """
        Apply the creditor waterfall to distribute available funds.

        Follows FDIC receivership priority:
        1. Administrative expenses
        2. Secured claims (to extent of collateral)
        3. Depositor preference (domestic deposits)
        4. General unsecured
        5. Subordinated debt
        6. Equity
        """
        remaining = available_funds
        distributions = {}

        # Sort claims by priority
        sorted_claims = sorted(self.claims, key=lambda c: c.priority.value)

        current_priority = None
        priority_claims = []

        for claim in sorted_claims:
            if claim.priority != current_priority:
                # Process previous priority level
                if priority_claims:
                    remaining = self._distribute_to_priority(
                        priority_claims, remaining, distributions
                    )
                current_priority = claim.priority
                priority_claims = [claim]
            else:
                priority_claims.append(claim)

        # Process final priority level
        if priority_claims:
            self._distribute_to_priority(priority_claims, remaining, distributions)

        return distributions

    def _distribute_to_priority(
        self,
        claims: List[Claim],
        available: float,
        distributions: Dict
    ) -> float:
        """Distribute funds to claims at the same priority level"""
        # Secured claims get collateral first
        remaining = available

        for claim in claims:
            if claim.priority == ClaimPriority.SECURED_CLAIMS:
                # Secured creditors get their collateral
                recovery = min(claim.amount, claim.collateral_value, remaining)
                distributions[claim.holder] = {
                    "claim": claim.amount,
                    "recovery": recovery,
                    "recovery_rate": recovery / claim.amount if claim.amount > 0 else 0,
                }
                remaining -= recovery
            else:
                # Pro-rata distribution within priority
                total_claims = sum(c.amount for c in claims
                                   if c.priority != ClaimPriority.SECURED_CLAIMS)

                if total_claims > 0:
                    share = claim.amount / total_claims
                    recovery = min(claim.amount, remaining * share)
                else:
                    recovery = 0

                distributions[claim.holder] = {
                    "claim": claim.amount,
                    "recovery": recovery,
                    "recovery_rate": recovery / claim.amount if claim.amount > 0 else 0,
                    "is_insured_deposit": claim.is_insured_deposit,
                }

        # Calculate remaining after this priority
        total_distributed = sum(d["recovery"] for d in distributions.values())
        return available - total_distributed

    def calculate_least_cost(
        self,
        bidders: Optional[List[BidderProfile]] = None
    ) -> Dict:
        """
        Calculate least-cost resolution per FDIA 13(c)(4).

        FDIC must choose the resolution method that results in
        the least cost to the Deposit Insurance Fund, unless
        systemic risk exception is invoked.
        """
        costs = {}

        # Option 1: Deposit Payoff (baseline)
        insured_deposits = sum(
            d.amount for d in self.bank.deposits if d.is_insured
        )
        uninsured_deposits = sum(
            d.amount for d in self.bank.deposits if not d.is_insured
        )

        # Recovery from liquidation
        recovery = self.calculate_asset_recovery(
            liquidation_discount=0.20,
            is_going_concern=False
        )

        # Waterfall distribution
        distributions = self.apply_waterfall(recovery["total_recovery"])

        # FDIC pays insured deposits, recovers from estate
        insured_recovery = sum(
            d["recovery"] for name, d in distributions.items()
            if d.get("is_insured_deposit", False)
        )

        payoff_cost = ResolutionCost(
            insured_deposit_coverage=insured_deposits,
            uninsured_deposit_coverage=0,
            asset_losses=self.bank.total_assets - recovery["total_recovery"],
            administrative_costs=self.bank.total_assets * 0.02,
            loss_share_commitment=0,
            total_cost=insured_deposits - insured_recovery + self.bank.total_assets * 0.02,
            cost_to_dif=insured_deposits - insured_recovery,
        )
        costs["deposit_payoff"] = payoff_cost

        # Option 2: P&A with bidders
        if bidders:
            for bidder in bidders:
                pa_cost = self._calculate_pa_cost(bidder)
                costs[f"pa_{bidder.name}"] = pa_cost

        # Option 3: Bridge Bank (typically more expensive short-term)
        bridge_cost = self._calculate_bridge_cost()
        costs["bridge_bank"] = bridge_cost

        # Find least cost option
        sorted_options = sorted(costs.items(), key=lambda x: x[1].cost_to_dif)
        least_cost_option = sorted_options[0]

        return {
            "bank_name": self.bank.name,
            "total_assets": self.bank.total_assets,
            "total_deposits": self.bank.total_deposits,
            "insured_deposits": insured_deposits,
            "uninsured_deposits": uninsured_deposits,
            "asset_recovery": recovery,
            "options": {name: self._cost_to_dict(cost) for name, cost in costs.items()},
            "least_cost_option": least_cost_option[0],
            "least_cost_amount": least_cost_option[1].cost_to_dif,
            "creditor_distributions": distributions,
        }

    def _calculate_pa_cost(self, bidder: BidderProfile) -> ResolutionCost:
        """Calculate cost of P&A transaction with specific bidder"""
        # Going concern recovery is better
        recovery = self.calculate_asset_recovery(
            liquidation_discount=0.10,
            is_going_concern=True
        )

        # Premium paid by acquirer reduces cost
        premium = self.bank.total_deposits * bidder.premium_offered

        # Loss share increases FDIC exposure
        estimated_losses = self.bank.total_assets * 0.08  # Assume 8% losses
        fdic_loss_share = estimated_losses * bidder.loss_share_request

        insured = sum(d.amount for d in self.bank.deposits if d.is_insured)
        uninsured = sum(d.amount for d in self.bank.deposits if not d.is_insured)

        # In P&A, FDIC typically covers uninsured as well (systemic cases)
        total_cost = insured + uninsured - recovery["total_recovery"] - premium + fdic_loss_share

        return ResolutionCost(
            insured_deposit_coverage=insured,
            uninsured_deposit_coverage=uninsured,
            asset_losses=self.bank.total_assets - recovery["total_recovery"],
            administrative_costs=self.bank.total_assets * 0.01,  # Lower in P&A
            loss_share_commitment=fdic_loss_share,
            total_cost=max(0, total_cost),
            cost_to_dif=max(0, total_cost),
        )

    def _calculate_bridge_cost(self) -> ResolutionCost:
        """Calculate cost of operating a bridge bank"""
        # Bridge banks typically have higher operating costs
        # but can achieve better eventual sale price

        insured = sum(d.amount for d in self.bank.deposits if d.is_insured)
        uninsured = sum(d.amount for d in self.bank.deposits if not d.is_insured)

        # Bridge bank operating costs (~2% of assets per year)
        operating_cost = self.bank.total_assets * 0.02

        # But better recovery on eventual sale
        recovery = self.calculate_asset_recovery(
            liquidation_discount=0.08,
            is_going_concern=True
        )

        # FDIC provides liquidity to bridge bank
        liquidity_support = self.bank.total_deposits * 0.05

        total_cost = (
            insured + uninsured -
            recovery["total_recovery"] +
            operating_cost +
            liquidity_support
        )

        return ResolutionCost(
            insured_deposit_coverage=insured,
            uninsured_deposit_coverage=uninsured,
            asset_losses=self.bank.total_assets - recovery["total_recovery"],
            administrative_costs=operating_cost,
            loss_share_commitment=0,
            total_cost=total_cost,
            cost_to_dif=total_cost,
        )

    def _cost_to_dict(self, cost: ResolutionCost) -> Dict:
        """Convert ResolutionCost to dictionary"""
        return {
            "insured_deposit_coverage": cost.insured_deposit_coverage,
            "uninsured_deposit_coverage": cost.uninsured_deposit_coverage,
            "asset_losses": cost.asset_losses,
            "administrative_costs": cost.administrative_costs,
            "loss_share_commitment": cost.loss_share_commitment,
            "total_cost": cost.total_cost,
            "cost_to_dif": cost.cost_to_dif,
        }

    def evaluate_systemic_risk_exception(self) -> Dict:
        """
        Evaluate whether systemic risk exception (SRE) is warranted.

        Under FDIA 13(c)(4)(G), FDIC can deviate from least-cost
        if failure would have "serious adverse effects on economic
        conditions or financial stability."

        Requires 2/3 vote of FDIC Board + Fed Board + Treasury approval.

        SVB and Signature both received SRE on March 12, 2023.
        """
        # Size-based criteria
        is_large = self.bank.total_assets > 50_000_000_000  # $50B

        # Interconnectedness
        interbank_exposure = sum(self.bank.interbank_assets.values())
        is_interconnected = interbank_exposure > self.bank.total_assets * 0.05

        # Deposit concentration in critical sectors
        critical_deposits = sum(
            d.amount for d in self.bank.deposits
            if d.depositor_type in ["financial", "corporate"]
            and not d.is_insured
        )
        has_critical_deposits = critical_deposits > 10_000_000_000  # $10B

        # Payment system importance
        payment_volume = self.bank.total_assets * 0.5  # Proxy
        is_payment_critical = payment_volume > 50_000_000_000

        # Substitutability
        has_unique_services = False  # Would need more data

        # Contagion risk
        uninsured_ratio = self.bank.uninsured_deposit_ratio
        high_contagion_risk = uninsured_ratio > 0.5

        # Overall assessment
        factors_present = sum([
            is_large,
            is_interconnected,
            has_critical_deposits,
            is_payment_critical,
            high_contagion_risk,
        ])

        recommendation = factors_present >= 3

        return {
            "bank_name": self.bank.name,
            "total_assets": self.bank.total_assets,
            "factors": {
                "size_over_50B": is_large,
                "significant_interconnections": is_interconnected,
                "critical_sector_deposits": has_critical_deposits,
                "payment_system_importance": is_payment_critical,
                "high_contagion_risk": high_contagion_risk,
            },
            "factors_present": factors_present,
            "factors_required": 3,
            "sre_recommended": recommendation,
            "approval_required": [
                "2/3 FDIC Board",
                "2/3 Federal Reserve Board",
                "Treasury Secretary (in consultation with President)",
            ],
            "implications_if_invoked": [
                "FDIC can protect all depositors (insured and uninsured)",
                "FDIC can provide open bank assistance",
                "Cost allocated to special assessment on all banks",
                "Required reporting to Congress within 3 days",
            ],
        }

    def generate_resolution_plan(self) -> Dict:
        """Generate comprehensive resolution plan"""
        least_cost = self.calculate_least_cost(
            bidders=[
                BidderProfile(
                    name="Large Regional Acquirer",
                    total_assets=200_000_000_000,
                    cet1_ratio=0.12,
                    can_absorb_deposits=True,
                    premium_offered=0.01,
                    loss_share_request=0.80,
                    cherry_picking=False,
                ),
                BidderProfile(
                    name="G-SIB Acquirer",
                    total_assets=1_000_000_000_000,
                    cet1_ratio=0.13,
                    can_absorb_deposits=True,
                    premium_offered=0.02,
                    loss_share_request=0.50,
                    cherry_picking=True,
                ),
            ]
        )

        sre_analysis = self.evaluate_systemic_risk_exception()

        return {
            "bank_name": self.bank.name,
            "resolution_summary": {
                "total_assets": self.bank.total_assets,
                "total_deposits": self.bank.total_deposits,
                "insured_deposits": least_cost["insured_deposits"],
                "uninsured_deposits": least_cost["uninsured_deposits"],
                "uninsured_ratio": self.bank.uninsured_deposit_ratio,
            },
            "least_cost_analysis": least_cost,
            "systemic_risk_exception": sre_analysis,
            "recommended_approach": self._recommend_approach(least_cost, sre_analysis),
            "timeline": self._generate_timeline(),
            "key_decisions": [
                "Invoke systemic risk exception?" if sre_analysis["sre_recommended"] else None,
                "Accept bidder with loss-share or operate bridge bank?",
                "Treatment of uninsured depositors",
                "Litigation hold and claims process",
            ],
        }

    def _recommend_approach(self, least_cost: Dict, sre: Dict) -> Dict:
        """Generate resolution recommendation"""
        if sre["sre_recommended"]:
            # Systemic case - prioritize stability
            if least_cost["least_cost_option"].startswith("pa_"):
                return {
                    "method": ResolutionMethod.PURCHASE_ASSUMPTION.value,
                    "rationale": "P&A with acquirer under systemic risk exception",
                    "depositor_treatment": "All deposits protected",
                    "estimated_cost": least_cost["least_cost_amount"],
                }
            else:
                return {
                    "method": ResolutionMethod.BRIDGE_BANK.value,
                    "rationale": "Bridge bank to stabilize, seek acquirer",
                    "depositor_treatment": "All deposits protected",
                    "estimated_cost": least_cost["options"]["bridge_bank"]["cost_to_dif"],
                }
        else:
            # Non-systemic - strict least cost
            return {
                "method": least_cost["least_cost_option"],
                "rationale": "Least cost to DIF per FDIA 13(c)(4)",
                "depositor_treatment": "Insured deposits protected; uninsured pro-rata",
                "estimated_cost": least_cost["least_cost_amount"],
            }

    def _generate_timeline(self) -> List[Dict]:
        """Generate typical resolution timeline"""
        return [
            {"day": 0, "action": "Bank closed by chartering authority"},
            {"day": 0, "action": "FDIC appointed as receiver"},
            {"day": 0, "action": "Bridge bank established (if applicable)"},
            {"day": 1, "action": "Insured deposit access restored"},
            {"day": 1, "action": "Acquirer due diligence begins"},
            {"day": 7, "action": "Initial bid deadline"},
            {"day": 14, "action": "Final bids due"},
            {"day": 21, "action": "P&A agreement signed"},
            {"day": 30, "action": "Transaction closes"},
            {"day": 90, "action": "Receiver's claims process begins"},
            {"day": 180, "action": "Initial dividends to creditors"},
        ]
