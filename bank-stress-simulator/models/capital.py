"""
Basel III Capital Adequacy Calculator

Implements the standardized approach for calculating risk-weighted assets
and capital ratios per the Basel III framework.

Key regulatory references:
- Basel III: A global regulatory framework for more resilient banks (BCBS 189)
- Basel III: Finalising post-crisis reforms (BCBS 424) - "Basel III Endgame"
- Federal Reserve Regulation Q (12 CFR 217)
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
from enum import Enum

from models.bank import Bank, Asset, AssetClass, RISK_WEIGHTS


class StressScenario(Enum):
    """Federal Reserve stress test scenarios"""
    BASELINE = "baseline"
    ADVERSE = "adverse"
    SEVERELY_ADVERSE = "severely_adverse"


@dataclass
class CapitalRequirements:
    """Basel III capital requirements with buffers"""
    # Minimum requirements
    min_cet1_ratio: float = 0.045      # 4.5%
    min_tier1_ratio: float = 0.06      # 6.0%
    min_total_capital_ratio: float = 0.08  # 8.0%

    # Buffers
    capital_conservation_buffer: float = 0.025  # 2.5%
    countercyclical_buffer: float = 0.0         # 0-2.5%, set by regulators
    gsib_surcharge: float = 0.0                 # 1-3.5% for G-SIBs

    # Leverage ratio
    min_leverage_ratio: float = 0.04   # 4% for most banks
    supplementary_leverage_ratio: float = 0.03  # Additional for G-SIBs

    @property
    def total_cet1_requirement(self) -> float:
        """Total CET1 requirement including all buffers"""
        return (self.min_cet1_ratio +
                self.capital_conservation_buffer +
                self.countercyclical_buffer +
                self.gsib_surcharge)

    @property
    def total_tier1_requirement(self) -> float:
        return (self.min_tier1_ratio +
                self.capital_conservation_buffer +
                self.countercyclical_buffer +
                self.gsib_surcharge)

    @property
    def total_capital_requirement(self) -> float:
        return (self.min_total_capital_ratio +
                self.capital_conservation_buffer +
                self.countercyclical_buffer +
                self.gsib_surcharge)


class CapitalAnalyzer:
    """
    Comprehensive capital adequacy analysis engine.

    Performs Basel III capital calculations including:
    - Risk-weighted asset computation
    - Capital ratio analysis
    - Buffer utilization
    - Stress testing under DFAST/CCAR scenarios
    """

    def __init__(self, bank: Bank):
        self.bank = bank
        self.requirements = CapitalRequirements(
            gsib_surcharge=bank.gsib_surcharge_pct if bank.is_gsib else 0
        )

    def calculate_rwa_by_category(self) -> Dict[AssetClass, float]:
        """Break down RWA by asset class"""
        rwa_by_class: Dict[AssetClass, float] = {}
        for asset in self.bank.assets:
            current = rwa_by_class.get(asset.asset_class, 0)
            rwa_by_class[asset.asset_class] = current + asset.risk_weighted_value
        return rwa_by_class

    def calculate_operational_risk_rwa(self) -> float:
        """
        Basel III Standardized Approach for operational risk.
        Based on Business Indicator Component (BIC).
        Simplified: using ~12% of average gross income proxy.
        """
        # Proxy: 12% of interest income + fee income
        # In practice, this would use actual business indicator data
        estimated_gross_income = self.bank.total_assets * 0.03  # ~3% of assets
        operational_rwa = estimated_gross_income * 0.12 * 12.5  # 12.5x multiplier
        return operational_rwa

    def calculate_market_risk_rwa(self) -> float:
        """
        Market risk RWA for trading book.
        Simplified calculation using standardized approach.
        """
        # Only applies to trading assets
        trading_assets = sum(
            a.market_value for a in self.bank.assets
            if "trading" in a.name.lower()
        )
        # Simplified: 8% capital charge → 12.5x RWA multiplier
        return trading_assets * 0.08 * 12.5

    def calculate_total_rwa(self) -> Dict[str, float]:
        """Calculate all components of RWA"""
        credit_rwa = self.bank.total_rwa
        operational_rwa = self.calculate_operational_risk_rwa()
        market_rwa = self.calculate_market_risk_rwa()

        return {
            "credit_risk_rwa": credit_rwa,
            "operational_risk_rwa": operational_rwa,
            "market_risk_rwa": market_rwa,
            "total_rwa": credit_rwa + operational_rwa + market_rwa,
        }

    def calculate_capital_ratios(self) -> Dict[str, float]:
        """Calculate all Basel III capital ratios"""
        total_rwa = self.calculate_total_rwa()["total_rwa"]

        return {
            "cet1_ratio": self.bank.capital.cet1_capital / total_rwa if total_rwa > 0 else 0,
            "tier1_ratio": self.bank.capital.tier1_capital / total_rwa if total_rwa > 0 else 0,
            "total_capital_ratio": self.bank.capital.total_capital / total_rwa if total_rwa > 0 else 0,
            "leverage_ratio": self.bank.leverage_ratio,
            "total_rwa": total_rwa,
        }

    def calculate_buffer_utilization(self) -> Dict[str, Dict[str, float]]:
        """
        Calculate how much of each buffer the bank is using.
        If buffers are penetrated, dividend/bonus restrictions apply.
        """
        ratios = self.calculate_capital_ratios()
        cet1 = ratios["cet1_ratio"]

        # CET1 buffer analysis
        min_cet1 = self.requirements.min_cet1_ratio
        ccb = self.requirements.capital_conservation_buffer
        ccyb = self.requirements.countercyclical_buffer
        gsib = self.requirements.gsib_surcharge

        # How much CET1 is available for each buffer layer
        excess_over_min = max(0, cet1 - min_cet1)

        # Buffer utilization (0 = fully utilized, 1 = not used at all)
        gsib_remaining = min(gsib, excess_over_min) / gsib if gsib > 0 else 1.0
        excess_after_gsib = max(0, excess_over_min - gsib)

        ccyb_remaining = min(ccyb, excess_after_gsib) / ccyb if ccyb > 0 else 1.0
        excess_after_ccyb = max(0, excess_after_gsib - ccyb)

        ccb_remaining = min(ccb, excess_after_ccyb) / ccb if ccb > 0 else 1.0

        return {
            "gsib_buffer": {
                "required": gsib,
                "available": min(gsib, excess_over_min),
                "utilization_pct": 1 - gsib_remaining,
            },
            "countercyclical_buffer": {
                "required": ccyb,
                "available": min(ccyb, excess_after_gsib),
                "utilization_pct": 1 - ccyb_remaining,
            },
            "conservation_buffer": {
                "required": ccb,
                "available": min(ccb, excess_after_ccyb),
                "utilization_pct": 1 - ccb_remaining,
            },
        }

    def stress_test_capital(
        self,
        scenario: StressScenario,
        custom_params: Optional[Dict] = None
    ) -> Dict[str, float]:
        """
        Apply stress scenario to capital.

        Scenarios based on Federal Reserve DFAST parameters:
        - Baseline: Normal economic conditions
        - Adverse: Mild recession
        - Severely Adverse: Deep recession with market stress
        """
        # Default stress parameters (loss rates, RWA growth)
        stress_params = {
            StressScenario.BASELINE: {
                "loan_loss_rate": 0.01,      # 1% cumulative losses
                "securities_markdown": 0.0,   # No additional markdown
                "rwa_growth": 0.02,          # 2% RWA growth
                "net_income_impact": 0.0,    # Normal profitability
            },
            StressScenario.ADVERSE: {
                "loan_loss_rate": 0.04,      # 4% cumulative losses
                "securities_markdown": 0.05,  # 5% additional markdown
                "rwa_growth": 0.05,          # 5% RWA growth
                "net_income_impact": -0.02,  # 2% hit to pre-provision income
            },
            StressScenario.SEVERELY_ADVERSE: {
                "loan_loss_rate": 0.08,      # 8% cumulative losses
                "securities_markdown": 0.15,  # 15% additional markdown
                "rwa_growth": 0.10,          # 10% RWA growth
                "net_income_impact": -0.04,  # 4% hit
            },
        }

        params = custom_params or stress_params[scenario]

        # Calculate stressed capital
        current_cet1 = self.bank.capital.cet1_capital

        # Loan losses hit retained earnings
        total_loans = sum(
            a.book_value for a in self.bank.assets
            if "loan" in a.name.lower() or "mortgage" in a.name.lower()
        )
        loan_losses = total_loans * params["loan_loss_rate"]

        # Securities markdowns hit AOCI (and CET1 if AOCI filter removed)
        total_securities = sum(
            a.market_value for a in self.bank.assets
            if any(x in a.name.lower() for x in ["treasury", "mbs", "bond", "securities"])
        )
        securities_losses = total_securities * params["securities_markdown"]

        # Pre-provision net revenue impact
        ppnr_impact = self.bank.total_assets * params["net_income_impact"]

        # Stressed capital
        stressed_cet1 = current_cet1 - loan_losses - securities_losses + ppnr_impact

        # Stressed RWA
        current_rwa = self.calculate_total_rwa()["total_rwa"]
        stressed_rwa = current_rwa * (1 + params["rwa_growth"])

        # Stressed ratios
        stressed_cet1_ratio = stressed_cet1 / stressed_rwa if stressed_rwa > 0 else 0
        stressed_tier1_ratio = (
            (self.bank.capital.tier1_capital - loan_losses - securities_losses + ppnr_impact) /
            stressed_rwa if stressed_rwa > 0 else 0
        )

        return {
            "scenario": scenario.value,
            "pre_stress_cet1": current_cet1,
            "loan_losses": loan_losses,
            "securities_losses": securities_losses,
            "ppnr_impact": ppnr_impact,
            "stressed_cet1": stressed_cet1,
            "stressed_cet1_ratio": stressed_cet1_ratio,
            "stressed_tier1_ratio": stressed_tier1_ratio,
            "capital_shortfall": max(0,
                self.requirements.total_cet1_requirement * stressed_rwa - stressed_cet1
            ),
            "passes_stress_test": stressed_cet1_ratio >= self.requirements.total_cet1_requirement,
        }

    def interest_rate_sensitivity(self, rate_shock_bps: int) -> Dict[str, float]:
        """
        Calculate capital impact of interest rate shock.
        This is what killed SVB - they had massive duration risk.
        """
        total_mtm_impact = 0.0
        asset_impacts = []

        for asset in self.bank.assets:
            if asset.duration > 0:
                impact = asset.apply_interest_rate_shock(rate_shock_bps)
                total_mtm_impact += impact
                asset_impacts.append({
                    "asset": asset.name,
                    "duration": asset.duration,
                    "market_value": asset.market_value,
                    "mtm_impact": impact,
                })

        # Impact on capital (if AOCI filter removed)
        current_cet1 = self.bank.capital.cet1_capital
        post_shock_cet1 = current_cet1 + total_mtm_impact

        current_rwa = self.calculate_total_rwa()["total_rwa"]

        return {
            "rate_shock_bps": rate_shock_bps,
            "total_mtm_impact": total_mtm_impact,
            "pre_shock_cet1": current_cet1,
            "post_shock_cet1": post_shock_cet1,
            "pre_shock_cet1_ratio": current_cet1 / current_rwa if current_rwa > 0 else 0,
            "post_shock_cet1_ratio": post_shock_cet1 / current_rwa if current_rwa > 0 else 0,
            "cet1_ratio_change": (post_shock_cet1 - current_cet1) / current_rwa if current_rwa > 0 else 0,
            "asset_level_impacts": asset_impacts,
        }

    def aoci_filter_impact(self) -> Dict[str, float]:
        """
        Calculate impact of removing the AOCI filter.

        Under current rules (for non-advanced approaches banks),
        unrealized gains/losses on AFS securities don't flow through
        to regulatory capital. Basel III endgame proposes removing
        this filter, which would have shown SVB's true capital position.
        """
        # Current unrealized gains/losses
        unrealized = sum(a.unrealized_gain_loss for a in self.bank.assets)

        current_cet1 = self.bank.capital.cet1_capital
        # If filter removed, AOCI flows through
        adjusted_cet1 = current_cet1 + unrealized

        current_rwa = self.calculate_total_rwa()["total_rwa"]

        return {
            "unrealized_gains_losses": unrealized,
            "current_cet1_with_filter": current_cet1,
            "cet1_without_filter": adjusted_cet1,
            "current_cet1_ratio": current_cet1 / current_rwa if current_rwa > 0 else 0,
            "adjusted_cet1_ratio": adjusted_cet1 / current_rwa if current_rwa > 0 else 0,
            "ratio_impact": (adjusted_cet1 - current_cet1) / current_rwa if current_rwa > 0 else 0,
        }

    def generate_capital_report(self) -> Dict:
        """Generate comprehensive capital adequacy report"""
        ratios = self.calculate_capital_ratios()
        rwa_breakdown = self.calculate_rwa_by_category()
        buffers = self.calculate_buffer_utilization()
        aoci_impact = self.aoci_filter_impact()

        # Run all stress scenarios
        stress_results = {
            scenario.value: self.stress_test_capital(scenario)
            for scenario in StressScenario
        }

        # Interest rate sensitivity at various shocks
        rate_shocks = [100, 200, 300, 400]
        rate_sensitivity = {
            f"+{shock}bps": self.interest_rate_sensitivity(shock)
            for shock in rate_shocks
        }

        return {
            "bank_name": self.bank.name,
            "total_assets": self.bank.total_assets,
            "capital_structure": {
                "cet1": self.bank.capital.cet1_capital,
                "at1": self.bank.capital.at1_capital,
                "tier1": self.bank.capital.tier1_capital,
                "tier2": self.bank.capital.tier2_capital,
                "total_capital": self.bank.capital.total_capital,
            },
            "capital_ratios": ratios,
            "requirements": {
                "cet1": self.requirements.total_cet1_requirement,
                "tier1": self.requirements.total_tier1_requirement,
                "total": self.requirements.total_capital_requirement,
                "leverage": self.requirements.min_leverage_ratio,
            },
            "rwa_breakdown": {k.value: v for k, v in rwa_breakdown.items()},
            "buffer_utilization": buffers,
            "aoci_filter_impact": aoci_impact,
            "stress_test_results": stress_results,
            "interest_rate_sensitivity": rate_sensitivity,
            "regulatory_status": self._determine_regulatory_status(ratios),
        }

    def _determine_regulatory_status(self, ratios: Dict[str, float]) -> Dict[str, str]:
        """Determine PCA (Prompt Corrective Action) category"""
        cet1 = ratios["cet1_ratio"]
        tier1 = ratios["tier1_ratio"]
        total = ratios["total_capital_ratio"]
        leverage = ratios["leverage_ratio"]

        # PCA categories per 12 USC 1831o
        if cet1 >= 0.065 and tier1 >= 0.08 and total >= 0.10 and leverage >= 0.05:
            category = "well_capitalized"
            description = "Exceeds all capital requirements"
        elif cet1 >= 0.045 and tier1 >= 0.06 and total >= 0.08 and leverage >= 0.04:
            category = "adequately_capitalized"
            description = "Meets minimum requirements"
        elif cet1 >= 0.03 or tier1 >= 0.04 or total >= 0.06 or leverage >= 0.03:
            category = "undercapitalized"
            description = "Subject to mandatory restrictions"
        elif cet1 >= 0.02 or tier1 >= 0.03 or total >= 0.04:
            category = "significantly_undercapitalized"
            description = "Subject to enhanced restrictions"
        else:
            category = "critically_undercapitalized"
            description = "Subject to receivership within 90 days"

        return {
            "pca_category": category,
            "description": description,
            "enforcement_actions": self._get_enforcement_actions(category),
        }

    def _get_enforcement_actions(self, category: str) -> List[str]:
        """List enforcement actions for each PCA category"""
        actions = {
            "well_capitalized": [],
            "adequately_capitalized": [
                "Cannot accept brokered deposits without FDIC approval"
            ],
            "undercapitalized": [
                "Must submit capital restoration plan",
                "Asset growth restricted",
                "Requires approval for acquisitions/new activities",
                "Cannot pay dividends that would worsen condition",
            ],
            "significantly_undercapitalized": [
                "All undercapitalized restrictions plus:",
                "Must sell shares or be acquired",
                "Restrictions on executive compensation",
                "Must divest troubled subsidiaries",
            ],
            "critically_undercapitalized": [
                "All above restrictions plus:",
                "Receiver/conservator appointment within 90 days",
                "Cannot pay principal/interest on subordinated debt",
                "Subject to least-cost resolution",
            ],
        }
        return actions.get(category, [])
