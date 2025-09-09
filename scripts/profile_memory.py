#!/usr/bin/env python3
"""Memory profiling script for PromptCraft.

This script analyzes memory usage patterns during various operations
to identify optimization opportunities.
"""

import tracemalloc
import time
import statistics
import sys
import argparse
from pathlib import Path
from typing import Dict, Any, List
import json


def measure_memory_usage_cold_start(iterations: int = 5) -> Dict[str, Any]:
    """Measure memory usage during cold start operations."""
    print("Measuring cold start memory usage...")
    
    results = []
    
    for i in range(iterations):
        # Start memory tracking before imports
        tracemalloc.start()
        
        start_time = time.perf_counter()
        
        # Simulate cold start - import main modules
        import promptcraft.main
        import promptcraft.core
        import promptcraft.exceptions
        
        end_time = time.perf_counter()
        
        # Get memory snapshot
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        results.append({
            "iteration": i + 1,
            "duration_ms": (end_time - start_time) * 1000,
            "current_bytes": current,
            "peak_bytes": peak,
            "current_mb": current / (1024 * 1024),
            "peak_mb": peak / (1024 * 1024)
        })
        
        # Clear import cache to simulate true cold start
        import importlib
        modules_to_clear = [name for name in sys.modules.keys() 
                          if name.startswith('promptcraft')]
        for module_name in modules_to_clear:
            if module_name in sys.modules:
                del sys.modules[module_name]
    
    # Calculate statistics
    current_bytes = [r["current_bytes"] for r in results]
    peak_bytes = [r["peak_bytes"] for r in results]
    
    return {
        "iterations": len(results),
        "average_current_mb": statistics.mean(r["current_mb"] for r in results),
        "average_peak_mb": statistics.mean(r["peak_mb"] for r in results),
        "max_peak_mb": max(r["peak_mb"] for r in results),
        "min_current_mb": min(r["current_mb"] for r in results),
        "std_current_mb": statistics.stdev(r["current_mb"] for r in results) if len(results) > 1 else 0,
        "std_peak_mb": statistics.stdev(r["peak_mb"] for r in results) if len(results) > 1 else 0,
        "detailed_results": results
    }


def measure_template_processing_memory(iterations: int = 10) -> Dict[str, Any]:
    """Measure memory usage during template processing operations."""
    print("Measuring template processing memory usage...")
    
    # Ensure test template exists
    test_commands_dir = Path(".promptcraft/commands")
    test_commands_dir.mkdir(parents=True, exist_ok=True)
    
    test_template = test_commands_dir / "memory-test.md"
    if not test_template.exists():
        # Create a template with various content sizes
        large_content = "# Memory Test Template\n\n" + "This is test content. " * 100
        large_content += "\n\nTemplate with arguments: $ARGUMENTS\n\n"
        large_content += "Additional content: " + "X" * 1000  # 1KB extra content
        test_template.write_text(large_content)
    
    results = []
    
    # Import modules once
    from promptcraft.core import process_command
    
    for i in range(iterations):
        tracemalloc.start()
        
        start_time = time.perf_counter()
        
        # Process template
        result = process_command("memory-test", ["arg1", "arg2", "test-argument"])
        
        end_time = time.perf_counter()
        
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        results.append({
            "iteration": i + 1,
            "duration_ms": (end_time - start_time) * 1000,
            "current_bytes": current,
            "peak_bytes": peak,
            "current_mb": current / (1024 * 1024),
            "peak_mb": peak / (1024 * 1024),
            "result_size_bytes": len(result.encode('utf-8')) if result else 0
        })
    
    return {
        "iterations": len(results),
        "average_current_mb": statistics.mean(r["current_mb"] for r in results),
        "average_peak_mb": statistics.mean(r["peak_mb"] for r in results),
        "max_peak_mb": max(r["peak_mb"] for r in results),
        "min_current_mb": min(r["current_mb"] for r in results),
        "average_result_size_kb": statistics.mean(r["result_size_bytes"] for r in results) / 1024,
        "detailed_results": results
    }


def measure_discovery_memory() -> Dict[str, Any]:
    """Measure memory usage during command discovery."""
    print("Measuring command discovery memory usage...")
    
    from promptcraft.core import discover_commands
    
    # Clear any existing cache
    import promptcraft.core
    promptcraft.core._DISCOVERY_CACHE.clear()
    
    results = []
    
    # Measure first discovery (cold)
    tracemalloc.start()
    start_time = time.perf_counter()
    commands_cold = discover_commands()
    end_time = time.perf_counter()
    current_cold, peak_cold = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    results.append({
        "type": "cold_discovery",
        "duration_ms": (end_time - start_time) * 1000,
        "current_mb": current_cold / (1024 * 1024),
        "peak_mb": peak_cold / (1024 * 1024),
        "commands_found": len(commands_cold)
    })
    
    # Measure second discovery (warm/cached)
    tracemalloc.start()
    start_time = time.perf_counter()
    commands_warm = discover_commands()
    end_time = time.perf_counter()
    current_warm, peak_warm = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    results.append({
        "type": "warm_discovery",
        "duration_ms": (end_time - start_time) * 1000,
        "current_mb": current_warm / (1024 * 1024),
        "peak_mb": peak_warm / (1024 * 1024),
        "commands_found": len(commands_warm)
    })
    
    return {
        "cold_discovery": results[0],
        "warm_discovery": results[1],
        "cache_effectiveness": {
            "time_reduction_percent": ((results[0]["duration_ms"] - results[1]["duration_ms"]) / results[0]["duration_ms"]) * 100,
            "memory_reduction_percent": ((results[0]["peak_mb"] - results[1]["peak_mb"]) / results[0]["peak_mb"]) * 100 if results[0]["peak_mb"] > 0 else 0
        }
    }


def analyze_string_operations_memory() -> Dict[str, Any]:
    """Analyze memory usage of string operations in template processing."""
    print("Analyzing string operations memory usage...")
    
    # Test different string operation patterns
    test_cases = [
        ("small_template", "Hello $ARGUMENTS!", ["world"]),
        ("medium_template", "# Template\n\n" + "Content line. " * 50 + "\n\nArgs: $ARGUMENTS", ["arg1", "arg2", "arg3"]),
        ("large_template", "# Large Template\n\n" + "Large content block. " * 500 + "\n\nArguments provided: $ARGUMENTS\n\n" + "End content. " * 100, ["large", "argument", "list", "with", "many", "items"])
    ]
    
    results = {}
    
    for test_name, template_content, args in test_cases:
        # Create temporary template
        test_file = Path(".promptcraft/commands") / f"{test_name}.md"
        test_file.write_text(template_content)
        
        try:
            tracemalloc.start()
            
            from promptcraft.core import process_command
            result = process_command(test_name, args)
            
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            
            results[test_name] = {
                "template_size_kb": len(template_content.encode('utf-8')) / 1024,
                "result_size_kb": len(result.encode('utf-8')) / 1024,
                "memory_current_mb": current / (1024 * 1024),
                "memory_peak_mb": peak / (1024 * 1024),
                "memory_per_kb_ratio": (peak / (1024 * 1024)) / (len(template_content.encode('utf-8')) / 1024) if len(template_content) > 0 else 0
            }
        
        finally:
            # Clean up test file
            if test_file.exists():
                test_file.unlink()
    
    return results


def main():
    """Main entry point for memory profiling."""
    parser = argparse.ArgumentParser(description="Profile PromptCraft memory usage")
    parser.add_argument("--iterations", type=int, default=5, help="Number of iterations for tests")
    parser.add_argument("--output", help="Output file for JSON results")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    print("PromptCraft Memory Usage Profiler")
    print("=" * 35)
    
    # Run all memory profiling tests
    try:
        cold_start_memory = measure_memory_usage_cold_start(args.iterations)
        print(f"[OK] Cold start average peak: {cold_start_memory['average_peak_mb']:.2f}MB")
        
    except Exception as e:
        print(f"[ERROR] Cold start memory profiling failed: {e}")
        cold_start_memory = {}
    
    try:
        template_memory = measure_template_processing_memory(args.iterations * 2)
        print(f"[OK] Template processing average peak: {template_memory['average_peak_mb']:.2f}MB")
        
    except Exception as e:
        print(f"[ERROR] Template processing memory profiling failed: {e}")
        template_memory = {}
    
    try:
        discovery_memory = measure_discovery_memory()
        print(f"[OK] Discovery cold: {discovery_memory['cold_discovery']['peak_mb']:.2f}MB, warm: {discovery_memory['warm_discovery']['peak_mb']:.2f}MB")
        
    except Exception as e:
        print(f"[ERROR] Discovery memory profiling failed: {e}")
        discovery_memory = {}
    
    try:
        string_memory = analyze_string_operations_memory()
        print(f"[OK] String operations analyzed for {len(string_memory)} test cases")
        
    except Exception as e:
        print(f"[ERROR] String operations analysis failed: {e}")
        string_memory = {}
    
    # Combine results
    combined_results = {
        "timestamp": time.time(),
        "cold_start_memory": cold_start_memory,
        "template_processing_memory": template_memory,
        "discovery_memory": discovery_memory,
        "string_operations_memory": string_memory
    }
    
    # Display summary
    print(f"\nMemory Usage Summary:")
    print(f"=" * 25)
    
    if cold_start_memory:
        print(f"Cold Start Peak: {cold_start_memory['average_peak_mb']:.2f}MB ± {cold_start_memory['std_peak_mb']:.2f}MB")
    
    if template_memory:
        print(f"Template Processing Peak: {template_memory['average_peak_mb']:.2f}MB")
        print(f"Average Result Size: {template_memory['average_result_size_kb']:.1f}KB")
    
    if discovery_memory:
        cache_eff = discovery_memory.get('cache_effectiveness', {})
        print(f"Discovery Cache Effectiveness: {cache_eff.get('time_reduction_percent', 0):.1f}% time reduction")
    
    if string_memory:
        for case_name, case_data in string_memory.items():
            print(f"{case_name}: {case_data['memory_peak_mb']:.2f}MB peak ({case_data['template_size_kb']:.1f}KB template)")
    
    # Save results if requested
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(combined_results, f, indent=2)
        print(f"\nResults saved to: {args.output}")
    
    print(f"\n[SUCCESS] Memory profiling completed!")


if __name__ == "__main__":
    main()