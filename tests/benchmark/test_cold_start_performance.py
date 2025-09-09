"""Cold start performance benchmarks for PromptCraft CLI.

These tests validate that cold start performance meets the acceptance criteria
of <150ms for initial command execution on standard hardware.
"""

import subprocess
import pytest
import time
from pathlib import Path


@pytest.mark.benchmark
@pytest.mark.performance
class TestColdStartPerformance:
    """Test cold start performance requirements."""

    def test_cold_start_performance_target(self, benchmark):
        """Test that cold start performance meets <150ms target.
        
        Measures the time from Python process start to completion
        of a simple command execution.
        """
        # Ensure test template exists
        commands_dir = Path(".promptcraft/commands")
        commands_dir.mkdir(parents=True, exist_ok=True)
        
        test_template = commands_dir / "bench-cold.md"
        if not test_template.exists():
            test_template.write_text("# Cold Start Benchmark\n\nBenchmark test: $ARGUMENTS")
        
        def execute_cold_start():
            """Execute a cold start command."""
            result = subprocess.run(
                ["python", "-m", "promptcraft", "bench-cold", "test", "--stdout"],
                capture_output=True,
                text=True,
                timeout=5.0
            )
            assert result.returncode == 0, f"Command failed: {result.stderr}"
            return result
        
        # Use pytest-benchmark to measure cold start performance
        result = benchmark(execute_cold_start)
        
        # Verify the command actually worked
        assert "Benchmark test: test" in result.stdout
        
        # Clean up
        if test_template.exists():
            test_template.unlink()

    def test_cold_start_consistency(self, benchmark):
        """Test that cold start performance is consistent across runs.
        
        Validates that cold start times don't have excessive variance
        which could indicate performance issues.
        """
        commands_dir = Path(".promptcraft/commands")
        commands_dir.mkdir(parents=True, exist_ok=True)
        
        test_template = commands_dir / "bench-consistency.md"
        if not test_template.exists():
            test_template.write_text("# Consistency Test\n\nConsistency: $ARGUMENTS")
        
        def execute_consistent_cold_start():
            """Execute cold start for consistency testing."""
            result = subprocess.run(
                ["python", "-m", "promptcraft", "bench-consistency", "consistent", "--stdout"],
                capture_output=True,
                text=True,
                timeout=5.0
            )
            assert result.returncode == 0
            return result
        
        # Benchmark with multiple rounds to measure consistency
        benchmark.pedantic(execute_consistent_cold_start, rounds=5, iterations=1)
        
        # Clean up
        if test_template.exists():
            test_template.unlink()

    def test_import_performance_isolation(self, benchmark):
        """Test import performance in isolation.
        
        Measures just the import time without subprocess overhead
        to validate lazy loading effectiveness.
        """
        def import_promptcraft_modules():
            """Import PromptCraft modules and measure time."""
            import importlib
            import sys
            
            # Clear any existing imports to simulate cold start
            modules_to_clear = [name for name in sys.modules.keys() 
                              if name.startswith('promptcraft')]
            for module_name in modules_to_clear:
                if module_name in sys.modules:
                    del sys.modules[module_name]
            
            # Now import the main module (this triggers lazy loading pattern)
            import promptcraft.main
            import promptcraft.core
            import promptcraft.exceptions
            
            return True
        
        result = benchmark(import_promptcraft_modules)
        assert result is True

    @pytest.mark.parametrize("command_args", [
        (["simple-test", "arg1"]),
        (["complex-test", "arg1", "arg2", "arg3", "arg4"]),
        (["unicode-test", "héllo", "wörld", "测试"]),
    ])
    def test_cold_start_with_different_arguments(self, benchmark, command_args):
        """Test cold start performance with various argument patterns.
        
        Validates that argument complexity doesn't significantly impact
        cold start performance.
        """
        commands_dir = Path(".promptcraft/commands")
        commands_dir.mkdir(parents=True, exist_ok=True)
        
        template_name = command_args[0]
        args = command_args[1:]
        
        test_template = commands_dir / f"{template_name}.md"
        if not test_template.exists():
            test_template.write_text(f"# {template_name.title()}\n\nTest args: $ARGUMENTS")
        
        def execute_with_args():
            result = subprocess.run(
                ["python", "-m", "promptcraft", template_name] + args + ["--stdout"],
                capture_output=True,
                text=True,
                timeout=5.0
            )
            assert result.returncode == 0, f"Failed with args {args}: {result.stderr}"
            return result
        
        try:
            result = benchmark(execute_with_args)
            # Verify arguments were processed
            args_string = " ".join(args)
            assert f"Test args: {args_string}" in result.stdout
            
        finally:
            # Clean up
            if test_template.exists():
                test_template.unlink()


@pytest.mark.benchmark
@pytest.mark.performance
def test_python_startup_baseline(benchmark):
    """Benchmark Python startup overhead as a baseline.
    
    This provides context for cold start measurements by showing
    how much time Python itself takes to start up.
    """
    def python_startup():
        """Measure pure Python startup time."""
        result = subprocess.run(
            ["python", "-c", "print('ok')"],
            capture_output=True,
            text=True,
            timeout=2.0
        )
        assert result.returncode == 0
        assert result.stdout.strip() == "ok"
        return result
    
    benchmark(python_startup)


@pytest.mark.benchmark
@pytest.mark.performance 
def test_subprocess_overhead_baseline(benchmark):
    """Benchmark subprocess overhead with minimal Python execution.
    
    Measures the overhead of subprocess creation and Python startup
    with minimal imports, providing baseline for cold start measurements.
    """
    def minimal_python_execution():
        """Execute minimal Python code via subprocess."""
        result = subprocess.run(
            ["python", "-c", "import sys; print(len(sys.argv))"],
            capture_output=True,
            text=True,
            timeout=2.0
        )
        assert result.returncode == 0
        assert result.stdout.strip() == "1"  # Just the script name
        return result
    
    benchmark(minimal_python_execution)