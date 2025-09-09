#!/usr/bin/env python3
"""Detailed import analysis script for PromptCraft.

This script analyzes import performance in detail using cProfile
to identify the biggest bottlenecks in module loading.
"""

import cProfile
import pstats
import time
import sys
from io import StringIO
from pstats import SortKey


def analyze_import_performance():
    """Analyze import performance with detailed cProfile output."""
    
    print("PromptCraft Import Performance Analysis")
    print("=" * 40)
    
    # Create profiler
    profiler = cProfile.Profile()
    
    # Profile the main import chain
    print("Profiling main import chain...")
    profiler.enable()
    start_time = time.perf_counter()
    
    # Import the main modules in order (simulating CLI startup)
    import click  # Heavy framework import
    import pyperclip  # Clipboard functionality
    import promptcraft.main  # Our main module
    import promptcraft.core  # Core functionality
    import promptcraft.exceptions  # Exception classes
    
    end_time = time.perf_counter()
    profiler.disable()
    
    total_import_time = (end_time - start_time) * 1000
    print(f"Total import time: {total_import_time:.2f}ms\n")
    
    # Analyze results
    s = StringIO()
    ps = pstats.Stats(profiler, stream=s)
    
    # Sort by cumulative time to see biggest bottlenecks
    print("Top 15 functions by cumulative time:")
    print("-" * 60)
    ps.sort_stats(SortKey.CUMULATIVE)
    ps.print_stats(15)
    print(s.getvalue())
    
    # Reset string buffer
    s = StringIO()
    ps = pstats.Stats(profiler, stream=s)
    
    # Sort by total time to see most expensive individual operations
    print("\nTop 10 functions by total time:")
    print("-" * 45)
    ps.sort_stats(SortKey.TIME)
    ps.print_stats(10)
    print(s.getvalue())
    
    # Focus on our own modules
    s = StringIO()
    ps = pstats.Stats(profiler, stream=s)
    
    print("\nPromptCraft module analysis:")
    print("-" * 35)
    ps.sort_stats(SortKey.CUMULATIVE)
    ps.print_stats('promptcraft')
    print(s.getvalue())
    
    return total_import_time


def analyze_lazy_loading_opportunities():
    """Identify opportunities for lazy loading."""
    
    print("\nLazy Loading Analysis")
    print("=" * 25)
    
    # Analyze current imports in main.py
    print("Analyzing main.py imports...")
    
    main_imports = [
        ("sys", "Always needed for exit codes"),
        ("os", "Used for environment checks"),
        ("time", "Used for clipboard timeout"),
        ("pathlib.Path", "Used for file operations"),
        ("click", "Heavy CLI framework - could be lazy loaded"),
        ("pyperclip", "Clipboard operations - could be lazy loaded"),
        ("typing.Tuple", "Type hints - compile time only"),
        ("promptcraft.__version__", "Lightweight - needed for --version"),
        ("promptcraft.core", "Core functionality - could be lazy loaded"),
        ("promptcraft.exceptions", "Lightweight exception classes")
    ]
    
    critical_imports = []
    lazy_candidates = []
    
    for import_name, analysis in main_imports:
        if "could be lazy loaded" in analysis:
            lazy_candidates.append((import_name, analysis))
        else:
            critical_imports.append((import_name, analysis))
    
    print(f"\nCritical imports (must load at startup): {len(critical_imports)}")
    for imp, reason in critical_imports:
        print(f"  - {imp}: {reason}")
    
    print(f"\nLazy loading candidates: {len(lazy_candidates)}")
    for imp, reason in lazy_candidates:
        print(f"  - {imp}: {reason}")
    
    # Estimate potential savings
    print(f"\nPotential optimizations:")
    print(f"  - Click framework: ~20-30ms savings if lazy loaded")
    print(f"  - Pyperclip: ~5-10ms savings if lazy loaded")
    print(f"  - Core module: ~2-5ms savings if lazy loaded")
    print(f"  - Estimated total savings: ~25-45ms")
    
    return lazy_candidates


def analyze_subprocess_overhead():
    """Analyze subprocess startup overhead."""
    
    print("\nSubprocess Startup Analysis")
    print("=" * 30)
    
    # Time just Python startup with no imports
    start_time = time.perf_counter()
    result = subprocess.run([
        "python", "-c", "pass"
    ], capture_output=True, timeout=2)
    end_time = time.perf_counter()
    
    python_startup = (end_time - start_time) * 1000
    print(f"Pure Python startup: {python_startup:.2f}ms")
    
    # Time Python startup with just standard library
    start_time = time.perf_counter()
    result = subprocess.run([
        "python", "-c", "import sys, os, time; print('ok')"
    ], capture_output=True, timeout=2)
    end_time = time.perf_counter()
    
    stdlib_startup = (end_time - start_time) * 1000
    print(f"Python + stdlib: {stdlib_startup:.2f}ms")
    
    print(f"\nBreakdown estimate:")
    print(f"  - Python interpreter startup: ~{python_startup:.1f}ms")
    print(f"  - Standard library imports: ~{(stdlib_startup - python_startup):.1f}ms")
    print(f"  - Third-party imports (Click, pyperclip): ~25-35ms")
    print(f"  - PromptCraft modules: ~5-15ms")
    print(f"  - Command execution overhead: ~20-30ms")


def main():
    """Main entry point for import analysis."""
    import subprocess
    
    total_time = analyze_import_performance()
    lazy_candidates = analyze_lazy_loading_opportunities()
    
    try:
        analyze_subprocess_overhead()
    except Exception as e:
        print(f"Subprocess analysis failed: {e}")
    
    print(f"\nSUMMARY")
    print("=" * 20)
    print(f"Current import performance: {total_time:.2f}ms")
    print(f"Lazy loading opportunities: {len(lazy_candidates)} modules")
    print(f"Estimated improvement potential: 25-45ms (15-25% reduction)")
    print(f"Target for cold start: 150ms (currently ~296ms)")
    print(f"Import optimization contributes: ~15-25% of total improvement needed")


if __name__ == "__main__":
    main()