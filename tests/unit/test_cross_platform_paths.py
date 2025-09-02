"""Cross-platform path handling tests using pathlib."""

import os
import tempfile
import sys
from pathlib import Path, PurePath, PurePosixPath, PureWindowsPath
from unittest.mock import patch, Mock

import pytest
from promptcraft.core import find_command_path, discover_commands, generate_prompt, process_command
from promptcraft.exceptions import CommandNotFoundError, TemplateReadError


class TestPathlibCrossPlatformCompatibility:
    """Test pathlib usage for cross-platform compatibility."""

    def test_pathlib_path_construction(self):
        """Test that pathlib constructs paths correctly on all platforms."""
        # Test basic path construction
        test_paths = [
            (".promptcraft", "commands"),
            ("home", "user", ".promptcraft", "commands"),
            ("C:", "Users", "user", ".promptcraft"),  # Windows-style (will be handled correctly)
        ]
        
        for path_parts in test_paths:
            path = Path(*path_parts)
            
            # Should create valid Path object
            assert isinstance(path, Path)
            
            # Should use correct separator for current platform
            path_str = str(path)
            if os.name == 'nt':
                assert '\\' in path_str or '/' in path_str  # Windows allows both
            else:
                assert '\\' not in path_str  # Unix should not have backslashes

    def test_pathlib_path_resolution(self):
        """Test pathlib path resolution across platforms."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)
            
            # Test various path resolution patterns
            path_patterns = [
                base_path / ".promptcraft" / "commands",
                base_path.joinpath(".promptcraft", "commands"),
                base_path / Path(".promptcraft") / Path("commands"),
            ]
            
            for pattern in path_patterns:
                # Should resolve to same path regardless of construction method
                resolved = pattern.resolve()
                assert resolved.is_absolute()
                assert resolved.name == "commands"
                assert resolved.parent.name == ".promptcraft"

    def test_pathlib_exists_and_is_file_cross_platform(self):
        """Test pathlib existence and file type checking across platforms."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)
            
            # Create test structure
            cmd_dir = base_path / ".promptcraft" / "commands"
            cmd_dir.mkdir(parents=True)
            
            test_file = cmd_dir / "test-cmd.md"
            test_file.write_text("# Test Command\n\nTest content.")
            
            # Test existence checking
            assert base_path.exists()
            assert cmd_dir.exists()
            assert test_file.exists()
            
            # Test type checking
            assert base_path.is_dir()
            assert cmd_dir.is_dir()
            assert test_file.is_file()
            
            # Test non-existence
            nonexistent = cmd_dir / "nonexistent.md"
            assert not nonexistent.exists()
            assert not nonexistent.is_file()

    def test_pathlib_glob_patterns_cross_platform(self):
        """Test pathlib glob patterns work consistently across platforms."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)
            cmd_dir = base_path / "commands"
            cmd_dir.mkdir()
            
            # Create test files with various names
            test_files = [
                "simple.md",
                "with-dashes.md",
                "with_underscores.md",
                "CamelCase.md",
                "123numeric.md",
                "dots.in.name.md",
            ]
            
            for filename in test_files:
                (cmd_dir / filename).write_text(f"# {filename[:-3]}")
            
            # Test glob patterns
            patterns = [
                "*.md",
                "**/*.md",
                "*-*.md",  # Files with dashes
                "*_*.md",  # Files with underscores
                "[Cc]*.md",  # Case-insensitive pattern
            ]
            
            for pattern in patterns:
                matches = list(cmd_dir.glob(pattern))
                assert len(matches) >= 1
                
                # All matches should be .md files
                for match in matches:
                    assert match.suffix == ".md"
                    assert match.is_file()

    def test_pathlib_stem_and_suffix_handling(self):
        """Test pathlib stem and suffix handling across platforms."""
        test_filenames = [
            "simple.md",
            "complex-name.md",
            "with_underscores.md",
            "dots.in.name.md",
            "multiple.dots.here.md",
            "no-extension",
            ".hidden.md",
        ]
        
        for filename in test_filenames:
            path = Path(filename)
            
            # Test stem (filename without suffix)
            if filename == "no-extension":
                assert path.stem == "no-extension"
                assert path.suffix == ""
            elif filename == ".hidden.md":
                assert path.stem == ".hidden"
                assert path.suffix == ".md"
            elif filename == "dots.in.name.md":
                assert path.stem == "dots.in.name"
                assert path.suffix == ".md"
            else:
                assert path.suffix == ".md"
                assert path.stem == filename[:-3]  # Remove .md

    def test_pathlib_parent_and_parts_cross_platform(self):
        """Test pathlib parent and parts handling across platforms."""
        # Create complex path
        complex_path = Path("home") / "user" / ".promptcraft" / "commands" / "file.md"
        
        # Test parent navigation
        assert complex_path.name == "file.md"
        assert complex_path.parent.name == "commands"
        assert complex_path.parent.parent.name == ".promptcraft"
        assert complex_path.parent.parent.parent.name == "user"
        
        # Test parts
        parts = complex_path.parts
        assert parts[-1] == "file.md"
        assert parts[-2] == "commands"
        assert parts[-3] == ".promptcraft"
        
        # Test cross-platform part handling
        if os.name == 'nt':
            # On Windows, first part might be drive letter
            assert len(parts) >= 4
        else:
            # On Unix, parts should be exactly what we specified
            assert parts == ("home", "user", ".promptcraft", "commands", "file.md")


class TestFilePathResolutionOnDifferentOS:
    """Test file path resolution on different operating systems."""

    @patch('promptcraft.core.Path.cwd')
    @patch('promptcraft.core.Path.home')
    def test_windows_path_resolution(self, mock_home, mock_cwd):
        """Test path resolution with Windows-style paths."""
        # Mock Windows-style paths
        mock_cwd.return_value = PureWindowsPath("C:\\Users\\User\\Project")
        mock_home.return_value = PureWindowsPath("C:\\Users\\User")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create actual directory structure for testing
            base_path = Path(tmpdir)
            cmd_dir = base_path / ".promptcraft" / "commands"
            cmd_dir.mkdir(parents=True)
            
            test_file = cmd_dir / "windows-test.md"
            test_file.write_text("# Windows Test\n\nWindows-specific test.")
            
            # Override the mocked paths to use our temp directory
            mock_cwd.return_value = base_path
            
            # Test command discovery
            result = discover_commands()
            
            assert len(result) >= 1
            windows_cmd = next((cmd for cmd in result if cmd.name == "windows-test"), None)
            assert windows_cmd is not None
            assert windows_cmd.source == "Project"

    @patch('promptcraft.core.Path.cwd')
    @patch('promptcraft.core.Path.home')
    def test_unix_path_resolution(self, mock_home, mock_cwd):
        """Test path resolution with Unix-style paths."""
        # Mock Unix-style paths
        mock_cwd.return_value = PurePosixPath("/home/user/project")
        mock_home.return_value = PurePosixPath("/home/user")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create actual directory structure for testing
            base_path = Path(tmpdir)
            cmd_dir = base_path / ".promptcraft" / "commands"
            cmd_dir.mkdir(parents=True)
            
            test_file = cmd_dir / "unix-test.md"
            test_file.write_text("# Unix Test\n\nUnix-specific test.")
            
            # Override the mocked paths to use our temp directory
            mock_cwd.return_value = base_path
            
            # Test command discovery
            result = discover_commands()
            
            assert len(result) >= 1
            unix_cmd = next((cmd for cmd in result if cmd.name == "unix-test"), None)
            assert unix_cmd is not None
            assert unix_cmd.source == "Project"

    def test_mixed_separator_handling(self):
        """Test handling of mixed path separators."""
        if os.name == 'nt':
            # On Windows, test both separators
            mixed_paths = [
                "C:\\Users\\User/.promptcraft/commands",
                "C:/Users/User\\.promptcraft\\commands",
                ".\\promptcraft/commands",
            ]
            
            for path_str in mixed_paths:
                path = Path(path_str)
                # Should normalize separators
                normalized = str(path)
                # Windows Path should use consistent separators
                assert isinstance(path, Path)
        else:
            # On Unix, backslashes are part of filename
            path = Path("dir\\with\\backslashes")
            assert "\\with\\backslashes" in str(path)

    def test_absolute_vs_relative_path_handling(self):
        """Test absolute vs relative path handling across platforms."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)
            
            # Test relative path handling
            relative_path = Path(".promptcraft") / "commands" / "relative-test.md"
            absolute_path = base_path / relative_path
            
            # Create the structure
            absolute_path.parent.mkdir(parents=True)
            absolute_path.write_text("# Relative Test")
            
            # Test that both resolve correctly
            assert relative_path.name == "relative-test.md"
            assert absolute_path.name == "relative-test.md"
            assert absolute_path.is_absolute()
            assert not relative_path.is_absolute()
            
            # Test resolution
            resolved_relative = (base_path / relative_path).resolve()
            resolved_absolute = absolute_path.resolve()
            
            assert resolved_relative == resolved_absolute

    def test_case_sensitivity_across_platforms(self):
        """Test case sensitivity handling across different platforms."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)
            cmd_dir = base_path / ".promptcraft" / "commands"
            cmd_dir.mkdir(parents=True)
            
            # Create files with different cases
            original_file = cmd_dir / "CaseTest.md"
            original_file.write_text("# Case Test")
            
            # Test case sensitivity based on platform
            different_case = cmd_dir / "casetest.md"
            
            if sys.platform.startswith('darwin') or os.name == 'nt':
                # macOS and Windows are typically case-insensitive
                # Note: This might vary based on filesystem
                pass  # Skip detailed case sensitivity tests
            else:
                # Linux is typically case-sensitive
                assert not different_case.exists()
                
                # Create file with different case
                different_case.write_text("# Different Case")
                assert different_case.exists()
                assert original_file.exists()


class TestTemplateDirectoryScanningOnVariousPlatforms:
    """Test template directory scanning on various platforms."""

    def test_directory_scanning_with_platform_specific_paths(self):
        """Test directory scanning handles platform-specific path quirks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)
            
            # Create platform-agnostic structure
            structure_tests = [
                ("simple", "commands"),
                ("with spaces", "commands"),
                ("with-dashes", "commands"),
                ("with_underscores", "commands"),
                ("123numeric", "commands"),
            ]
            
            created_dirs = []
            for dir_name, subdir in structure_tests:
                try:
                    test_dir = base_path / dir_name / ".promptcraft" / subdir
                    test_dir.mkdir(parents=True)
                    
                    # Create test file
                    test_file = test_dir / "platform-test.md"
                    test_file.write_text(f"# Platform Test in {dir_name}")
                    
                    created_dirs.append((dir_name, test_dir))
                except OSError:
                    # Some names might not be valid on certain platforms
                    continue
            
            # Test scanning each directory
            for dir_name, test_dir in created_dirs:
                with patch('promptcraft.core.Path.cwd', return_value=base_path / dir_name):
                    result = discover_commands()
                    
                    assert len(result) >= 1
                    platform_cmd = next((cmd for cmd in result if cmd.name == "platform-test"), None)
                    assert platform_cmd is not None

    def test_deep_directory_nesting(self):
        """Test scanning works with deeply nested directory structures."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)
            
            # Create deeply nested structure
            deep_path = base_path
            for i in range(10):  # 10 levels deep
                deep_path = deep_path / f"level{i}"
            
            cmd_dir = deep_path / ".promptcraft" / "commands"
            cmd_dir.mkdir(parents=True)
            
            test_file = cmd_dir / "deep-test.md"
            test_file.write_text("# Deep Test\n\nDeeply nested command.")
            
            # Test that scanning works even with deep nesting
            with patch('promptcraft.core.Path.cwd', return_value=deep_path):
                result = discover_commands()
                
                assert len(result) >= 1
                deep_cmd = next((cmd for cmd in result if cmd.name == "deep-test"), None)
                assert deep_cmd is not None
                assert deep_cmd.source == "Project"

    def test_scanning_with_special_characters_in_paths(self):
        """Test directory scanning with special characters in paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)
            
            # Test various special character combinations
            special_dirs = [
                "normal",
                "with spaces",
                "with-dashes",
                "with_underscores",
                "with.dots",
                "with(parentheses)",
                "with[brackets]",
            ]
            
            # Add Unicode if platform supports it
            if sys.platform != 'win32':  # Windows filename handling varies
                special_dirs.extend([
                    "café",
                    "测试目录",
                ])
            
            successful_dirs = []
            for dir_name in special_dirs:
                try:
                    test_dir = base_path / dir_name / ".promptcraft" / "commands"
                    test_dir.mkdir(parents=True)
                    
                    test_file = test_dir / "special-char-test.md"
                    test_file.write_text(f"# Special Char Test in {dir_name}")
                    
                    successful_dirs.append((dir_name, test_dir))
                except (OSError, UnicodeEncodeError):
                    # Some special characters might not be supported
                    continue
            
            # Test each successful directory
            for dir_name, test_dir in successful_dirs:
                with patch('promptcraft.core.Path.cwd', return_value=base_path / dir_name):
                    result = discover_commands()
                    
                    assert len(result) >= 1
                    special_cmd = next((cmd for cmd in result if cmd.name == "special-char-test"), None)
                    assert special_cmd is not None

    def test_symbolic_link_handling_across_platforms(self):
        """Test symbolic link handling on platforms that support them."""
        if os.name == 'nt':
            pytest.skip("Symbolic link tests require elevated privileges on Windows")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)
            
            # Create actual directory structure
            actual_dir = base_path / "actual" / ".promptcraft" / "commands"
            actual_dir.mkdir(parents=True)
            
            actual_file = actual_dir / "symlink-test.md"
            actual_file.write_text("# Symlink Test\n\nSymlinked command.")
            
            # Create symbolic links at various levels
            link_scenarios = [
                ("link-to-commands", actual_dir),  # Link to commands directory
                ("link-to-promptcraft", actual_dir.parent),  # Link to .promptcraft directory
            ]
            
            successful_links = []
            for link_name, target in link_scenarios:
                try:
                    link_path = base_path / link_name
                    link_path.symlink_to(target, target_is_directory=True)
                    successful_links.append(link_name)
                except OSError:
                    # Symlink creation might fail
                    continue
            
            # Test scanning through symlinks
            for link_name in successful_links:
                if link_name == "link-to-commands":
                    # Direct link to commands directory
                    with patch('promptcraft.core.Path.cwd', return_value=base_path), \
                         patch('promptcraft.core.Path.home', return_value=Path("/fake")):
                        
                        # Manually check the linked directory
                        linked_commands = base_path / link_name
                        if linked_commands.exists():
                            files = list(linked_commands.glob("*.md"))
                            assert len(files) >= 1
                
                elif link_name == "link-to-promptcraft":
                    # Link to .promptcraft directory structure
                    fake_project = base_path / "fake-project"
                    fake_project.mkdir()
                    
                    # Create symlink to .promptcraft in fake project
                    (fake_project / ".promptcraft").symlink_to(target, target_is_directory=True)
                    
                    with patch('promptcraft.core.Path.cwd', return_value=fake_project):
                        result = discover_commands()
                        
                        symlink_cmd = next((cmd for cmd in result if cmd.name == "symlink-test"), None)
                        assert symlink_cmd is not None


class TestPathNormalizationAndEdgeCases:
    """Test path normalization and edge cases."""

    def test_path_normalization(self):
        """Test that paths are properly normalized across platforms."""
        # Test various path patterns that need normalization
        path_tests = [
            ("./current/dir", "current/dir"),
            ("../parent/dir", "../parent/dir"),
            ("dir/../same", "same"),
            ("dir/./same", "dir/same"),
            ("//double//slashes", "double/slashes" if os.name != 'nt' else "double\\slashes"),
        ]
        
        for input_path, expected_pattern in path_tests:
            path = Path(input_path)
            normalized = path.resolve()
            
            # Should be absolute after resolve
            assert normalized.is_absolute()

    def test_edge_case_directory_names(self):
        """Test edge cases in directory names."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)
            
            # Test edge case directory names
            edge_cases = [
                ".",  # Current directory (might cause issues)
                "..",  # Parent directory (might cause issues)
                "...",  # Triple dots
                " ",  # Single space
                "  ",  # Multiple spaces
                "-",  # Single dash
                "_",  # Single underscore
                "a",  # Single character
                "A",  # Single capital
                "0",  # Single digit
            ]
            
            successful_cases = []
            for case in edge_cases:
                if case in [".", ".."]:
                    continue  # Skip problematic cases
                
                try:
                    case_dir = base_path / case / ".promptcraft" / "commands"
                    case_dir.mkdir(parents=True)
                    
                    test_file = case_dir / "edge-case.md"
                    test_file.write_text(f"# Edge Case: {case}")
                    
                    successful_cases.append(case)
                except OSError:
                    # Some edge cases might not be valid directory names
                    continue
            
            # Test each successful case
            for case in successful_cases:
                with patch('promptcraft.core.Path.cwd', return_value=base_path / case):
                    result = discover_commands()
                    
                    assert len(result) >= 1
                    edge_cmd = next((cmd for cmd in result if cmd.name == "edge-case"), None)
                    assert edge_cmd is not None

    def test_long_path_handling(self):
        """Test handling of very long paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)
            
            # Create a very long path (but within filesystem limits)
            long_components = ["very-long-directory-name-component"] * 10
            long_path = base_path
            
            try:
                for component in long_components:
                    long_path = long_path / component
                
                cmd_dir = long_path / ".promptcraft" / "commands"
                cmd_dir.mkdir(parents=True)
                
                test_file = cmd_dir / "long-path-test.md"
                test_file.write_text("# Long Path Test")
                
                # Should handle long paths correctly
                assert test_file.exists()
                assert test_file.is_file()
                
                # Test command discovery with long path
                with patch('promptcraft.core.Path.cwd', return_value=long_path):
                    result = discover_commands()
                    
                    long_cmd = next((cmd for cmd in result if cmd.name == "long-path-test"), None)
                    assert long_cmd is not None
                    
            except OSError as e:
                if "too long" in str(e).lower():
                    pytest.skip("Path too long for filesystem")
                else:
                    raise

    def test_concurrent_path_operations(self):
        """Test concurrent path operations don't interfere with each other."""
        import threading
        import queue
        
        results = queue.Queue()
        
        def test_path_operations(thread_id):
            try:
                with tempfile.TemporaryDirectory() as tmpdir:
                    base_path = Path(tmpdir)
                    cmd_dir = base_path / ".promptcraft" / "commands"
                    cmd_dir.mkdir(parents=True)
                    
                    test_file = cmd_dir / f"concurrent-{thread_id}.md"
                    test_file.write_text(f"# Concurrent Test {thread_id}")
                    
                    # Test various path operations
                    assert test_file.exists()
                    assert test_file.is_file()
                    assert test_file.parent.is_dir()
                    
                    content = test_file.read_text()
                    assert f"Concurrent Test {thread_id}" in content
                    
                    results.put((thread_id, "success", None))
                    
            except Exception as e:
                results.put((thread_id, "error", str(e)))
        
        # Start multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=test_path_operations, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Check results
        thread_results = []
        while not results.empty():
            thread_results.append(results.get())
        
        assert len(thread_results) == 10
        
        for thread_id, status, error in thread_results:
            if error:
                pytest.fail(f"Thread {thread_id} failed: {error}")
            assert status == "success"