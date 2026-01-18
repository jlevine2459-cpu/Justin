# Bank Stress Testing & Resolution Simulator

A sophisticated terminal-based simulation tool for modeling bank capital adequacy, liquidity stress,
deposit flight scenarios, and resolution planning - designed to demonstrate understanding of modern
prudential bank regulation.

## Features

### 1. Basel III Capital Adequacy Calculator
- Common Equity Tier 1 (CET1) ratio computation
- Additional Tier 1 (AT1) capital treatment
- Tier 2 capital and total capital ratio
- Risk-weighted asset (RWA) calculations by asset class
- G-SIB surcharge modeling
- Countercyclical capital buffer (CCyB) scenarios

### 2. Liquidity Stress Testing
- Liquidity Coverage Ratio (LCR) under stress scenarios
- Net Stable Funding Ratio (NSFR) analysis
- High-Quality Liquid Assets (HQLA) categorization (Level 1, 2A, 2B)
- Cash flow projections under adverse scenarios

### 3. Bank Run Simulation
- Deposit flight modeling based on depositor characteristics
- Uninsured deposit concentration risk (the SVB problem)
- Social media contagion velocity factors
- Real-time visualization of liquidity drain

### 4. Systemic Risk & Contagion Network
- Interbank exposure modeling
- Counterparty credit risk propagation
- Fire sale externalities
- Network centrality analysis for systemically important institutions

### 5. Resolution Planning Module
- Bridge bank scenario modeling
- Least-cost resolution analysis
- Depositor preference and creditor hierarchy
- Cross-border resolution coordination factors

## Regulatory Framework References

This tool implements concepts from:
- Basel III Framework (BCBS)
- Dodd-Frank Act Title II (Orderly Liquidation Authority)
- FDIC regulations on deposit insurance and resolution
- Federal Reserve stress testing (CCAR/DFAST)
- OCC heightened standards

## Usage

```bash
python3 main.py
```

## Architecture

```
bank-stress-simulator/
├── main.py                 # Entry point with terminal UI
├── models/
│   ├── bank.py            # Bank entity model
│   ├── capital.py         # Basel III capital calculations
│   ├── liquidity.py       # LCR/NSFR calculations
│   └── resolution.py      # Resolution planning logic
├── simulation/
│   ├── stress_test.py     # Stress scenario engine
│   ├── bank_run.py        # Deposit flight simulation
│   └── contagion.py       # Network contagion model
└── visualization/
    └── terminal_ui.py     # Rich terminal graphics
```

## Author's Note

This simulator was built to demonstrate understanding of the complex regulatory landscape
that governs bank safety and soundness. The 2023 banking crisis (SVB, Signature, First Republic)
highlighted how quickly confidence can evaporate when uninsured deposits concentrate and
interest rate risk materializes on bank balance sheets.

As regulators continue to refine Basel III endgame rules and consider deposit insurance reform,
tools like this help visualize the interconnected nature of capital, liquidity, and resolution planning.
