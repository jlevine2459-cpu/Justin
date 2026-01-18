"""
Liquidity Risk Analysis Module

Implements Basel III liquidity requirements:
- Liquidity Coverage Ratio (LCR)
- Net Stable Funding Ratio (NSFR)
- Intraday liquidity monitoring

Key regulatory references:
- Basel III: The Liquidity Coverage Ratio (BCBS 238)
- Basel III: The Net Stable Funding Ratio (BCBS 295)
- Federal Reserve Regulation WW (12 CFR 249)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum

from models.bank import (
    Bank, Asset, Deposit, DepositType, HQLALevel,
    DEPOSIT_RUNOFF_RATES, HQLA_HAIRCUTS
)


class LiquidityStressLevel(Enum):
    """Severity of liquidity stress scenario"""
    NORMAL = "normal"
    MODERATE = "moderate"
    SEVERE = "severe"
    EXTREME = "extreme"  # SVB-style run


@dataclass
class CashFlowProjection:
    """Daily cash flow projection"""
    day: int
    inflows: float
    outflows: float
    net_flow: float
    cumulative_flow: float
    liquidity_position: float


class LiquidityAnalyzer:
    """
    Comprehensive liquidity risk analysis engine.

    Models the liquidity risks that proved fatal for SVB:
    - Deposit concentration and flight risk
    - Asset-liability maturity mismatch
    - HQLA adequacy under stress
    """

    def __init__(self, bank: Bank):
        self.bank = bank

    def calculate_hqla_composition(self) -> Dict[str, float]:
        """
        Calculate High-Quality Liquid Assets by level.

        Level 1: No haircut (cash, central bank reserves, sovereign debt)
        Level 2A: 15% haircut (GSE debt, high-grade corporate)
        Level 2B: 25-50% haircut (lower-grade assets, RMBS)

        Level 2 assets capped at 40% of total HQLA.
        Level 2B capped at 15% of total HQLA.
        """
        level_1 = 0.0
        level_2a = 0.0
        level_2b = 0.0

        for asset in self.bank.assets:
            if asset.hqla_level == HQLALevel.LEVEL_1:
                level_1 += asset.market_value  # No haircut
            elif asset.hqla_level == HQLALevel.LEVEL_2A:
                level_2a += asset.market_value * (1 - HQLA_HAIRCUTS[HQLALevel.LEVEL_2A])
            elif asset.hqla_level == HQLALevel.LEVEL_2B:
                level_2b += asset.market_value * (1 - HQLA_HAIRCUTS[HQLALevel.LEVEL_2B])

        # Apply caps
        total_before_caps = level_1 + level_2a + level_2b

        # Level 2B capped at 15% of total
        level_2b_capped = min(level_2b, total_before_caps * 0.15)

        # Total Level 2 capped at 40% of total
        level_2_combined = level_2a + level_2b_capped
        level_2_cap = (level_1 / 0.6) * 0.4 if level_1 > 0 else 0
        level_2_capped = min(level_2_combined, level_2_cap)

        # Adjusted HQLA after caps
        total_hqla = level_1 + level_2_capped

        return {
            "level_1_unadjusted": level_1,
            "level_2a_after_haircut": level_2a,
            "level_2b_after_haircut": level_2b,
            "level_2b_after_cap": level_2b_capped,
            "level_2_total_after_cap": level_2_capped,
            "total_hqla": total_hqla,
            "level_2_cap_binding": level_2_combined > level_2_cap,
        }

    def calculate_cash_outflows(self, stress_level: LiquidityStressLevel = LiquidityStressLevel.SEVERE) -> Dict[str, float]:
        """
        Calculate 30-day stressed cash outflows.

        Outflow categories:
        1. Retail deposit run-off
        2. Wholesale funding run-off
        3. Secured funding run-off (repo)
        4. Derivative obligations
        5. Credit/liquidity facility draws
        """
        # Stress multipliers
        stress_multipliers = {
            LiquidityStressLevel.NORMAL: 0.5,
            LiquidityStressLevel.MODERATE: 1.0,
            LiquidityStressLevel.SEVERE: 1.5,
            LiquidityStressLevel.EXTREME: 3.0,  # SVB scenario
        }
        multiplier = stress_multipliers[stress_level]

        # Deposit outflows
        deposit_outflows = 0.0
        deposit_detail = []

        for deposit in self.bank.deposits:
            base_runoff = DEPOSIT_RUNOFF_RATES[deposit.deposit_type]
            stressed_runoff = min(1.0, base_runoff * multiplier)
            outflow = deposit.amount * stressed_runoff

            deposit_outflows += outflow
            deposit_detail.append({
                "name": deposit.name,
                "amount": deposit.amount,
                "base_runoff_rate": base_runoff,
                "stressed_runoff_rate": stressed_runoff,
                "outflow": outflow,
            })

        # Secured funding (repo) outflows
        # Assume 25-100% roll-off depending on collateral quality
        repo_outflow = self.bank.repo_funding * 0.25 * multiplier

        # FHLB advance potential calls
        fhlb_outflow = self.bank.fhlb_advances * 0.10 * multiplier

        # Derivative cash outflows (simplified)
        derivative_outflow = self.bank.derivatives_notional * 0.001 * multiplier

        # Credit facility draws
        commitment_draws = self.bank.unfunded_commitments * 0.10 * multiplier

        # Letter of credit draws
        loc_draws = self.bank.letters_of_credit * 0.50 * multiplier

        total_outflows = (
            deposit_outflows +
            repo_outflow +
            fhlb_outflow +
            derivative_outflow +
            commitment_draws +
            loc_draws
        )

        return {
            "stress_level": stress_level.value,
            "deposit_outflows": deposit_outflows,
            "deposit_detail": deposit_detail,
            "repo_outflows": repo_outflow,
            "fhlb_outflows": fhlb_outflow,
            "derivative_outflows": derivative_outflow,
            "commitment_draws": commitment_draws,
            "loc_draws": loc_draws,
            "total_outflows": total_outflows,
        }

    def calculate_cash_inflows(self) -> Dict[str, float]:
        """
        Calculate 30-day cash inflows.

        Inflow categories:
        1. Maturing loans
        2. Maturing securities
        3. Interbank lending maturities

        Note: Inflows capped at 75% of outflows per LCR rules.
        """
        # Loan maturities (assume 5% of loans mature within 30 days)
        total_loans = sum(
            a.book_value for a in self.bank.assets
            if "loan" in a.name.lower()
        )
        loan_inflows = total_loans * 0.05

        # Securities maturities (based on maturity profile)
        securities_inflows = 0.0
        for asset in self.bank.assets:
            if asset.maturity_days <= 30:
                securities_inflows += asset.market_value

        # Interbank receivables
        interbank_inflows = sum(self.bank.interbank_assets.values()) * 0.20

        total_inflows = loan_inflows + securities_inflows + interbank_inflows

        return {
            "loan_inflows": loan_inflows,
            "securities_inflows": securities_inflows,
            "interbank_inflows": interbank_inflows,
            "total_inflows_uncapped": total_inflows,
        }

    def calculate_lcr(self, stress_level: LiquidityStressLevel = LiquidityStressLevel.SEVERE) -> Dict[str, float]:
        """
        Calculate Liquidity Coverage Ratio.

        LCR = Stock of HQLA / Total Net Cash Outflows over 30 days

        Minimum requirement: 100%
        """
        hqla = self.calculate_hqla_composition()
        outflows = self.calculate_cash_outflows(stress_level)
        inflows = self.calculate_cash_inflows()

        # Net outflows (inflows capped at 75% of outflows)
        inflow_cap = outflows["total_outflows"] * 0.75
        capped_inflows = min(inflows["total_inflows_uncapped"], inflow_cap)
        net_outflows = outflows["total_outflows"] - capped_inflows

        lcr = hqla["total_hqla"] / net_outflows if net_outflows > 0 else float('inf')

        return {
            "hqla": hqla["total_hqla"],
            "gross_outflows": outflows["total_outflows"],
            "gross_inflows": inflows["total_inflows_uncapped"],
            "capped_inflows": capped_inflows,
            "net_outflows": net_outflows,
            "lcr_ratio": lcr,
            "lcr_pct": lcr * 100,
            "meets_requirement": lcr >= 1.0,
            "surplus_deficit_days": (hqla["total_hqla"] - net_outflows) / (net_outflows / 30) if net_outflows > 0 else float('inf'),
        }

    def calculate_nsfr(self) -> Dict[str, float]:
        """
        Calculate Net Stable Funding Ratio.

        NSFR = Available Stable Funding / Required Stable Funding

        Measures funding stability over 1-year horizon.
        Minimum requirement: 100%
        """
        # Available Stable Funding (ASF)
        # Tier 1 + Tier 2 capital: 100% ASF
        capital_asf = self.bank.capital.total_capital

        # Stable deposits: 95% ASF
        stable_deposits = sum(
            d.amount for d in self.bank.deposits
            if d.deposit_type in [DepositType.INSURED_RETAIL_STABLE]
        )
        stable_deposit_asf = stable_deposits * 0.95

        # Less stable deposits: 90% ASF
        less_stable_deposits = sum(
            d.amount for d in self.bank.deposits
            if d.deposit_type in [DepositType.INSURED_RETAIL_LESS_STABLE, DepositType.UNINSURED_RETAIL]
        )
        less_stable_asf = less_stable_deposits * 0.90

        # Wholesale operational: 50% ASF
        operational_wholesale = sum(
            d.amount for d in self.bank.deposits
            if d.deposit_type == DepositType.OPERATIONAL_WHOLESALE
        )
        operational_asf = operational_wholesale * 0.50

        # Non-operational wholesale: 0-50% ASF depending on maturity
        non_op_wholesale = sum(
            d.amount for d in self.bank.deposits
            if d.deposit_type in [DepositType.NON_OPERATIONAL_WHOLESALE, DepositType.UNINSURED_WHOLESALE]
        )
        non_op_asf = non_op_wholesale * 0.25  # Assume short-term

        # Long-term debt > 1 year: 100% ASF
        long_term_debt = self.bank.other_borrowings * 0.50  # Assume half is long-term

        total_asf = (
            capital_asf +
            stable_deposit_asf +
            less_stable_asf +
            operational_asf +
            non_op_asf +
            long_term_debt
        )

        # Required Stable Funding (RSF)
        rsf_breakdown = {}
        total_rsf = 0.0

        for asset in self.bank.assets:
            # RSF factors based on asset type
            if asset.hqla_level == HQLALevel.LEVEL_1:
                rsf_factor = 0.0  # No RSF required
            elif asset.hqla_level == HQLALevel.LEVEL_2A:
                rsf_factor = 0.15
            elif asset.hqla_level == HQLALevel.LEVEL_2B:
                rsf_factor = 0.50
            elif "loan" in asset.name.lower():
                rsf_factor = 0.65 if "residential" in asset.name.lower() else 0.85
            else:
                rsf_factor = 1.0  # Default 100% RSF

            rsf = asset.book_value * rsf_factor
            rsf_breakdown[asset.name] = {
                "value": asset.book_value,
                "rsf_factor": rsf_factor,
                "rsf": rsf,
            }
            total_rsf += rsf

        # Off-balance sheet RSF
        obs_rsf = self.bank.unfunded_commitments * 0.05
        total_rsf += obs_rsf

        nsfr = total_asf / total_rsf if total_rsf > 0 else float('inf')

        return {
            "available_stable_funding": {
                "capital": capital_asf,
                "stable_deposits": stable_deposit_asf,
                "less_stable_deposits": less_stable_asf,
                "operational_wholesale": operational_asf,
                "non_operational_wholesale": non_op_asf,
                "long_term_debt": long_term_debt,
                "total": total_asf,
            },
            "required_stable_funding": {
                "by_asset": rsf_breakdown,
                "off_balance_sheet": obs_rsf,
                "total": total_rsf,
            },
            "nsfr_ratio": nsfr,
            "nsfr_pct": nsfr * 100,
            "meets_requirement": nsfr >= 1.0,
            "funding_gap": total_asf - total_rsf,
        }

    def project_liquidity(
        self,
        days: int = 30,
        stress_level: LiquidityStressLevel = LiquidityStressLevel.SEVERE,
        panic_onset_day: Optional[int] = None
    ) -> List[CashFlowProjection]:
        """
        Project daily liquidity position under stress.

        Models how quickly a bank can run out of liquidity,
        similar to what happened with SVB over March 8-10, 2023.
        """
        projections = []
        hqla = self.calculate_hqla_composition()["total_hqla"]
        current_liquidity = hqla

        # Base daily outflow rate
        monthly_outflows = self.calculate_cash_outflows(stress_level)["total_outflows"]
        base_daily_outflow = monthly_outflows / 30

        # Base daily inflows
        monthly_inflows = self.calculate_cash_inflows()["total_inflows_uncapped"]
        daily_inflows = monthly_inflows / 30

        for day in range(1, days + 1):
            # Panic multiplier if we're past the onset day
            if panic_onset_day and day >= panic_onset_day:
                # Panic accelerates exponentially for first few days
                days_since_panic = day - panic_onset_day
                panic_multiplier = min(5.0, 1.0 + (days_since_panic * 0.5) ** 1.5)
            else:
                panic_multiplier = 1.0

            daily_outflows = base_daily_outflow * panic_multiplier

            # Inflows may decrease during panic (asset fire sales at discount)
            adjusted_inflows = daily_inflows * (1.0 / panic_multiplier)

            net_flow = adjusted_inflows - daily_outflows
            current_liquidity += net_flow

            projections.append(CashFlowProjection(
                day=day,
                inflows=adjusted_inflows,
                outflows=daily_outflows,
                net_flow=net_flow,
                cumulative_flow=sum(p.net_flow for p in projections) + net_flow,
                liquidity_position=current_liquidity,
            ))

        return projections

    def calculate_survival_days(
        self,
        stress_level: LiquidityStressLevel = LiquidityStressLevel.SEVERE,
        panic_onset_day: int = 1
    ) -> Dict[str, float]:
        """
        Calculate how many days until liquidity exhaustion.

        SVB went from announcement to failure in ~40 hours.
        """
        projections = self.project_liquidity(
            days=90,
            stress_level=stress_level,
            panic_onset_day=panic_onset_day
        )

        # Find day when liquidity goes negative
        failure_day = None
        for proj in projections:
            if proj.liquidity_position <= 0:
                failure_day = proj.day
                break

        return {
            "stress_level": stress_level.value,
            "panic_onset_day": panic_onset_day,
            "initial_hqla": self.calculate_hqla_composition()["total_hqla"],
            "survival_days": failure_day if failure_day else ">90",
            "survives_30_days": failure_day is None or failure_day > 30,
            "day_30_liquidity": projections[29].liquidity_position if len(projections) >= 30 else None,
            "projections": projections[:30],  # First 30 days
        }

    def deposit_concentration_analysis(self) -> Dict[str, float]:
        """
        Analyze deposit concentration risk.

        SVB had 94% uninsured deposits and high concentration
        in the tech/VC sector - a deadly combination.
        """
        total_deposits = self.bank.total_deposits
        uninsured = sum(d.amount for d in self.bank.deposits if not d.is_insured)
        insured = total_deposits - uninsured

        # Concentration by depositor type
        by_type = {}
        for deposit in self.bank.deposits:
            dtype = deposit.depositor_type
            by_type[dtype] = by_type.get(dtype, 0) + deposit.amount

        # Single name concentrations
        max_concentration = max(d.concentration_pct for d in self.bank.deposits)

        return {
            "total_deposits": total_deposits,
            "insured_deposits": insured,
            "uninsured_deposits": uninsured,
            "uninsured_ratio": uninsured / total_deposits if total_deposits > 0 else 0,
            "insured_ratio": insured / total_deposits if total_deposits > 0 else 0,
            "by_depositor_type": by_type,
            "max_single_depositor_concentration": max_concentration,
            "risk_assessment": self._assess_deposit_risk(uninsured / total_deposits if total_deposits > 0 else 0),
        }

    def _assess_deposit_risk(self, uninsured_ratio: float) -> Dict[str, str]:
        """Assess deposit flight risk based on concentration"""
        if uninsured_ratio >= 0.80:
            level = "critical"
            description = "Extremely high uninsured deposit concentration. Vulnerable to rapid run."
            recommendation = "Urgently diversify funding sources and reduce uninsured concentration."
        elif uninsured_ratio >= 0.60:
            level = "high"
            description = "High uninsured deposit concentration. Significant run risk."
            recommendation = "Develop contingency funding plan. Consider deposit insurance strategies."
        elif uninsured_ratio >= 0.40:
            level = "moderate"
            description = "Moderate uninsured deposit concentration. Manageable run risk."
            recommendation = "Monitor concentration trends. Maintain robust HQLA buffer."
        else:
            level = "low"
            description = "Healthy deposit insurance coverage. Lower run risk."
            recommendation = "Continue monitoring funding stability."

        return {
            "risk_level": level,
            "description": description,
            "recommendation": recommendation,
        }

    def generate_liquidity_report(self) -> Dict:
        """Generate comprehensive liquidity risk report"""
        hqla = self.calculate_hqla_composition()
        lcr = self.calculate_lcr()
        nsfr = self.calculate_nsfr()
        deposits = self.deposit_concentration_analysis()

        # Survival analysis at different stress levels
        survival = {
            level.value: self.calculate_survival_days(level, panic_onset_day=1)
            for level in LiquidityStressLevel
        }

        return {
            "bank_name": self.bank.name,
            "hqla_composition": hqla,
            "liquidity_coverage_ratio": lcr,
            "net_stable_funding_ratio": nsfr,
            "deposit_concentration": deposits,
            "survival_analysis": survival,
            "regulatory_status": {
                "lcr_compliant": lcr["meets_requirement"],
                "nsfr_compliant": nsfr["meets_requirement"],
                "overall_assessment": "PASS" if lcr["meets_requirement"] and nsfr["meets_requirement"] else "FAIL",
            },
        }
