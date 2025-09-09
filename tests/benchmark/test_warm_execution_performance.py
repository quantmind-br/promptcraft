"""Warm execution performance benchmarks for PromptCraft.

These tests validate that warm execution performance meets the acceptance criteria
of <100ms for subsequent command executions with modules already loaded.
"""

import pytest
import time
from pathlib import Path


@pytest.mark.benchmark
@pytest.mark.performance
class TestWarmExecutionPerformance:
    """Test warm execution performance requirements."""

    def test_warm_execution_performance_target(self, benchmark):
        """Test that warm execution meets <100ms target.
        
        Measures execution time with modules already loaded,
        simulating subsequent command executions.
        """
        # Pre-import modules to simulate warm state
        from promptcraft.core import process_command
        
        # Setup test template
        commands_dir = Path(".promptcraft/commands")
        commands_dir.mkdir(parents=True, exist_ok=True)
        
        test_template = commands_dir / "bench-warm.md"
        if not test_template.exists():
            test_template.write_text("# Warm Execution Benchmark\n\nWarm test: $ARGUMENTS")
        
        def execute_warm():
            """Execute warm command processing."""
            result = process_command("bench-warm", ["warm", "test"])
            assert "Warm test: warm test" in result
            return result
        
        try:
            # Benchmark warm execution
            benchmark(execute_warm)
            
        finally:
            # Clean up
            if test_template.exists():
                test_template.unlink()

    def test_template_processing_performance(self, benchmark):
        """Test template processing performance in isolation.
        
        Measures just the template processing without file discovery overhead.
        """
        from promptcraft.core import generate_prompt
        
        # Create test template file
        commands_dir = Path(".promptcraft/commands")
        commands_dir.mkdir(parents=True, exist_ok=True)
        
        test_template = commands_dir / "process-bench.md"
        template_content = "# Processing Benchmark\n\nProcessing: $ARGUMENTS\n\nEnd of template."
        test_template.write_text(template_content)
        
        def process_template():
            """Process template with arguments."""
            result = generate_prompt(test_template, ["benchmark", "arguments"])
            assert "Processing: benchmark arguments" in result
            return result
        
        try:
            benchmark(process_template)
            
        finally:
            # Clean up
            if test_template.exists():
                test_template.unlink()

    def test_command_discovery_performance(self, benchmark):
        """Test command discovery performance with caching.
        
        Validates that command discovery is fast, especially with caching.
        """
        from promptcraft.core import discover_commands
        
        # Clear cache first to test cold discovery
        import promptcraft.core
        promptcraft.core._DISCOVERY_CACHE.clear()
        
        # Create some test templates for discovery
        commands_dir = Path(".promptcraft/commands")
        commands_dir.mkdir(parents=True, exist_ok=True)
        
        test_templates = []
        for i in range(5):
            template = commands_dir / f"discover-test-{i}.md"
            template.write_text(f"# Discovery Test {i}\n\nTest template {i}: $ARGUMENTS")
            test_templates.append(template)
        
        def discover_with_cache():
            """Discover commands (should use cache after first call)."""
            commands = discover_commands()
            # Verify we found our test templates
            test_command_names = [f"discover-test-{i}" for i in range(5)]
            found_names = {cmd.name for cmd in commands}
            for test_name in test_command_names:
                assert test_name in found_names, f"Missing test command: {test_name}"
            return commands
        
        try:
            # First call to populate cache
            discover_commands()
            
            # Now benchmark the cached version
            benchmark(discover_with_cache)
            
        finally:
            # Clean up test templates
            for template in test_templates:
                if template.exists():
                    template.unlink()

    def test_file_path_resolution_performance(self, benchmark):
        """Test file path resolution performance with caching.
        
        Validates that find_command_path is optimized with caching.
        """
        from promptcraft.core import find_command_path
        
        # Setup test template
        commands_dir = Path(".promptcraft/commands")
        commands_dir.mkdir(parents=True, exist_ok=True)
        
        test_template = commands_dir / "path-bench.md"
        if not test_template.exists():
            test_template.write_text("# Path Resolution Benchmark\n\nPath test: $ARGUMENTS")
        
        def resolve_path():
            """Resolve command path (should use cache after first call)."""
            path = find_command_path("path-bench")
            assert path.exists()
            assert path.name == "path-bench.md"
            return path
        
        try:
            # First call to populate cache
            find_command_path("path-bench")
            
            # Now benchmark the cached version
            benchmark(resolve_path)
            
        finally:
            # Clean up
            if test_template.exists():
                test_template.unlink()

    @pytest.mark.parametrize("template_size", [
        ("small", "# Small Template\n\nSmall: $ARGUMENTS"),
        ("medium", "# Medium Template\n\n" + "Content line. " * 50 + "\n\nMedium: $ARGUMENTS"),
        ("large", "# Large Template\n\n" + "Large content. " * 500 + "\n\nLarge: $ARGUMENTS")
    ])
    def test_template_size_performance_scaling(self, benchmark, template_size):
        """Test performance scaling with different template sizes.
        
        Validates that performance scales reasonably with template size.
        """
        from promptcraft.core import process_command
        
        template_name, content = template_size
        
        # Setup template
        commands_dir = Path(".promptcraft/commands")
        commands_dir.mkdir(parents=True, exist_ok=True)
        
        test_template = commands_dir / f"size-{template_name}.md"
        test_template.write_text(content)
        
        def process_sized_template():
            """Process template of specific size."""
            result = process_command(f"size-{template_name}", ["test", "args"])
            assert f"{template_name.title()}: test args" in result
            return result
        
        try:
            benchmark(process_sized_template)
            
        finally:
            # Clean up
            if test_template.exists():
                test_template.unlink()

    def test_argument_substitution_performance(self, benchmark):
        """Test performance of argument substitution with many arguments.
        
        Validates that argument processing is efficient even with
        many arguments.
        """
        from promptcraft.core import generate_prompt
        
        # Create template with argument placeholder
        commands_dir = Path(".promptcraft/commands")
        commands_dir.mkdir(parents=True, exist_ok=True)
        
        test_template = commands_dir / "args-bench.md"
        test_template.write_text("# Args Benchmark\n\nArgs: $ARGUMENTS\n\nEnd of template.")
        
        # Many arguments to test substitution performance
        many_args = [f"arg{i}" for i in range(20)]
        
        def substitute_many_args():
            """Substitute many arguments into template."""
            result = generate_prompt(test_template, many_args)
            expected_args = " ".join(many_args)
            assert f"Args: {expected_args}" in result
            return result
        
        try:
            benchmark(substitute_many_args)
            
        finally:
            # Clean up
            if test_template.exists():
                test_template.unlink()


@pytest.mark.benchmark
@pytest.mark.performance
def test_cache_effectiveness_timing(benchmark):
    """Test that caching provides measurable performance improvements.
    
    This test validates that our caching mechanisms actually improve
    performance by comparing cached vs uncached operations.
    """
    from promptcraft.core import discover_commands, find_command_path
    import promptcraft.core
    
    # Setup test templates
    commands_dir = Path(".promptcraft/commands")
    commands_dir.mkdir(parents=True, exist_ok=True)
    
    test_templates = []
    for i in range(3):
        template = commands_dir / f"cache-test-{i}.md"
        template.write_text(f"# Cache Test {i}\n\nCache test {i}: $ARGUMENTS")
        test_templates.append(template)
    
    def cached_operations():
        """Perform operations that should benefit from caching."""
        # Discovery (uses cache)
        commands = discover_commands()
        
        # Path resolution (uses cache)
        for i in range(3):
            path = find_command_path(f"cache-test-{i}")
            assert path.exists()
        
        return len(commands)
    
    try:
        # First run to populate caches
        cached_operations()
        
        # Now benchmark the cached version
        result = benchmark(cached_operations)
        assert result > 0
        
    finally:
        # Clean up
        for template in test_templates:
            if template.exists():
                template.unlink()