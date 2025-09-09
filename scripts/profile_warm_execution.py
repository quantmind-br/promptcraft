#!/usr/bin/env python3
"""Performance profiling script for warm execution timing.

This script measures warm execution performance by keeping PromptCraft
modules loaded in memory and measuring subsequent command executions.
"""

import time
import statistics
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Any
import json
import tracemalloc


def measure_warm_execution(command_name: str, arguments: List[str], iterations: int = 10) -> Dict[str, Any]:
    """Measure warm execution performance with modules already loaded.
    
    Args:
        command_name: Command name to execute
        arguments: Command arguments
        iterations: Number of iterations for statistical accuracy
        
    Returns:
        Dictionary with performance metrics
    """
    # Import modules once (simulating warm state)
    from promptcraft.core import process_command
    from promptcraft.exceptions import CommandNotFoundError, TemplateReadError
    
    # Ensure test template exists
    test_commands_dir = Path(".promptcraft/commands")
    if not test_commands_dir.exists():
        test_commands_dir.mkdir(parents=True, exist_ok=True)
        
    test_template = test_commands_dir / f"{command_name}.md"
    if not test_template.exists():
        test_template.write_text(f"# {command_name.title()} Test\n\nThis is a warm execution test with: $ARGUMENTS")
    
    execution_times = []
    memory_usage = []
    
    for i in range(iterations):
        # Start memory tracking
        tracemalloc.start()
        
        start_time = time.perf_counter()
        
        try:
            # Execute command (warm execution)
            result = process_command(command_name, arguments)
            
            end_time = time.perf_counter()
            execution_time_ms = (end_time - start_time) * 1000
            
            # Get memory usage
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            
            execution_times.append(execution_time_ms)
            memory_usage.append({
                "current_bytes": current,
                "peak_bytes": peak
            })
            
        except (CommandNotFoundError, TemplateReadError) as e:
            tracemalloc.stop()
            print(f"Warning: Iteration {i+1} failed with error: {e}")
        except Exception as e:
            tracemalloc.stop()
            print(f"Warning: Iteration {i+1} failed with unexpected error: {e}")
    
    if not execution_times:
        raise RuntimeError("All iterations failed - unable to measure warm execution performance")
    
    # Calculate statistics
    avg_current_memory = statistics.mean(m["current_bytes"] for m in memory_usage)
    avg_peak_memory = statistics.mean(m["peak_bytes"] for m in memory_usage)
    
    return {
        "command": command_name,
        "arguments": arguments,
        "iterations": len(execution_times),
        "mean_ms": statistics.mean(execution_times),
        "median_ms": statistics.median(execution_times),
        "min_ms": min(execution_times),
        "max_ms": max(execution_times),
        "stdev_ms": statistics.stdev(execution_times) if len(execution_times) > 1 else 0,
        "raw_times_ms": execution_times,
        "memory_current_avg_bytes": avg_current_memory,
        "memory_peak_avg_bytes": avg_peak_memory,
        "memory_current_avg_mb": avg_current_memory / (1024 * 1024),
        "memory_peak_avg_mb": avg_peak_memory / (1024 * 1024),
        "target_ms": 100.0,  # From acceptance criteria
        "passes_target": statistics.mean(execution_times) <= 100.0
    }


def measure_filesystem_operations(iterations: int = 20) -> Dict[str, Any]:
    """Measure file system operation performance.
    
    Args:
        iterations: Number of iterations for statistical accuracy
        
    Returns:
        Dictionary with file system performance metrics
    """
    from promptcraft.core import find_command_path, discover_commands
    
    # Create test templates for consistent measurements
    test_commands_dir = Path(".promptcraft/commands")
    test_commands_dir.mkdir(parents=True, exist_ok=True)
    
    # Create multiple test templates to simulate realistic scenarios
    test_templates = []
    for i in range(5):
        template_name = f"perf-test-{i}"
        template_path = test_commands_dir / f"{template_name}.md"
        if not template_path.exists():
            template_path.write_text(f"# Performance Test {i}\n\nTest template {i} with: $ARGUMENTS")
        test_templates.append(template_name)
    
    results = {}
    
    # Measure find_command_path performance
    find_times = []
    for i in range(iterations):
        start_time = time.perf_counter()
        
        try:
            # Test finding existing command
            find_command_path(test_templates[i % len(test_templates)])
            end_time = time.perf_counter()
            find_times.append((end_time - start_time) * 1000)
        except Exception as e:
            print(f"Warning: find_command_path iteration {i+1} failed: {e}")
    
    if find_times:
        results["find_command"] = {
            "mean_ms": statistics.mean(find_times),
            "median_ms": statistics.median(find_times),
            "min_ms": min(find_times),
            "max_ms": max(find_times),
            "stdev_ms": statistics.stdev(find_times) if len(find_times) > 1 else 0
        }
    
    # Measure discover_commands performance (more intensive)
    discover_times = []
    for i in range(max(1, iterations // 4)):  # Fewer iterations for more expensive operation
        start_time = time.perf_counter()
        
        try:
            discover_commands()
            end_time = time.perf_counter()
            discover_times.append((end_time - start_time) * 1000)
        except Exception as e:
            print(f"Warning: discover_commands iteration {i+1} failed: {e}")
    
    if discover_times:
        results["discover_commands"] = {
            "mean_ms": statistics.mean(discover_times),
            "median_ms": statistics.median(discover_times),
            "min_ms": min(discover_times),
            "max_ms": max(discover_times),
            "stdev_ms": statistics.stdev(discover_times) if len(discover_times) > 1 else 0
        }
    
    return results


def main():
    """Main entry point for warm execution profiling."""
    parser = argparse.ArgumentParser(description="Profile PromptCraft warm execution performance")
    parser.add_argument("--iterations", type=int, default=10, help="Number of iterations to run")
    parser.add_argument("--command", default="perf-test-0", help="Command name to profile")
    parser.add_argument("--arguments", nargs="*", default=["hello", "world"], help="Command arguments")
    parser.add_argument("--output", help="Output file for JSON results")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    print("PromptCraft Warm Execution Performance Profiler")
    print("=" * 48)
    
    # Measure warm execution performance
    print(f"Measuring warm execution performance...")
    print(f"  Command: {args.command}")
    print(f"  Arguments: {' '.join(args.arguments)}")
    print(f"  Iterations: {args.iterations}")
    
    try:
        warm_results = measure_warm_execution(args.command, args.arguments, args.iterations)
        
        print(f"\nWarm Execution Performance Results:")
        print(f"  Command: {warm_results['command']}")
        print(f"  Iterations: {warm_results['iterations']}")
        print(f"  Mean time: {warm_results['mean_ms']:.2f}ms")
        print(f"  Median time: {warm_results['median_ms']:.2f}ms")
        print(f"  Min time: {warm_results['min_ms']:.2f}ms")
        print(f"  Max time: {warm_results['max_ms']:.2f}ms")
        print(f"  Std deviation: {warm_results['stdev_ms']:.2f}ms")
        print(f"  Target (100ms): {'PASS' if warm_results['passes_target'] else 'FAIL'}")
        print(f"  Memory usage: {warm_results['memory_current_avg_mb']:.2f}MB avg, {warm_results['memory_peak_avg_mb']:.2f}MB peak")
        
    except Exception as e:
        print(f"Error measuring warm execution performance: {e}")
        warm_results = None
        if args.verbose:
            import traceback
            traceback.print_exc()
    
    # Measure file system operations
    print(f"\nMeasuring file system operations performance...")
    
    try:
        fs_results = measure_filesystem_operations(args.iterations)
        
        print(f"\nFile System Performance Results:")
        if "find_command" in fs_results:
            fc = fs_results["find_command"]
            print(f"  find_command_path: {fc['mean_ms']:.2f}ms avg, {fc['min_ms']:.2f}-{fc['max_ms']:.2f}ms range")
        
        if "discover_commands" in fs_results:
            dc = fs_results["discover_commands"]
            print(f"  discover_commands: {dc['mean_ms']:.2f}ms avg, {dc['min_ms']:.2f}-{dc['max_ms']:.2f}ms range")
            
    except Exception as e:
        print(f"Error measuring file system performance: {e}")
        fs_results = {}
        if args.verbose:
            import traceback
            traceback.print_exc()
    
    # Combine results
    combined_results = {
        "timestamp": time.time(),
        "warm_execution": warm_results,
        "filesystem": fs_results
    }
    
    # Save results if requested
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(combined_results, f, indent=2)
        print(f"\nResults saved to: {args.output}")
    
    # Exit with appropriate code based on performance targets
    success = True
    if warm_results and not warm_results['passes_target']:
        print(f"\nWarning: Warm execution performance does not meet target of 100ms")
        success = False
    
    if success:
        print(f"\nSuccess: Warm execution performance meets targets!")
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()