#!/usr/bin/env python3
"""
Neo Coordination Layer - Interactive Launcher
Run this after cloning to explore Neo's conflict detection.

Usage:
    python3 run.py
"""

import os
import sys
import subprocess
import webbrowser
import time
from pathlib import Path

# Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'


def print_header():
    """Print Neo welcome header."""
    print(f"\n{Colors.HEADER}{Colors.BOLD}")
    print("╔═════════════════════════════════════════════════════╗")
    print("║                                                     ║")
    print("║           🚀 Neo: Agent Coordination Layer 🚀       ║")
    print("║                                                     ║")
    print("║   Preventing conflicting work before agents collide ║")
    print("║                                                     ║")
    print("╚═════════════════════════════════════════════════════╝")
    print(f"{Colors.END}\n")


def print_menu():
    """Print interactive menu."""
    print(f"{Colors.CYAN}{Colors.BOLD}Choose an option:{Colors.END}\n")
    print(f"{Colors.GREEN}1{Colors.END} - View Interactive Dashboard (Browser)")
    print(f"{Colors.GREEN}2{Colors.END} - Run CLI Demo (All 5 Scenarios)")
    print(f"{Colors.GREEN}3{Colors.END} - Simulate 2 Agents (Choose Conflict Level)")
    print(f"{Colors.GREEN}4{Colors.END} - View Documentation")
    print(f"{Colors.GREEN}5{Colors.END} - Run Tests (if available)")
    print(f"{Colors.GREEN}6{Colors.END} - Exit")
    print(f"\n{Colors.YELLOW}Enter your choice (1-6):{Colors.END} ", end="")


def option_1_dashboard():
    """Open interactive dashboard in browser."""
    print(f"\n{Colors.BLUE}📊 Opening Interactive Dashboard...{Colors.END}")
    dashboard_path = Path("examples/neo_unified_dashboard.html")

    if not dashboard_path.exists():
        print(f"{Colors.RED}❌ Dashboard not found at {dashboard_path}{Colors.END}")
        print(f"{Colors.YELLOW}Trying alternate locations...{Colors.END}")
        dashboard_path = Path("ui_dashboard.html")
        if not dashboard_path.exists():
            print(f"{Colors.RED}❌ No dashboard found{Colors.END}")
            return

    abs_path = dashboard_path.resolve()
    file_url = f"file://{abs_path}"

    print(f"{Colors.GREEN}✓ Launching browser...{Colors.END}")
    print(f"{Colors.CYAN}Dashboard: {file_url}{Colors.END}\n")

    try:
        webbrowser.open(file_url)
        print(f"{Colors.GREEN}✓ Dashboard opened in browser{Colors.END}")
        print(f"{Colors.YELLOW}Try these scenarios:{Colors.END}")
        print("  • Click scenario buttons to simulate agent interactions")
        print("  • Watch conflict detection in real-time")
        print("  • See risk scoring and enforcement gates in action")
    except Exception as e:
        print(f"{Colors.RED}Could not open browser: {e}{Colors.END}")
        print(f"{Colors.YELLOW}Open manually: {file_url}{Colors.END}")

    time.sleep(1)


def option_2_cli_demo():
    """Run CLI simulation with all scenarios."""
    print(f"\n{Colors.BLUE}🎬 Running CLI Demo (All 5 Scenarios)...{Colors.END}\n")

    cli_path = Path("cli_simulation.py")
    if not cli_path.exists():
        print(f"{Colors.RED}❌ cli_simulation.py not found{Colors.END}")
        return

    try:
        subprocess.run([sys.executable, str(cli_path)], check=True)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Demo interrupted by user{Colors.END}")
    except Exception as e:
        print(f"{Colors.RED}Error running demo: {e}{Colors.END}")


def option_3_multi_agent():
    """Simulate 2 agents with chosen conflict level."""
    print(f"\n{Colors.BLUE}👥 Multi-Agent Simulation{Colors.END}")
    print(f"{Colors.CYAN}Choose conflict level:{Colors.END}\n")
    print(f"{Colors.GREEN}1{Colors.END} - LOW (non-overlapping regions)")
    print(f"{Colors.GREEN}2{Colors.END} - MEDIUM (overlapping regions)")
    print(f"{Colors.GREEN}3{Colors.END} - HIGH (signature changes)")
    print(f"\n{Colors.YELLOW}Enter choice (1-3):{Colors.END} ", end="")

    try:
        choice = input().strip()

        scenarios = {
            "1": ("LOW", "Scenario 2: Non-Overlapping Regions"),
            "2": ("MEDIUM", "Scenario 1: Overlapping Regions"),
            "3": ("HIGH", "Scenario 3: Signature Change"),
        }

        if choice not in scenarios:
            print(f"{Colors.RED}Invalid choice{Colors.END}")
            return

        level, desc = scenarios[choice]
        print(f"\n{Colors.BLUE}Running {level} conflict scenario...{Colors.END}")
        print(f"{Colors.CYAN}{desc}{Colors.END}\n")

        cli_path = Path("cli_simulation.py")
        if not cli_path.exists():
            print(f"{Colors.RED}cli_simulation.py not found{Colors.END}")
            return

        subprocess.run([sys.executable, str(cli_path)], check=True)

    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Simulation interrupted{Colors.END}")
    except Exception as e:
        print(f"{Colors.RED}Error: {e}{Colors.END}")


def option_4_docs():
    """Open documentation."""
    print(f"\n{Colors.BLUE}📚 Neo Documentation{Colors.END}\n")

    docs = [
        ("README.md", "Main overview and quick start"),
        ("docs/01-ARCHITECTURE.md", "How Neo works internally"),
        ("docs/IMPLEMENTATION.md", "Integration guide for agents"),
        ("QUICKSTART.md", "Quick reference + code examples"),
        ("POC_REPORT.md", "Detailed findings and verdict"),
    ]

    print(f"{Colors.CYAN}Available documentation:{Colors.END}\n")
    for i, (path, desc) in enumerate(docs, 1):
        print(f"{Colors.GREEN}{i}{Colors.END} - {path}")
        print(f"   {desc}\n")

    print(f"{Colors.YELLOW}View documentation in your editor or run:{Colors.END}")
    print(f"  cat README.md")
    print(f"  cat QUICKSTART.md")
    print(f"  cat POC_REPORT.md\n")


def option_5_tests():
    """Run test suite if available."""
    print(f"\n{Colors.BLUE}🧪 Running Tests{Colors.END}\n")

    # Check for pytest
    try:
        subprocess.run([sys.executable, "-m", "pytest", "--version"],
                      capture_output=True, check=True)
    except:
        print(f"{Colors.RED}pytest not installed{Colors.END}")
        print(f"{Colors.YELLOW}Install with: pip install -r requirements.txt{Colors.END}\n")
        return

    # Look for tests directory
    tests_path = Path("tests")
    if not tests_path.exists():
        print(f"{Colors.YELLOW}No tests/ directory found yet{Colors.END}")
        print(f"{Colors.CYAN}Test suite coming soon!{Colors.END}\n")
        return

    print(f"{Colors.GREEN}Running pytest...{Colors.END}\n")
    try:
        subprocess.run([sys.executable, "-m", "pytest", "tests/", "-v"], check=False)
    except Exception as e:
        print(f"{Colors.RED}Error running tests: {e}{Colors.END}")


def option_6_exit():
    """Exit gracefully."""
    print(f"\n{Colors.GREEN}✓ Thanks for exploring Neo!{Colors.END}")
    print(f"{Colors.CYAN}Next steps:{Colors.END}")
    print("  1. Read QUICKSTART.md for integration examples")
    print("  2. Explore the examples/ folder")
    print("  3. Check GitHub: https://github.com/jaykrishna316/Neo")
    print(f"\n{Colors.YELLOW}Happy coordinating! 🚀{Colors.END}\n")
    sys.exit(0)


def main():
    """Main launcher loop."""
    print_header()

    options = {
        "1": ("Dashboard", option_1_dashboard),
        "2": ("CLI Demo", option_2_cli_demo),
        "3": ("Multi-Agent", option_3_multi_agent),
        "4": ("Docs", option_4_docs),
        "5": ("Tests", option_5_tests),
        "6": ("Exit", option_6_exit),
    }

    while True:
        print_menu()

        try:
            choice = input().strip()

            if choice not in options:
                print(f"{Colors.RED}Invalid choice. Please enter 1-6.{Colors.END}\n")
                continue

            name, func = options[choice]
            func()

            if choice != "6":
                print(f"\n{Colors.YELLOW}Press Enter to return to menu...{Colors.END}")
                input()
                print("\n" + "="*60 + "\n")

        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}Interrupted by user{Colors.END}")
            option_6_exit()
        except Exception as e:
            print(f"{Colors.RED}Error: {e}{Colors.END}\n")


if __name__ == "__main__":
    main()
