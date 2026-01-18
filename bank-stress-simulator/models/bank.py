"""
Bank Entity Model

Models a bank's balance sheet with the granularity required for
Basel III capital calculations and liquidity stress testing.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum
import random


class AssetClass(Enum):
    """Risk-weighted asset classes per Basel III standardized approach"""
    CASH = "cash"
    SOVEREIGNS_0 = "sovereigns_0pct"      # 0% risk weight (US Treasury, etc.)
    SOVEREIGNS_20 = "sovereigns_20pct"    # 20% risk weight
    PSE = "public_sector_entities"         # 20% risk weight
    BANKS_20 = "banks_20pct"              # 20% risk weight (short-term)
    BANKS_50 = "banks_50pct"              # 50% risk weight (long-term)
    CORPORATE_20 = "corporate_20pct"      # 20% investment grade
    CORPORATE_50 = "corporate_50pct"      # 50%
    CORPORATE_100 = "corporate_100pct"    # 100% standard corporate
    RETAIL = "retail"                      # 75% risk weight
    RESIDENTIAL_MORTGAGE = "resi_mortgage" # 35-100% based on LTV
    COMMERCIAL_RE = "commercial_re"        # 100% risk weight
    EQUITY = "equity"                      # 100-400% risk weight
    SECURITIZATION = "securitization"      # Varies widely
    OTHER = "other"                        # 100% default


# Basel III risk weights by asset class
RISK_WEIGHTS = {
    AssetClass.CASH: 0.0,
    AssetClass.SOVEREIGNS_0: 0.0,
    AssetClass.SOVEREIGNS_20: 0.20,
    AssetClass.PSE: 0.20,
    AssetClass.BANKS_20: 0.20,
    AssetClass.BANKS_50: 0.50,
    AssetClass.CORPORATE_20: 0.20,
    AssetClass.CORPORATE_50: 0.50,
    AssetClass.CORPORATE_100: 1.00,
    AssetClass.RETAIL: 0.75,
    AssetClass.RESIDENTIAL_MORTGAGE: 0.50,  # Simplified; actual varies by LTV
    AssetClass.COMMERCIAL_RE: 1.00,
    AssetClass.EQUITY: 2.50,  # Using higher weight for unlisted
    AssetClass.SECURITIZATION: 1.00,  # Simplified
    AssetClass.OTHER: 1.00,
}


class DepositType(Enum):
    """Deposit categories for run-off analysis"""
    INSURED_RETAIL_STABLE = "insured_retail_stable"      # 3% run-off
    INSURED_RETAIL_LESS_STABLE = "insured_retail_less"   # 10% run-off
    UNINSURED_RETAIL = "uninsured_retail"                # 10-20% run-off
    OPERATIONAL_WHOLESALE = "operational_wholesale"       # 25% run-off
    NON_OPERATIONAL_WHOLESALE = "non_op_wholesale"       # 40% run-off
    UNINSURED_WHOLESALE = "uninsured_wholesale"          # 100% run-off in stress


# LCR run-off rates under 30-day stress scenario
DEPOSIT_RUNOFF_RATES = {
    DepositType.INSURED_RETAIL_STABLE: 0.03,
    DepositType.INSURED_RETAIL_LESS_STABLE: 0.10,
    DepositType.UNINSURED_RETAIL: 0.20,
    DepositType.OPERATIONAL_WHOLESALE: 0.25,
    DepositType.NON_OPERATIONAL_WHOLESALE: 0.40,
    DepositType.UNINSURED_WHOLESALE: 1.00,
}


class HQLALevel(Enum):
    """High-Quality Liquid Asset levels for LCR"""
    LEVEL_1 = "level_1"      # No haircut (cash, reserves, sovereigns)
    LEVEL_2A = "level_2a"    # 15% haircut (GSE, high-grade corporate)
    LEVEL_2B = "level_2b"    # 25-50% haircut (lower-grade assets)


HQLA_HAIRCUTS = {
    HQLALevel.LEVEL_1: 0.0,
    HQLALevel.LEVEL_2A: 0.15,
    HQLALevel.LEVEL_2B: 0.50,
}


@dataclass
class Asset:
    """Individual asset on bank balance sheet"""
    name: str
    book_value: float
    market_value: float
    asset_class: AssetClass
    hqla_level: Optional[HQLALevel] = None
    duration: float = 0.0  # Modified duration for interest rate risk
    yield_rate: float = 0.0
    maturity_days: int = 365

    @property
    def risk_weighted_value(self) -> float:
        """Calculate RWA contribution"""
        return self.book_value * RISK_WEIGHTS[self.asset_class]

    @property
    def unrealized_gain_loss(self) -> float:
        """Mark-to-market gain/loss"""
        return self.market_value - self.book_value

    def apply_interest_rate_shock(self, rate_change_bps: int) -> float:
        """Calculate market value change from rate shock"""
        rate_change = rate_change_bps / 10000
        price_change = -self.duration * rate_change * self.market_value
        return price_change


@dataclass
class Deposit:
    """Deposit liability with run-off characteristics"""
    name: str
    amount: float
    deposit_type: DepositType
    is_insured: bool
    depositor_type: str  # "retail", "corporate", "financial", "government"
    concentration_pct: float = 0.0  # % of total deposits from single depositor

    @property
    def stress_runoff(self) -> float:
        """30-day stress run-off amount"""
        return self.amount * DEPOSIT_RUNOFF_RATES[self.deposit_type]

    def apply_panic_multiplier(self, panic_level: float) -> float:
        """
        Apply social media / news-driven panic multiplier.
        SVB showed how fast uninsured deposits can flee.
        """
        base_runoff = DEPOSIT_RUNOFF_RATES[self.deposit_type]
        # Uninsured deposits are much more sensitive to panic
        if not self.is_insured:
            panic_multiplier = 1 + (panic_level * 3)  # Up to 4x normal run-off
        else:
            panic_multiplier = 1 + (panic_level * 0.5)  # Insured less sensitive
        return min(self.amount, self.amount * base_runoff * panic_multiplier)


@dataclass
class Capital:
    """Bank capital structure per Basel III"""
    # CET1 components
    common_stock: float = 0.0
    retained_earnings: float = 0.0
    accumulated_other_comprehensive_income: float = 0.0  # AOCI

    # AT1 components
    perpetual_preferred: float = 0.0
    contingent_convertibles: float = 0.0  # CoCos

    # Tier 2 components
    subordinated_debt: float = 0.0
    loan_loss_reserves: float = 0.0

    # Regulatory deductions
    goodwill: float = 0.0
    deferred_tax_assets: float = 0.0

    @property
    def cet1_capital(self) -> float:
        """Common Equity Tier 1"""
        gross = self.common_stock + self.retained_earnings + self.accumulated_other_comprehensive_income
        deductions = self.goodwill + self.deferred_tax_assets
        return max(0, gross - deductions)

    @property
    def at1_capital(self) -> float:
        """Additional Tier 1"""
        return self.perpetual_preferred + self.contingent_convertibles

    @property
    def tier1_capital(self) -> float:
        """Total Tier 1 = CET1 + AT1"""
        return self.cet1_capital + self.at1_capital

    @property
    def tier2_capital(self) -> float:
        """Tier 2 capital"""
        return self.subordinated_debt + self.loan_loss_reserves

    @property
    def total_capital(self) -> float:
        """Total regulatory capital"""
        return self.tier1_capital + self.tier2_capital


@dataclass
class Bank:
    """
    Complete bank entity model for stress testing.

    Designed to capture the key elements that matter for:
    - Capital adequacy (Basel III)
    - Liquidity (LCR/NSFR)
    - Resolution planning
    """
    name: str
    charter_type: str  # "national", "state_member", "state_nonmember"
    total_assets: float

    # Balance sheet components
    assets: List[Asset] = field(default_factory=list)
    deposits: List[Deposit] = field(default_factory=list)
    capital: Capital = field(default_factory=Capital)

    # Liability details
    other_borrowings: float = 0.0
    fhlb_advances: float = 0.0  # Federal Home Loan Bank
    repo_funding: float = 0.0

    # Off-balance sheet
    unfunded_commitments: float = 0.0
    letters_of_credit: float = 0.0
    derivatives_notional: float = 0.0

    # Systemic importance
    is_gsib: bool = False
    gsib_score: float = 0.0
    gsib_surcharge_pct: float = 0.0

    # Interbank exposures (for contagion modeling)
    interbank_assets: Dict[str, float] = field(default_factory=dict)
    interbank_liabilities: Dict[str, float] = field(default_factory=dict)

    @property
    def total_rwa(self) -> float:
        """Total risk-weighted assets"""
        asset_rwa = sum(a.risk_weighted_value for a in self.assets)
        # Simplified: add off-balance sheet with 10% credit conversion factor
        obs_rwa = (self.unfunded_commitments + self.letters_of_credit) * 0.10
        return asset_rwa + obs_rwa

    @property
    def total_deposits(self) -> float:
        return sum(d.amount for d in self.deposits)

    @property
    def uninsured_deposit_ratio(self) -> float:
        """Key metric that doomed SVB"""
        uninsured = sum(d.amount for d in self.deposits if not d.is_insured)
        total = self.total_deposits
        return uninsured / total if total > 0 else 0

    @property
    def hqla_total(self) -> float:
        """High-quality liquid assets (after haircuts)"""
        total = 0.0
        for asset in self.assets:
            if asset.hqla_level:
                haircut = HQLA_HAIRCUTS[asset.hqla_level]
                total += asset.market_value * (1 - haircut)
        return total

    @property
    def total_stress_outflows(self) -> float:
        """30-day stressed cash outflows for LCR"""
        deposit_outflows = sum(d.stress_runoff for d in self.deposits)
        # Add other outflows (simplified)
        commitment_draws = self.unfunded_commitments * 0.10  # 10% draw rate
        return deposit_outflows + commitment_draws

    @property
    def lcr_ratio(self) -> float:
        """Liquidity Coverage Ratio = HQLA / Net Cash Outflows"""
        outflows = self.total_stress_outflows
        if outflows == 0:
            return float('inf')
        return self.hqla_total / outflows

    @property
    def cet1_ratio(self) -> float:
        """CET1 capital ratio = CET1 / RWA"""
        rwa = self.total_rwa
        if rwa == 0:
            return float('inf')
        return self.capital.cet1_capital / rwa

    @property
    def tier1_ratio(self) -> float:
        """Tier 1 capital ratio"""
        rwa = self.total_rwa
        if rwa == 0:
            return float('inf')
        return self.capital.tier1_capital / rwa

    @property
    def total_capital_ratio(self) -> float:
        """Total capital ratio"""
        rwa = self.total_rwa
        if rwa == 0:
            return float('inf')
        return self.capital.total_capital / rwa

    @property
    def leverage_ratio(self) -> float:
        """Tier 1 leverage ratio = Tier 1 / Total Assets"""
        if self.total_assets == 0:
            return float('inf')
        return self.capital.tier1_capital / self.total_assets

    def calculate_minimum_capital_requirements(self) -> Dict[str, float]:
        """
        Basel III minimum capital requirements.
        Includes buffers and G-SIB surcharge if applicable.
        """
        rwa = self.total_rwa

        # Minimum ratios
        min_cet1 = 0.045  # 4.5%
        min_tier1 = 0.06  # 6%
        min_total = 0.08  # 8%

        # Capital Conservation Buffer: 2.5%
        ccb = 0.025

        # G-SIB surcharge if applicable
        gsib = self.gsib_surcharge_pct if self.is_gsib else 0

        # Countercyclical buffer (assume 0 for now, can be 0-2.5%)
        ccyb = 0.0

        return {
            "min_cet1_pct": min_cet1 + ccb + gsib + ccyb,
            "min_tier1_pct": min_tier1 + ccb + gsib + ccyb,
            "min_total_pct": min_total + ccb + gsib + ccyb,
            "min_cet1_amount": rwa * (min_cet1 + ccb + gsib + ccyb),
            "min_tier1_amount": rwa * (min_tier1 + ccb + gsib + ccyb),
            "min_total_amount": rwa * (min_total + ccb + gsib + ccyb),
        }

    def capital_surplus_deficit(self) -> Dict[str, float]:
        """Calculate capital surplus/deficit vs requirements"""
        reqs = self.calculate_minimum_capital_requirements()
        return {
            "cet1_surplus": self.capital.cet1_capital - reqs["min_cet1_amount"],
            "tier1_surplus": self.capital.tier1_capital - reqs["min_tier1_amount"],
            "total_surplus": self.capital.total_capital - reqs["min_total_amount"],
        }

    def apply_aoci_filter_removal(self) -> None:
        """
        Basel III endgame proposes removing the AOCI filter for Category III/IV banks.
        This means unrealized losses on AFS securities hit capital.
        SVB would have shown much lower capital with this rule.
        """
        unrealized = sum(a.unrealized_gain_loss for a in self.assets)
        self.capital.accumulated_other_comprehensive_income = unrealized


def create_sample_regional_bank(name: str = "First Regional Bank") -> Bank:
    """
    Create a sample regional bank (~$50B assets) similar to
    the profile of banks that failed in 2023.
    """
    bank = Bank(
        name=name,
        charter_type="state_member",
        total_assets=50_000_000_000,  # $50B
        is_gsib=False,
    )

    # Assets - note the heavy securities portfolio (like SVB)
    bank.assets = [
        Asset("Cash & Fed Reserves", 2_000_000_000, 2_000_000_000,
              AssetClass.CASH, HQLALevel.LEVEL_1, duration=0),
        Asset("US Treasuries", 8_000_000_000, 7_200_000_000,  # 10% unrealized loss
              AssetClass.SOVEREIGNS_0, HQLALevel.LEVEL_1, duration=6.5, yield_rate=0.02),
        Asset("Agency MBS", 12_000_000_000, 10_200_000_000,  # 15% unrealized loss
              AssetClass.SOVEREIGNS_20, HQLALevel.LEVEL_2A, duration=7.2, yield_rate=0.025),
        Asset("Municipal Bonds", 3_000_000_000, 2_700_000_000,
              AssetClass.PSE, HQLALevel.LEVEL_2A, duration=5.0, yield_rate=0.03),
        Asset("Commercial Loans", 15_000_000_000, 15_000_000_000,
              AssetClass.CORPORATE_100, duration=2.5, yield_rate=0.065),
        Asset("CRE Loans", 6_000_000_000, 6_000_000_000,
              AssetClass.COMMERCIAL_RE, duration=3.0, yield_rate=0.055),
        Asset("Residential Mortgages", 3_000_000_000, 2_850_000_000,
              AssetClass.RESIDENTIAL_MORTGAGE, duration=4.5, yield_rate=0.04),
        Asset("Other Assets", 1_000_000_000, 1_000_000_000, AssetClass.OTHER),
    ]

    # Deposits - high uninsured concentration (the SVB problem)
    bank.deposits = [
        Deposit("Retail Insured", 8_000_000_000,
                DepositType.INSURED_RETAIL_STABLE, is_insured=True, depositor_type="retail"),
        Deposit("Retail Uninsured", 4_000_000_000,
                DepositType.UNINSURED_RETAIL, is_insured=False, depositor_type="retail"),
        Deposit("Corporate Operating", 10_000_000_000,
                DepositType.OPERATIONAL_WHOLESALE, is_insured=False, depositor_type="corporate"),
        Deposit("Corporate Non-Operating", 12_000_000_000,
                DepositType.NON_OPERATIONAL_WHOLESALE, is_insured=False, depositor_type="corporate"),
        Deposit("VC/Startup Deposits", 8_000_000_000,  # The SVB special
                DepositType.UNINSURED_WHOLESALE, is_insured=False,
                depositor_type="corporate", concentration_pct=0.16),
    ]

    # Capital structure
    bank.capital = Capital(
        common_stock=1_500_000_000,
        retained_earnings=2_800_000_000,
        accumulated_other_comprehensive_income=0,  # AOCI filter in place
        perpetual_preferred=200_000_000,
        subordinated_debt=500_000_000,
        loan_loss_reserves=300_000_000,
        goodwill=150_000_000,
        deferred_tax_assets=50_000_000,
    )

    # Other funding
    bank.fhlb_advances = 3_000_000_000
    bank.repo_funding = 1_000_000_000
    bank.other_borrowings = 500_000_000

    # Off-balance sheet
    bank.unfunded_commitments = 5_000_000_000
    bank.letters_of_credit = 500_000_000

    return bank


def create_sample_gsib(name: str = "Global Systemically Important Bank") -> Bank:
    """Create a sample G-SIB (~$500B assets)"""
    bank = Bank(
        name=name,
        charter_type="national",
        total_assets=500_000_000_000,
        is_gsib=True,
        gsib_score=450,
        gsib_surcharge_pct=0.025,  # 2.5% G-SIB surcharge
    )

    # More diversified asset base
    bank.assets = [
        Asset("Cash & Reserves", 40_000_000_000, 40_000_000_000,
              AssetClass.CASH, HQLALevel.LEVEL_1),
        Asset("US Treasuries", 50_000_000_000, 48_000_000_000,
              AssetClass.SOVEREIGNS_0, HQLALevel.LEVEL_1, duration=4.0),
        Asset("Agency Securities", 40_000_000_000, 37_000_000_000,
              AssetClass.SOVEREIGNS_20, HQLALevel.LEVEL_2A, duration=5.5),
        Asset("Corporate Bonds IG", 30_000_000_000, 28_500_000_000,
              AssetClass.CORPORATE_20, HQLALevel.LEVEL_2A, duration=4.5),
        Asset("C&I Loans", 120_000_000_000, 120_000_000_000,
              AssetClass.CORPORATE_100, duration=2.0),
        Asset("CRE Loans", 50_000_000_000, 50_000_000_000,
              AssetClass.COMMERCIAL_RE, duration=3.5),
        Asset("Consumer Loans", 60_000_000_000, 60_000_000_000,
              AssetClass.RETAIL, duration=2.5),
        Asset("Residential Mortgages", 80_000_000_000, 76_000_000_000,
              AssetClass.RESIDENTIAL_MORTGAGE, duration=5.0),
        Asset("Trading Assets", 20_000_000_000, 20_000_000_000,
              AssetClass.OTHER, duration=0.5),
        Asset("Other Assets", 10_000_000_000, 10_000_000_000, AssetClass.OTHER),
    ]

    # More stable deposit base
    bank.deposits = [
        Deposit("Retail Insured", 100_000_000_000,
                DepositType.INSURED_RETAIL_STABLE, is_insured=True, depositor_type="retail"),
        Deposit("Retail Less Stable", 50_000_000_000,
                DepositType.INSURED_RETAIL_LESS_STABLE, is_insured=True, depositor_type="retail"),
        Deposit("Corporate Operating", 80_000_000_000,
                DepositType.OPERATIONAL_WHOLESALE, is_insured=False, depositor_type="corporate"),
        Deposit("Corporate Non-Op", 60_000_000_000,
                DepositType.NON_OPERATIONAL_WHOLESALE, is_insured=False, depositor_type="corporate"),
        Deposit("Financial Institution", 40_000_000_000,
                DepositType.UNINSURED_WHOLESALE, is_insured=False, depositor_type="financial"),
    ]

    bank.capital = Capital(
        common_stock=25_000_000_000,
        retained_earnings=35_000_000_000,
        accumulated_other_comprehensive_income=-2_000_000_000,
        perpetual_preferred=5_000_000_000,
        contingent_convertibles=3_000_000_000,
        subordinated_debt=8_000_000_000,
        loan_loss_reserves=4_000_000_000,
        goodwill=8_000_000_000,
        deferred_tax_assets=2_000_000_000,
    )

    bank.fhlb_advances = 15_000_000_000
    bank.repo_funding = 25_000_000_000
    bank.other_borrowings = 12_000_000_000
    bank.unfunded_commitments = 100_000_000_000
    bank.letters_of_credit = 20_000_000_000
    bank.derivatives_notional = 500_000_000_000

    return bank
