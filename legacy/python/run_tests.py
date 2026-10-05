#!/usr/bin/env python3
"""
Test execution script with comprehensive coverage reporting.

This script provides various options for running tests and generating coverage reports.
It's designed to be used both locally and in CI/CD environments.
"""

import sys
import subprocess
import argparse
from pathlib import Path


def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"\n{'='*60}")
    print(f"🔄 {description}")
    print(f"{'='*60}")
    print(f"Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=False)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed with exit code {e.returncode}")
        return False
    except FileNotFoundError:
        print(f"❌ Command not found: {cmd[0]}")
        print("Make sure you have installed the project dependencies:")
        print("pip install -e .[dev]")
        return False


def main():
    """Main test execution function."""
    parser = argparse.ArgumentParser(
        description="Run PromptCraft tests with coverage reporting",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_tests.py                    # Run all tests with coverage
  python run_tests.py --quick           # Run tests without coverage
  python run_tests.py --unit-only       # Run only unit tests
  python run_tests.py --integration     # Run only integration tests
  python run_tests.py --coverage-only   # Only generate coverage report
  python run_tests.py --html            # Generate HTML coverage report
  python run_tests.py --fail-under 90   # Set minimum coverage to 90%
        """
    )
    
    parser.add_argument(
        "--quick", 
        action="store_true", 
        help="Run tests quickly without coverage reporting"
    )
    parser.add_argument(
        "--unit-only", 
        action="store_true", 
        help="Run only unit tests"
    )
    parser.add_argument(
        "--integration", 
        action="store_true", 
        help="Run only integration tests"
    )
    parser.add_argument(
        "--coverage-only", 
        action="store_true", 
        help="Only generate coverage report from existing data"
    )
    parser.add_argument(
        "--html", 
        action="store_true", 
        help="Generate HTML coverage report"
    )
    parser.add_argument(
        "--xml", 
        action="store_true", 
        help="Generate XML coverage report"
    )
    parser.add_argument(
        "--fail-under", 
        type=int, 
        default=95, 
        help="Minimum coverage percentage required (default: 95)"
    )
    parser.add_argument(
        "--verbose", 
        action="store_true", 
        help="Run tests with verbose output"
    )
    parser.add_argument(
        "--markers", 
        help="Run tests matching specific markers (e.g., 'not slow')"
    )
    
    args = parser.parse_args()
    
    # Verify we're in the right directory
    if not Path("pyproject.toml").exists():
        print("❌ Error: pyproject.toml not found. Please run from project root.")
        sys.exit(1)
    
    success = True
    
    if args.coverage_only:
        # Only generate coverage reports
        print("📊 Generating coverage reports from existing data...")
        
        if args.html:
            success &= run_command(
                ["coverage", "html"], 
                "Generating HTML coverage report"
            )
        
        if args.xml:
            success &= run_command(
                ["coverage", "xml"], 
                "Generating XML coverage report"
            )
        
        success &= run_command(
            ["coverage", "report", f"--fail-under={args.fail_under}"], 
            f"Coverage report (minimum {args.fail_under}%)"
        )
    
    else:
        # Run tests
        pytest_cmd = ["python", "-m", "pytest"]
        
        if args.quick:
            # Quick mode - no coverage
            if args.verbose:
                pytest_cmd.append("-v")
            if args.markers:
                pytest_cmd.extend(["-m", args.markers])
        else:
            # Full mode with coverage
            pytest_cmd.extend([
                f"--cov=promptcraft",
                "--cov-report=term-missing",
                f"--cov-fail-under={args.fail_under}",
                "--cov-branch"
            ])
            
            if args.html or args.xml:
                if args.html:
                    pytest_cmd.append("--cov-report=html:htmlcov")
                if args.xml:
                    pytest_cmd.append("--cov-report=xml:coverage.xml")
            
            if args.verbose:
                pytest_cmd.append("-v")
            
            if args.markers:
                pytest_cmd.extend(["-m", args.markers])
        
        # Add test selection
        if args.unit_only:
            pytest_cmd.append("tests/unit/")
        elif args.integration:
            pytest_cmd.extend(["-m", "integration"])
        else:
            pytest_cmd.append("tests/")
        
        success = run_command(pytest_cmd, "Running tests")
    
    # Final summary
    print(f"\n{'='*60}")
    if success:
        print("🎉 All operations completed successfully!")
        
        # Show where reports were generated
        if not args.quick and not args.coverage_only:
            print("\n📊 Coverage reports generated:")
            if Path("htmlcov/index.html").exists():
                print(f"  📄 HTML: file://{Path('htmlcov/index.html').resolve()}")
            if Path("coverage.xml").exists():
                print(f"  📋 XML: {Path('coverage.xml').resolve()}")
        
        print(f"\n🧪 Test execution summary:")
        print(f"  ✅ Tests passed")
        if not args.quick:
            print(f"  📈 Coverage target: {args.fail_under}%")
        
    else:
        print("❌ Some operations failed!")
        print("\n🔍 Troubleshooting tips:")
        print("  • Make sure all dependencies are installed: pip install -e .[dev]")
        print("  • Check that you're running from the project root directory")
        print("  • Review the error messages above for specific issues")
        sys.exit(1)
    
    print(f"{'='*60}")


if __name__ == "__main__":
    main()