#!/usr/bin/env python3
"""
Bank Stress Testing & Resolution Simulator

A comprehensive tool for modeling bank capital adequacy, liquidity stress,
deposit flight scenarios, and resolution planning - demonstrating understanding
of modern prudential bank regulation.

Based on:
- Basel III Framework (capital, liquidity)
- Federal Deposit Insurance Act (resolution)
- Lessons from 2023 banking crisis (SVB, Signature, First Republic)
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.bank import Bank, create_sample_regional_bank, create_sample_gsib
from models.capital import CapitalAnalyzer, StressScenario
from models.liquidity import LiquidityAnalyzer, LiquidityStressLevel
from models.resolution import ResolutionPlanner
from simulation.bank_run import BankRunSimulator, RunTrigger
from simulation.contagion import ContagionNetwork
from visualization.terminal_ui import (
    TerminalUI, Color, clear_screen,
    display_capital_report, display_liquidity_report,
    display_resolution_plan, display_contagion_analysis,
    animate_bank_run, format_currency, format_percentage
)


def print_menu():
    """Print the main menu"""
    print(f"""
{Color.CYAN}{Color.BOLD}╔══════════════════════════════════════════════════════════════════╗
║       BANK STRESS TESTING & RESOLUTION SIMULATOR                 ║
║                                                                  ║
║   A tool for exploring prudential bank regulation concepts       ║
╚══════════════════════════════════════════════════════════════════╝{Color.RESET}

{Color.YELLOW}Select an analysis module:{Color.RESET}

  {Color.BOLD}1.{Color.RESET} Capital Adequacy Analysis (Basel III)
     - CET1, Tier 1, Total Capital ratios
     - Risk-weighted assets breakdown
     - Stress test scenarios (DFAST)
     - Interest rate sensitivity

  {Color.BOLD}2.{Color.RESET} Liquidity Risk Analysis
     - LCR (Liquidity Coverage Ratio)
     - NSFR (Net Stable Funding Ratio)
     - Deposit concentration risk
     - Survival days under stress

  {Color.BOLD}3.{Color.RESET} Bank Run Simulation
     - Agent-based depositor modeling
     - SVB-style panic scenario
     - Social media contagion effects
     - Real-time visualization

  {Color.BOLD}4.{Color.RESET} Contagion Network Analysis
     - Interbank exposure modeling
     - Cascade simulation
     - Systemic importance ranking
     - 2023 Crisis recreation

  {Color.BOLD}5.{Color.RESET} Resolution Planning
     - Least-cost resolution analysis
     - Bridge bank scenarios
     - Systemic risk exception evaluation
     - Creditor waterfall

  {Color.BOLD}6.{Color.RESET} Full SVB Case Study
     - Complete analysis replicating 2023 failure

  {Color.BOLD}0.{Color.RESET} Exit

""")


def run_capital_analysis():
    """Run capital adequacy analysis"""
    ui = TerminalUI()
    clear_screen()

    print(f"\n{Color.YELLOW}Creating sample regional bank (similar to SVB profile)...{Color.RESET}\n")
    bank = create_sample_regional_bank("First Regional Bank")

    analyzer = CapitalAnalyzer(bank)
    report = analyzer.generate_capital_report()

    display_capital_report(ui, report)

    # Show stress test results
    ui.print_subheader("Stress Test Results")
    for scenario_name, results in report["stress_test_results"].items():
        status = "pass" if results["passes_stress_test"] else "fail"
        indicator = ui.status_indicator(status, scenario_name.replace("_", " ").title())
        print(f"  {indicator}")
        print(f"    Pre-stress CET1:  {format_percentage(report['capital_ratios']['cet1_ratio'])}")
        print(f"    Post-stress CET1: {format_percentage(results['stressed_cet1_ratio'])}")
        if results["capital_shortfall"] > 0:
            print(f"    {Color.RED}Shortfall: {format_currency(results['capital_shortfall'])}{Color.RESET}")
        print()

    # Interest rate sensitivity (the SVB killer)
    ui.print_subheader("Interest Rate Sensitivity (SVB's Achilles Heel)")
    print(f"  {Color.DIM}Impact of rate increases on capital (via AOCI):{Color.RESET}\n")

    for shock_name, impact in report["interest_rate_sensitivity"].items():
        print(f"  {shock_name}:")
        print(f"    MTM Impact:        {Color.RED}{format_currency(impact['total_mtm_impact'])}{Color.RESET}")
        print(f"    Post-shock CET1:   {format_percentage(impact['post_shock_cet1_ratio'])}")
        print()

    input(f"\n{Color.DIM}Press Enter to continue...{Color.RESET}")


def run_liquidity_analysis():
    """Run liquidity risk analysis"""
    ui = TerminalUI()
    clear_screen()

    print(f"\n{Color.YELLOW}Creating sample bank and analyzing liquidity risk...{Color.RESET}\n")
    bank = create_sample_regional_bank("First Regional Bank")

    analyzer = LiquidityAnalyzer(bank)
    report = analyzer.generate_liquidity_report()

    display_liquidity_report(ui, report)

    # Survival analysis
    ui.print_subheader("Survival Analysis Under Stress")
    for level, survival in report["survival_analysis"].items():
        days = survival["survival_days"]
        if days == ">90":
            color = Color.GREEN
        elif isinstance(days, int) and days > 30:
            color = Color.YELLOW
        else:
            color = Color.RED

        print(f"  {level.replace('_', ' ').title():15} Survival: {color}{days} days{Color.RESET}")

    input(f"\n{Color.DIM}Press Enter to continue...{Color.RESET}")


def run_bank_run_simulation():
    """Run bank run simulation with animation"""
    ui = TerminalUI()
    clear_screen()

    print(f"\n{Color.YELLOW}Setting up bank run simulation...{Color.RESET}")
    print(f"{Color.DIM}Modeling SVB-style capital raise announcement trigger...{Color.RESET}\n")

    bank = create_sample_regional_bank("Silicon Valley Regional Bank")

    # Make it more like SVB (higher uninsured ratio)
    for deposit in bank.deposits:
        if not deposit.is_insured:
            deposit.amount *= 1.5

    simulator = BankRunSimulator(bank)

    print("Press Enter to start simulation (Ctrl+C to skip animation)...")
    input()

    try:
        # Run animated simulation
        report = simulator.generate_run_report(
            trigger=RunTrigger.CAPITAL_RAISE_ANNOUNCEMENT,
            severity=0.7
        )
        animate_bank_run(ui, report["hourly_timeline"], delay=0.2)

    except KeyboardInterrupt:
        print(f"\n{Color.YELLOW}Animation skipped.{Color.RESET}")

    # Show summary
    print(f"\n{Color.CYAN}{'═' * 60}{Color.RESET}")
    print(f"{Color.BOLD}SIMULATION SUMMARY{Color.RESET}")

    report = simulator.generate_run_report(
        trigger=RunTrigger.CAPITAL_RAISE_ANNOUNCEMENT,
        severity=0.7
    )

    results = report["simulation_results"]
    print(f"\n  Trigger:              {report['trigger']}")
    print(f"  Duration:             {results['duration_hours']} hours")
    print(f"  Survived:             {Color.GREEN if results['survived'] else Color.RED}{results['survived']}{Color.RESET}")

    if results["failure_hour"]:
        print(f"  {Color.RED}Failure at hour:      {results['failure_hour']}{Color.RESET}")

    print(f"  Peak Hourly Outflow:  {format_currency(results['peak_outflow_amount'])}")
    print(f"  Total Deposit Flight: {format_currency(results['total_outflows'])}")
    print(f"  Final Peer Run Rate:  {format_percentage(results['final_peer_run_rate'])}")

    input(f"\n{Color.DIM}Press Enter to continue...{Color.RESET}")


def run_contagion_analysis():
    """Run systemic risk and contagion analysis"""
    ui = TerminalUI()
    clear_screen()

    print(f"\n{Color.YELLOW}Building bank network and analyzing systemic risk...{Color.RESET}\n")

    network = ContagionNetwork()
    network.generate_random_network(num_regional=6, num_gsib=3)

    analysis = network.analyze_systemic_risk()
    display_contagion_analysis(ui, analysis)

    # Run cascade simulation
    ui.print_subheader("Cascade Simulation: Regional Bank Failure")

    most_systemic = analysis["most_systemic_bank"]
    if most_systemic:
        print(f"\n  Simulating failure of: {Color.BOLD}{most_systemic}{Color.RESET}")

        cascade = network.simulate_cascade(most_systemic)

        print(f"\n  Initial Failure:    {cascade['initial_failure']}")
        print(f"  Total Failures:     {Color.RED}{cascade['num_failures']}{Color.RESET} / {cascade['total_banks']}")
        print(f"  Cascade Rounds:     {cascade['cascade_rounds']}")
        print(f"  System Assets Lost: {Color.RED}{format_percentage(cascade['pct_system_assets_failed'])}{Color.RESET}")

        print(f"\n  {Color.YELLOW}Failure Timeline:{Color.RESET}")
        for event in cascade["failure_timeline"][:10]:
            channel = event["channel"].replace("_", " ").title()
            print(f"    Round {event['round']}: {event['failed_bank']:<25} ({channel})")

    # 2023 crisis recreation
    ui.print_subheader("2023 Banking Crisis Recreation")
    print(f"\n  {Color.DIM}Modeling SVB → Signature → Regional contagion...{Color.RESET}\n")

    crisis = network.model_2023_crisis()
    print(f"  Initial Failure:    Silicon Valley Bank")
    print(f"  Total Failures:     {Color.RED}{crisis['num_failures']}{Color.RESET}")
    print(f"  System Impact:      {Color.RED}{format_percentage(crisis['pct_system_assets_failed'])}{Color.RESET}")

    print(f"\n  {Color.YELLOW}Cascade Sequence:{Color.RESET}")
    for event in crisis["failure_timeline"]:
        triggered = f" (triggered by {event.get('triggered_by', 'initial shock')})"
        print(f"    {event['failed_bank']}{triggered}")

    input(f"\n{Color.DIM}Press Enter to continue...{Color.RESET}")


def run_resolution_planning():
    """Run resolution planning analysis"""
    ui = TerminalUI()
    clear_screen()

    print(f"\n{Color.YELLOW}Analyzing resolution options...{Color.RESET}\n")

    bank = create_sample_regional_bank("First Regional Bank")
    planner = ResolutionPlanner(bank)

    plan = planner.generate_resolution_plan()
    display_resolution_plan(ui, plan)

    # Show timeline
    ui.print_subheader("Resolution Timeline")
    for milestone in plan["timeline"]:
        print(f"  Day {milestone['day']:3}: {milestone['action']}")

    input(f"\n{Color.DIM}Press Enter to continue...{Color.RESET}")


def run_svb_case_study():
    """Run comprehensive SVB-style case study"""
    ui = TerminalUI()
    clear_screen()

    ui.print_header("SVB CASE STUDY: ANATOMY OF A BANK FAILURE")

    print(f"""
{Color.DIM}On March 10, 2023, Silicon Valley Bank became the largest US bank failure
since Washington Mutual in 2008. This case study recreates the key factors:{Color.RESET}

  • High uninsured deposit concentration (94%)
  • Long-duration securities portfolio with unrealized losses
  • Concentrated depositor base (VC/tech ecosystem)
  • Rapid social media-driven bank run ($42B in one day)

{Color.YELLOW}Press Enter to begin analysis...{Color.RESET}
""")
    input()

    # Create SVB-like bank
    bank = create_sample_regional_bank("Silicon Valley Bank")
    bank.total_assets = 210_000_000_000  # $210B

    # Scale up to SVB size
    scale = 4.2
    for asset in bank.assets:
        asset.book_value *= scale
        asset.market_value *= scale
    for deposit in bank.deposits:
        deposit.amount *= scale
    bank.capital.common_stock *= scale
    bank.capital.retained_earnings *= scale

    # 1. Capital Analysis
    clear_screen()
    ui.print_header("PHASE 1: CAPITAL ADEQUACY UNDER RATE STRESS")

    print(f"{Color.DIM}SVB held long-duration securities that lost value as rates rose...{Color.RESET}\n")

    capital_analyzer = CapitalAnalyzer(bank)
    report = capital_analyzer.generate_capital_report()

    print(f"  Reported CET1 Ratio:      {Color.GREEN}{format_percentage(report['capital_ratios']['cet1_ratio'])}{Color.RESET}")
    print(f"  {Color.DIM}(With AOCI filter - hides unrealized losses){Color.RESET}\n")

    # Show what happens without AOCI filter
    aoci_impact = report["aoci_filter_impact"]
    print(f"  Unrealized Losses:        {Color.RED}{format_currency(aoci_impact['unrealized_gains_losses'])}{Color.RESET}")
    print(f"  True CET1 (no filter):    {Color.RED}{format_percentage(aoci_impact['adjusted_cet1_ratio'])}{Color.RESET}")
    print(f"\n  {Color.YELLOW}The AOCI filter masked $2.8B of hidden losses!{Color.RESET}")

    input(f"\n{Color.DIM}Press Enter for liquidity analysis...{Color.RESET}")

    # 2. Liquidity Analysis
    clear_screen()
    ui.print_header("PHASE 2: DEPOSIT CONCENTRATION RISK")

    liquidity_analyzer = LiquidityAnalyzer(bank)
    liquidity_report = liquidity_analyzer.generate_liquidity_report()

    deposits = liquidity_report["deposit_concentration"]
    print(f"  Total Deposits:      {format_currency(deposits['total_deposits'])}")
    print(f"  Uninsured Deposits:  {Color.RED}{format_currency(deposits['uninsured_deposits'])}{Color.RESET}")
    print(f"  Uninsured Ratio:     {Color.RED}{format_percentage(deposits['uninsured_ratio'])}{Color.RESET}")

    print(f"\n  {Color.YELLOW}94% of SVB's deposits were uninsured - a ticking time bomb.{Color.RESET}")
    print(f"  {Color.YELLOW}When confidence broke, depositors had every incentive to run.{Color.RESET}")

    # Survival analysis
    print(f"\n  {Color.CYAN}Survival Analysis Under Panic:{Color.RESET}")
    for level, survival in liquidity_report["survival_analysis"].items():
        if level == "extreme":
            print(f"    {level.title():15} {Color.RED}{survival['survival_days']} days{Color.RESET}")

    input(f"\n{Color.DIM}Press Enter for bank run simulation...{Color.RESET}")

    # 3. Bank Run
    clear_screen()
    ui.print_header("PHASE 3: THE RUN (MARCH 9-10, 2023)")

    print(f"""
{Color.DIM}Timeline of events:{Color.RESET}
  • March 8 (Wed PM): SVB announces capital raise + securities sale
  • March 9 (Thu):    $42 billion withdrawn in single day
  • March 10 (Fri AM): California DFPI closes bank, FDIC appointed

{Color.YELLOW}Simulating the run...{Color.RESET}
""")

    simulator = BankRunSimulator(bank)
    report = simulator.svb_scenario()

    # Quick summary instead of full animation
    print(f"  Hour  0: Deposits = {format_currency(report[0].remaining_deposits)}")
    for state in report:
        if state.hour in [6, 12, 18, 24, 30, 36]:
            remaining_pct = state.remaining_deposits / report[0].remaining_deposits
            bar_filled = int(remaining_pct * 30)
            bar = f"{'█' * bar_filled}{'░' * (30 - bar_filled)}"
            print(f"  Hour {state.hour:2}: [{bar}] {format_currency(state.remaining_deposits)}")

        if not state.bank_is_liquid:
            print(f"\n  {Color.BG_RED}{Color.WHITE} HOUR {state.hour}: LIQUIDITY EXHAUSTED {Color.RESET}")
            break

    input(f"\n{Color.DIM}Press Enter for resolution analysis...{Color.RESET}")

    # 4. Resolution
    clear_screen()
    ui.print_header("PHASE 4: RESOLUTION (FDIC TAKEOVER)")

    planner = ResolutionPlanner(bank)
    plan = planner.generate_resolution_plan()

    sre = plan["systemic_risk_exception"]
    print(f"  {Color.CYAN}Systemic Risk Exception Analysis:{Color.RESET}")
    print(f"  Factors Present: {sre['factors_present']}/5")

    for factor, present in sre["factors"].items():
        status = "pass" if present else "info"
        indicator = ui.status_indicator(status, factor.replace("_", " ").title())
        print(f"    {indicator}")

    print(f"\n  {Color.BG_RED}{Color.WHITE} SYSTEMIC RISK EXCEPTION INVOKED {Color.RESET}")
    print(f"  {Color.DIM}(As actually occurred on March 12, 2023){Color.RESET}")

    print(f"\n  Resolution Approach:")
    print(f"    1. Bridge bank established (Silicon Valley Bridge Bank)")
    print(f"    2. All depositors protected (insured AND uninsured)")
    print(f"    3. First Citizens acquires assets (March 26)")
    print(f"    4. Cost to DIF: ~$16 billion")

    input(f"\n{Color.DIM}Press Enter to see lessons learned...{Color.RESET}")

    # 5. Lessons Learned
    clear_screen()
    ui.print_header("LESSONS FROM SVB")

    print(f"""
{Color.CYAN}{Color.BOLD}Key Regulatory Takeaways:{Color.RESET}

  {Color.YELLOW}1. AOCI Filter Concerns{Color.RESET}
     Basel III Endgame proposes removing the AOCI filter for Category III/IV
     banks, which would have shown SVB's true capital position.

  {Color.YELLOW}2. Deposit Insurance Reform{Color.RESET}
     High uninsured deposit concentration creates inherent run risk.
     Options being discussed:
     • Unlimited transaction account coverage
     • Higher insurance limits
     • Risk-based deposit insurance premiums

  {Color.YELLOW}3. Interest Rate Risk Management{Color.RESET}
     Long-duration asset portfolios without hedging created massive
     unrealized losses that eventually forced liquidation.

  {Color.YELLOW}4. Speed of Modern Bank Runs{Color.RESET}
     Social media and mobile banking enabled $42B to flee in one day.
     Traditional liquidity frameworks may need updating.

  {Color.YELLOW}5. Regional Bank Supervision{Color.RESET}
     S.2155 (2018) reduced scrutiny of banks under $250B.
     SVB might have faced more oversight under prior rules.

{Color.DIM}These issues remain central to ongoing regulatory debates.{Color.RESET}
""")

    input(f"\n{Color.DIM}Press Enter to return to main menu...{Color.RESET}")


def main():
    """Main entry point"""
    while True:
        clear_screen()
        print_menu()

        try:
            choice = input(f"{Color.CYAN}Enter choice (0-6): {Color.RESET}").strip()

            if choice == "0":
                print(f"\n{Color.GREEN}Exiting. Thank you for using the Bank Stress Simulator.{Color.RESET}\n")
                sys.exit(0)
            elif choice == "1":
                run_capital_analysis()
            elif choice == "2":
                run_liquidity_analysis()
            elif choice == "3":
                run_bank_run_simulation()
            elif choice == "4":
                run_contagion_analysis()
            elif choice == "5":
                run_resolution_planning()
            elif choice == "6":
                run_svb_case_study()
            else:
                print(f"\n{Color.RED}Invalid choice. Please enter 0-6.{Color.RESET}")
                input("Press Enter to continue...")

        except KeyboardInterrupt:
            print(f"\n\n{Color.YELLOW}Interrupted. Returning to menu...{Color.RESET}")
            continue
        except Exception as e:
            print(f"\n{Color.RED}Error: {e}{Color.RESET}")
            input("Press Enter to continue...")


if __name__ == "__main__":
    main()
