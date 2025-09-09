#!/usr/bin/env python3
"""Performance profiling script for cold start timing.

This script measures the cold start performance of PromptCraft CLI
by launching new Python processes and measuring execution time.
"""

import subprocess
import time
import statistics
import sys
from pathlib import Path
from typing import List, Dict, Any
import json
import argparse


def measure_cold_start(command_args: List[str], iterations: int = 10) -> Dict[str, Any]:
    """Measure cold start performance by launching new Python processes.
    
    Args:
        command_args: Command arguments to execute
        iterations: Number of iterations to run for statistical accuracy
        
    Returns:
        Dictionary with performance metrics
    """
    execution_times = []
    
    # Ensure we have a command to test with
    test_commands_dir = Path(".promptcraft/commands")
    if not test_commands_dir.exists():
        test_commands_dir.mkdir(parents=True, exist_ok=True)
        # Create a minimal test template for profiling
        test_template = test_commands_dir / "profile-test.md"
        test_template.write_text("# Profile Test\n\nThis is a test template with: $ARGUMENTS")
    
    for i in range(iterations):
        start_time = time.perf_counter()
        
        try:
            # Launch new Python process to measure true cold start
            result = subprocess.run(
                ["python", "-m", "promptcraft"] + command_args,
                capture_output=True,
                text=True,
                timeout=5.0,  # 5 second timeout
                cwd=Path.cwd()
            )
            
            end_time = time.perf_counter()
            execution_time_ms = (end_time - start_time) * 1000
            
            # Only count successful executions
            if result.returncode == 0:
                execution_times.append(execution_time_ms)
            else:
                print(f"Warning: Iteration {i+1} failed with code {result.returncode}")
                print(f"  stderr: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            print(f"Warning: Iteration {i+1} timed out")
        except Exception as e:
            print(f"Warning: Iteration {i+1} failed with error: {e}")
    
    if not execution_times:
        raise RuntimeError("All iterations failed - unable to measure performance")
    
    # Calculate statistics
    return {
        "command": " ".join(command_args),
        "iterations": len(execution_times),
        "mean_ms": statistics.mean(execution_times),
        "median_ms": statistics.median(execution_times),
        "min_ms": min(execution_times),
        "max_ms": max(execution_times),
        "stdev_ms": statistics.stdev(execution_times) if len(execution_times) > 1 else 0,
        "raw_times_ms": execution_times,
        "target_ms": 150.0,  # From acceptance criteria
        "passes_target": statistics.mean(execution_times) <= 150.0
    }


def profile_import_time() -> Dict[str, Any]:
    """Profile Python import time for PromptCraft modules.
    
    Returns:
        Dictionary with import timing metrics
    """
    import cProfile
    import pstats
    import io
    from pstats import SortKey
    
    # Create profiler
    profiler = cProfile.Profile()
    
    # Profile the import
    profiler.enable()
    start_time = time.perf_counter()
    
    # Import PromptCraft modules
    import promptcraft.main
    import promptcraft.core
    import promptcraft.exceptions
    
    end_time = time.perf_counter()
    profiler.disable()
    
    # Get profiling results
    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s).sort_stats(SortKey.CUMULATIVE)
    ps.print_stats(20)  # Top 20 functions
    
    return {
        "total_import_time_ms": (end_time - start_time) * 1000,
        "profile_output": s.getvalue()
    }


def main():
    """Main entry point for performance profiling."""
    parser = argparse.ArgumentParser(description="Profile PromptCraft cold start performance")
    parser.add_argument("--iterations", type=int, default=10, help="Number of iterations to run")
    parser.add_argument("--command", default="profile-test hello world", help="Command to profile")
    parser.add_argument("--output", help="Output file for JSON results")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    print("PromptCraft Cold Start Performance Profiler")
    print("=" * 45)
    
    # Parse command arguments
    command_args = args.command.split()
    
    # Measure cold start performance
    print(f"Measuring cold start performance with command: {args.command}")
    print(f"Running {args.iterations} iterations...")
    
    try:
        cold_start_results = measure_cold_start(command_args, args.iterations)
        
        print(f"\nCold Start Performance Results:")
        print(f"  Command: {cold_start_results['command']}")
        print(f"  Iterations: {cold_start_results['iterations']}")
        print(f"  Mean time: {cold_start_results['mean_ms']:.2f}ms")
        print(f"  Median time: {cold_start_results['median_ms']:.2f}ms")
        print(f"  Min time: {cold_start_results['min_ms']:.2f}ms")
        print(f"  Max time: {cold_start_results['max_ms']:.2f}ms")
        print(f"  Std deviation: {cold_start_results['stdev_ms']:.2f}ms")
        print(f"  Target (150ms): {'PASS' if cold_start_results['passes_target'] else 'FAIL'}")
        
    except Exception as e:
        print(f"Error measuring cold start performance: {e}")
        sys.exit(1)
    
    # Profile import time
    print(f"\nProfiling import performance...")
    
    try:
        import_results = profile_import_time()
        
        print(f"\nImport Performance Results:")
        print(f"  Total import time: {import_results['total_import_time_ms']:.2f}ms")
        
        if args.verbose:
            print(f"\nDetailed profiling output:")
            print(import_results['profile_output'])
            
    except Exception as e:
        print(f"Error profiling imports: {e}")
        import_results = {"total_import_time_ms": 0, "profile_output": ""}
    
    # Combine results
    combined_results = {
        "timestamp": time.time(),
        "cold_start": cold_start_results,
        "imports": import_results
    }
    
    # Save results if requested
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(combined_results, f, indent=2)
        print(f"\nResults saved to: {args.output}")
    
    # Exit with appropriate code
    if not cold_start_results['passes_target']:
        print(f"\nWarning: Cold start performance does not meet target of 150ms")
        sys.exit(1)
    else:
        print(f"\nSuccess: Cold start performance meets target!")


if __name__ == "__main__":
    main()