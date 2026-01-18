"""
Terminal Visualization for Bank Stress Testing

Creates rich terminal-based visualizations including:
- ASCII bar charts and gauges
- Real-time stress test animations
- Network graphs (simplified)
- Color-coded regulatory status indicators

Uses ANSI escape codes for colors and formatting.
"""

import sys
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class Color:
    """ANSI color codes"""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    UNDERLINE = "\033[4m"

    # Foreground colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # Bright foreground
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"

    # Background colors
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"


def clear_screen():
    """Clear terminal screen"""
    print("\033[2J\033[H", end="")


def move_cursor(row: int, col: int):
    """Move cursor to position"""
    print(f"\033[{row};{col}H", end="")


def format_currency(amount: float) -> str:
    """Format number as currency"""
    if abs(amount) >= 1_000_000_000:
        return f"${amount / 1_000_000_000:.1f}B"
    elif abs(amount) >= 1_000_000:
        return f"${amount / 1_000_000:.1f}M"
    elif abs(amount) >= 1_000:
        return f"${amount / 1_000:.1f}K"
    else:
        return f"${amount:.0f}"


def format_percentage(value: float) -> str:
    """Format as percentage"""
    return f"{value * 100:.2f}%"


class TerminalUI:
    """Main terminal UI class"""

    def __init__(self, width: int = 100):
        self.width = width

    def print_header(self, title: str):
        """Print a styled header"""
        border = "═" * self.width
        print(f"\n{Color.CYAN}{Color.BOLD}╔{border}╗{Color.RESET}")
        padding = (self.width - len(title)) // 2
        print(f"{Color.CYAN}{Color.BOLD}║{' ' * padding}{title}{' ' * (self.width - padding - len(title))}║{Color.RESET}")
        print(f"{Color.CYAN}{Color.BOLD}╚{border}╝{Color.RESET}\n")

    def print_subheader(self, title: str):
        """Print a styled subheader"""
        print(f"\n{Color.YELLOW}{Color.BOLD}▌ {title}{Color.RESET}")
        print(f"{Color.DIM}{'─' * (self.width - 2)}{Color.RESET}")

    def print_box(self, content: List[str], title: Optional[str] = None):
        """Print content in a box"""
        max_len = max(len(line) for line in content) if content else 0
        box_width = min(max_len + 4, self.width)

        if title:
            print(f"┌─ {title} {'─' * (box_width - len(title) - 5)}┐")
        else:
            print(f"┌{'─' * box_width}┐")

        for line in content:
            padding = box_width - len(line) - 2
            print(f"│ {line}{' ' * padding}│")

        print(f"└{'─' * box_width}┘")

    def progress_bar(
        self,
        value: float,
        max_value: float,
        width: int = 40,
        label: str = "",
        thresholds: Optional[Dict[float, str]] = None
    ) -> str:
        """Create a progress bar with optional color thresholds"""
        ratio = min(1.0, max(0.0, value / max_value if max_value > 0 else 0))
        filled = int(width * ratio)
        empty = width - filled

        # Determine color based on thresholds
        color = Color.GREEN
        if thresholds:
            for threshold, threshold_color in sorted(thresholds.items()):
                if ratio <= threshold:
                    color = threshold_color
                    break

        bar = f"{color}{'█' * filled}{Color.DIM}{'░' * empty}{Color.RESET}"

        if label:
            return f"{label}: [{bar}] {format_percentage(ratio)}"
        return f"[{bar}] {format_percentage(ratio)}"

    def gauge(
        self,
        value: float,
        min_val: float,
        max_val: float,
        target: Optional[float] = None,
        label: str = "",
        width: int = 50
    ) -> str:
        """Create a gauge visualization"""
        range_val = max_val - min_val
        if range_val == 0:
            position = 0
        else:
            position = int((value - min_val) / range_val * width)
            position = max(0, min(width, position))

        # Create the gauge line
        line = list("─" * width)

        # Add target marker
        if target is not None:
            target_pos = int((target - min_val) / range_val * width)
            target_pos = max(0, min(width - 1, target_pos))
            line[target_pos] = "│"

        # Determine color based on position relative to target
        if target is not None and value >= target:
            indicator_color = Color.GREEN
        elif target is not None and value >= target * 0.9:
            indicator_color = Color.YELLOW
        else:
            indicator_color = Color.RED

        # Convert to string and add position indicator
        gauge_str = "".join(line)
        before = gauge_str[:position]
        after = gauge_str[position + 1:] if position < width else ""

        result = f"{before}{indicator_color}●{Color.RESET}{after}"

        if label:
            return f"{label}: [{result}] {format_percentage(value)}"
        return f"[{result}] {format_percentage(value)}"

    def table(
        self,
        headers: List[str],
        rows: List[List[str]],
        column_widths: Optional[List[int]] = None
    ):
        """Print a formatted table"""
        if not column_widths:
            column_widths = [max(len(str(row[i])) for row in [headers] + rows) + 2
                            for i in range(len(headers))]

        # Header
        header_str = "│".join(
            f" {h:<{column_widths[i] - 1}}"
            for i, h in enumerate(headers)
        )
        separator = "┼".join("─" * w for w in column_widths)

        print(f"{Color.BOLD}{header_str}{Color.RESET}")
        print(separator)

        # Rows
        for row in rows:
            row_str = "│".join(
                f" {str(cell):<{column_widths[i] - 1}}"
                for i, cell in enumerate(row)
            )
            print(row_str)

    def status_indicator(self, status: str, label: str) -> str:
        """Create a colored status indicator"""
        status_colors = {
            "pass": (Color.GREEN, "✓"),
            "fail": (Color.RED, "✗"),
            "warning": (Color.YELLOW, "⚠"),
            "info": (Color.BLUE, "ℹ"),
            "critical": (Color.BG_RED + Color.WHITE, "!"),
        }

        color, symbol = status_colors.get(status.lower(), (Color.WHITE, "?"))
        return f"{color}{symbol}{Color.RESET} {label}"

    def spark_line(self, values: List[float], width: int = 30) -> str:
        """Create a sparkline visualization"""
        if not values:
            return ""

        min_val = min(values)
        max_val = max(values)
        range_val = max_val - min_val if max_val != min_val else 1

        # Sparkline characters (8 levels)
        chars = "▁▂▃▄▅▆▇█"

        # Sample values to fit width
        if len(values) > width:
            step = len(values) / width
            sampled = [values[int(i * step)] for i in range(width)]
        else:
            sampled = values

        result = ""
        for v in sampled:
            level = int((v - min_val) / range_val * 7)
            level = max(0, min(7, level))
            result += chars[level]

        return result

    def network_ascii(
        self,
        nodes: List[str],
        edges: List[Tuple[str, str]],
        failed_nodes: Optional[List[str]] = None
    ) -> List[str]:
        """Create a simple ASCII network visualization"""
        failed_nodes = failed_nodes or []
        lines = []

        # Simple circular layout
        num_nodes = len(nodes)
        if num_nodes == 0:
            return ["(empty network)"]

        # Create node positions
        positions = {}
        radius = min(15, num_nodes * 2)

        import math
        for i, node in enumerate(nodes):
            angle = 2 * math.pi * i / num_nodes
            x = int(radius * math.cos(angle)) + radius + 2
            y = int(radius * 0.5 * math.sin(angle)) + radius // 2 + 2
            positions[node] = (x, y)

        # Create canvas
        height = radius + 4
        width = radius * 2 + 4
        canvas = [[" " for _ in range(width)] for _ in range(height)]

        # Draw edges (simplified - just show connections)
        for from_node, to_node in edges:
            if from_node in positions and to_node in positions:
                x1, y1 = positions[from_node]
                x2, y2 = positions[to_node]
                # Draw a simple line indicator
                mx, my = (x1 + x2) // 2, (y1 + y2) // 2
                if 0 <= my < height and 0 <= mx < width:
                    canvas[my][mx] = "·"

        # Draw nodes
        for node in nodes:
            if node in positions:
                x, y = positions[node]
                if 0 <= y < height and 0 <= x < width:
                    if node in failed_nodes:
                        symbol = "✗"
                    else:
                        symbol = "○"
                    canvas[y][x] = symbol

        # Convert canvas to lines
        for row in canvas:
            lines.append("".join(row))

        # Add legend
        lines.append("")
        lines.append(f"  ○ Active   {Color.RED}✗ Failed{Color.RESET}")

        return lines


def animate_bank_run(
    ui: TerminalUI,
    timeline: List[Dict],
    delay: float = 0.3
):
    """Animate a bank run simulation"""
    clear_screen()
    ui.print_header("BANK RUN SIMULATION")

    print(f"\n{Color.YELLOW}Simulating deposit flight...{Color.RESET}\n")

    max_deposits = timeline[0]["remaining_deposits"] if timeline else 0
    max_outflow = max(t["outflows"] for t in timeline) if timeline else 0

    for state in timeline:
        # Clear previous content
        move_cursor(5, 0)

        # Time
        print(f"Hour: {Color.BOLD}{state['hour']:3d}{Color.RESET}")
        print()

        # Remaining deposits
        deposits_pct = state["remaining_deposits"] / max_deposits if max_deposits > 0 else 0
        bar = ui.progress_bar(
            deposits_pct, 1.0,
            width=50,
            label="Deposits Remaining",
            thresholds={0.3: Color.RED, 0.5: Color.YELLOW, 1.0: Color.GREEN}
        )
        print(f"  {bar} ({format_currency(state['remaining_deposits'])})")

        # Hourly outflows
        print()
        outflow_bar = ui.progress_bar(
            state["outflows"], max_outflow,
            width=50,
            label="Hourly Outflows    ",
            thresholds={0.5: Color.YELLOW, 0.8: Color.RED, 1.0: Color.BRIGHT_RED}
        )
        print(f"  {outflow_bar} ({format_currency(state['outflows'])})")

        # Liquidity
        print()
        if state["bank_is_liquid"]:
            liq_status = ui.status_indicator("pass", f"Liquidity: {format_currency(state['liquidity'])}")
        else:
            liq_status = ui.status_indicator("critical", f"LIQUIDITY EXHAUSTED")
        print(f"  {liq_status}")

        # Peer run rate
        print()
        peer_bar = ui.progress_bar(
            state["peer_run_rate"], 1.0,
            width=30,
            label="Depositors Who Ran",
            thresholds={0.3: Color.YELLOW, 0.5: Color.RED, 1.0: Color.BRIGHT_RED}
        )
        print(f"  {peer_bar}")

        # Check for failure
        if not state["bank_is_liquid"]:
            print(f"\n{Color.BG_RED}{Color.WHITE}{Color.BOLD}  BANK FAILURE - LIQUIDITY EXHAUSTED  {Color.RESET}")
            break

        time.sleep(delay)
        sys.stdout.flush()


def display_capital_report(ui: TerminalUI, report: Dict):
    """Display capital adequacy report"""
    ui.print_header("CAPITAL ADEQUACY REPORT")
    print(f"Bank: {Color.BOLD}{report['bank_name']}{Color.RESET}")
    print(f"Total Assets: {format_currency(report['total_assets'])}")

    ui.print_subheader("Capital Structure")
    structure = report["capital_structure"]
    ui.table(
        headers=["Component", "Amount", "% of Total"],
        rows=[
            ["CET1 Capital", format_currency(structure["cet1"]),
             format_percentage(structure["cet1"] / structure["total_capital"])],
            ["Additional Tier 1", format_currency(structure["at1"]),
             format_percentage(structure["at1"] / structure["total_capital"])],
            ["Tier 1 Capital", format_currency(structure["tier1"]),
             format_percentage(structure["tier1"] / structure["total_capital"])],
            ["Tier 2 Capital", format_currency(structure["tier2"]),
             format_percentage(structure["tier2"] / structure["total_capital"])],
            ["Total Capital", format_currency(structure["total_capital"]), "100.00%"],
        ]
    )

    ui.print_subheader("Capital Ratios vs Requirements")
    ratios = report["capital_ratios"]
    reqs = report["requirements"]

    for ratio_name, ratio_val, req_val in [
        ("CET1 Ratio", ratios["cet1_ratio"], reqs["cet1"]),
        ("Tier 1 Ratio", ratios["tier1_ratio"], reqs["tier1"]),
        ("Total Capital", ratios["total_capital_ratio"], reqs["total"]),
        ("Leverage Ratio", ratios["leverage_ratio"], reqs["leverage"]),
    ]:
        gauge = ui.gauge(
            ratio_val, 0, 0.20,
            target=req_val,
            label=f"{ratio_name:20}",
            width=40
        )
        status = "pass" if ratio_val >= req_val else "fail"
        print(f"  {gauge} {ui.status_indicator(status, '')}")

    ui.print_subheader("Regulatory Status")
    status = report["regulatory_status"]
    category = status["pca_category"].replace("_", " ").title()

    if "well" in status["pca_category"]:
        color = Color.GREEN
    elif "adequately" in status["pca_category"]:
        color = Color.YELLOW
    else:
        color = Color.RED

    print(f"  PCA Category: {color}{Color.BOLD}{category}{Color.RESET}")
    print(f"  {Color.DIM}{status['description']}{Color.RESET}")

    if status["enforcement_actions"]:
        print(f"\n  {Color.YELLOW}Enforcement Actions:{Color.RESET}")
        for action in status["enforcement_actions"]:
            print(f"    • {action}")


def display_liquidity_report(ui: TerminalUI, report: Dict):
    """Display liquidity risk report"""
    ui.print_header("LIQUIDITY RISK REPORT")

    ui.print_subheader("HQLA Composition")
    hqla = report["hqla_composition"]
    ui.table(
        headers=["Level", "Amount", "After Haircuts"],
        rows=[
            ["Level 1 (No haircut)", format_currency(hqla["level_1_unadjusted"]),
             format_currency(hqla["level_1_unadjusted"])],
            ["Level 2A (15% haircut)", format_currency(hqla["level_2a_after_haircut"] / 0.85),
             format_currency(hqla["level_2a_after_haircut"])],
            ["Level 2B (50% haircut)", format_currency(hqla["level_2b_after_haircut"] / 0.50),
             format_currency(hqla["level_2b_after_haircut"])],
            ["Total HQLA", "", format_currency(hqla["total_hqla"])],
        ]
    )

    ui.print_subheader("Liquidity Coverage Ratio (LCR)")
    lcr = report["liquidity_coverage_ratio"]
    print(f"  HQLA:           {format_currency(lcr['hqla'])}")
    print(f"  Gross Outflows: {format_currency(lcr['gross_outflows'])}")
    print(f"  Capped Inflows: {format_currency(lcr['capped_inflows'])}")
    print(f"  Net Outflows:   {format_currency(lcr['net_outflows'])}")
    print()
    lcr_gauge = ui.gauge(
        lcr["lcr_ratio"], 0, 2.0,
        target=1.0,
        label="LCR Ratio",
        width=50
    )
    status = "pass" if lcr["meets_requirement"] else "fail"
    print(f"  {lcr_gauge} {ui.status_indicator(status, '')}")

    ui.print_subheader("Deposit Concentration Risk")
    deposits = report["deposit_concentration"]
    print(f"  Total Deposits:     {format_currency(deposits['total_deposits'])}")
    print(f"  Insured Deposits:   {format_currency(deposits['insured_deposits'])} ({format_percentage(deposits['insured_ratio'])})")
    print(f"  Uninsured Deposits: {format_currency(deposits['uninsured_deposits'])} ({format_percentage(deposits['uninsured_ratio'])})")

    risk = deposits["risk_assessment"]
    risk_colors = {
        "critical": Color.BRIGHT_RED,
        "high": Color.RED,
        "moderate": Color.YELLOW,
        "low": Color.GREEN,
    }
    risk_color = risk_colors.get(risk["risk_level"], Color.WHITE)
    print(f"\n  Risk Level: {risk_color}{Color.BOLD}{risk['risk_level'].upper()}{Color.RESET}")
    print(f"  {Color.DIM}{risk['description']}{Color.RESET}")


def display_resolution_plan(ui: TerminalUI, plan: Dict):
    """Display resolution planning report"""
    ui.print_header("RESOLUTION PLANNING ANALYSIS")

    summary = plan["resolution_summary"]
    print(f"Bank: {Color.BOLD}{plan['bank_name']}{Color.RESET}")
    print(f"Total Assets:      {format_currency(summary['total_assets'])}")
    print(f"Total Deposits:    {format_currency(summary['total_deposits'])}")
    print(f"Uninsured Ratio:   {Color.YELLOW}{format_percentage(summary['uninsured_ratio'])}{Color.RESET}")

    ui.print_subheader("Systemic Risk Exception Analysis")
    sre = plan["systemic_risk_exception"]

    print("  Factors Evaluated:")
    for factor, present in sre["factors"].items():
        indicator = ui.status_indicator("pass" if present else "info", factor.replace("_", " ").title())
        print(f"    {indicator}")

    if sre["sre_recommended"]:
        print(f"\n  {Color.BG_RED}{Color.WHITE} SRE RECOMMENDED {Color.RESET}")
        print(f"  {Color.DIM}Requires approval from:{Color.RESET}")
        for approver in sre["approval_required"]:
            print(f"    • {approver}")
    else:
        print(f"\n  {Color.GREEN}Standard least-cost resolution applies{Color.RESET}")

    ui.print_subheader("Resolution Options Comparison")
    options = plan["least_cost_analysis"]["options"]

    rows = []
    for option_name, costs in options.items():
        rows.append([
            option_name.replace("_", " ").title(),
            format_currency(costs["cost_to_dif"]),
            format_currency(costs["asset_losses"]),
            format_currency(costs.get("loss_share_commitment", 0)),
        ])

    ui.table(
        headers=["Option", "Cost to DIF", "Asset Losses", "Loss Share"],
        rows=rows
    )

    ui.print_subheader("Recommended Approach")
    rec = plan["recommended_approach"]
    print(f"  Method: {Color.BOLD}{rec['method'].replace('_', ' ').title()}{Color.RESET}")
    print(f"  Rationale: {rec['rationale']}")
    print(f"  Depositor Treatment: {rec['depositor_treatment']}")
    print(f"  Estimated Cost: {Color.YELLOW}{format_currency(rec['estimated_cost'])}{Color.RESET}")


def display_contagion_analysis(ui: TerminalUI, analysis: Dict):
    """Display systemic risk and contagion analysis"""
    ui.print_header("SYSTEMIC RISK & CONTAGION ANALYSIS")

    stats = analysis["network_stats"]
    print(f"Network Size: {stats['total_banks']} banks")
    print(f"Total Exposures: {stats['total_exposures']}")
    print(f"Avg Interconnection: {stats['avg_interconnection']:.1f}")

    ui.print_subheader("Systemic Importance Ranking")
    for i, bank_data in enumerate(analysis["systemic_importance_ranking"][:5]):
        bar = ui.progress_bar(
            bank_data["pct_system_affected"],
            1.0,
            width=30,
            thresholds={0.1: Color.GREEN, 0.3: Color.YELLOW, 1.0: Color.RED}
        )
        sifi = "SIFI" if bank_data["is_systemically_important"] else ""
        print(f"  {i + 1}. {bank_data['bank']:25} {bar} {Color.RED}{sifi}{Color.RESET}")

    if analysis["most_systemic_bank"]:
        print(f"\n  Most Systemic Institution: {Color.BOLD}{analysis['most_systemic_bank']}{Color.RESET}")
