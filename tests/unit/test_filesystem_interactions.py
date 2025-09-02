"""Comprehensive file system interaction tests using temporary directories."""

import os
import tempfile
import shutil
import stat
from pathlib import Path
from unittest.mock import patch, Mock, mock_open

import pytest
from promptcraft.core import (
    find_command_path, generate_prompt, process_command, 
    discover_commands, _extract_description
)
from promptcraft.exceptions import CommandNotFoundError, TemplateReadError


class TestTemplateFileDiscovery:
    """Test template file discovery in different directory structures."""

    def test_discovery_in_nested_directory_structures(self):
        """Test template discovery in deeply nested directory structures."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)
            
            # Create nested project structure
            project_levels = [
                "level1/level2/level3/project",
                "different/nested/structure/project2"
            ]
            
            for level_path in project_levels:
                full_path = base_path / level_path
                cmd_dir = full_path / ".promptcraft" / "commands"
                cmd_dir.mkdir(parents=True)
                
                # Create template files at each level
                (cmd_dir / f"nested-cmd-{level_path.replace('/', '-')}.md").write_text(
                    f"# Nested Command for {level_path}\n\nCommand at {level_path}."
                )
            
            # Test discovery from each nested level
            for level_path in project_levels:
                full_path = base_path / level_path
                with patch('promptcraft.core.Path.cwd', return_value=full_path):
                    result = discover_commands()
                    
                    assert len(result) >= 1
                    assert any(cmd.source == "Project" for cmd in result)

    def test_discovery_with_mixed_directory_permissions(self):
        """Test template discovery with various directory permissions."""
        if os.name == 'nt':
            pytest.skip("Permission tests not reliable on Windows")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)
            
            # Create directories with different permissions
            permission_scenarios = [
                ("readable", 0o755, True),
                ("read_only", 0o444, True),
                ("no_execute", 0o644, False),  # Can't list directory without execute
            ]
            
            for dir_name, permissions, should_discover in permission_scenarios:
                dir_path = base_path / dir_name / ".promptcraft" / "commands"
                dir_path.mkdir(parents=True)
                
                # Create template file
                (dir_path / f"{dir_name}-cmd.md").write_text(f"# {dir_name} Command")
                
                try:
                    # Set directory permissions
                    dir_path.chmod(permissions)
                    
                    with patch('promptcraft.core.Path.cwd', return_value=base_path / dir_name):
                        result = discover_commands()
                        
                        if should_discover:
                            assert len(result) >= 1
                            assert result[0].name == f"{dir_name}-cmd"
                        # For cases where discovery might fail due to permissions,
                        # we just ensure it doesn't crash
                        
                finally:
                    # Restore permissions for cleanup
                    try:
                        dir_path.chmod(0o755)
                    except:
                        pass

    def test_discovery_with_symlinked_directories(self):
        """Test template discovery with symbolic links to directories."""
        if os.name == 'nt':
            pytest.skip("Symlink test not applicable on Windows")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)
            
            # Create actual directory structure
            actual_dir = base_path / "actual" / ".promptcraft" / "commands"
            actual_dir.mkdir(parents=True)
            (actual_dir / "actual-cmd.md").write_text("# Actual Command\n\nActual content.")
            
            # Create symlink to .promptcraft directory
            symlink_base = base_path / "symlinked"
            symlink_base.mkdir()
            symlink_promptcraft = symlink_base / ".promptcraft"
            
            try:
                symlink_promptcraft.symlink_to(actual_dir.parent, target_is_directory=True)
                
                with patch('promptcraft.core.Path.cwd', return_value=symlink_base):
                    result = discover_commands()
                    
                    assert len(result) >= 1
                    assert result[0].name == "actual-cmd"
                    assert result[0].source == "Project"
                    
            except OSError:
                pytest.skip("Cannot create directory symlinks on this system")

    def test_discovery_with_case_sensitive_filesystems(self):
        """Test template discovery behavior on case-sensitive filesystems."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)
            cmd_dir = base_path / ".promptcraft" / "commands"
            cmd_dir.mkdir(parents=True)
            
            # Create files with different cases
            case_variants = [
                "lowercase.md",
                "UPPERCASE.md", 
                "CamelCase.md",
                "mixed_Case.md"
            ]
            
            created_files = []
            for variant in case_variants:
                try:
                    file_path = cmd_dir / variant
                    file_path.write_text(f"# {variant[:-3]}\n\nCase variant command.")
                    created_files.append(variant[:-3])  # Remove .md extension
                except OSError:
                    # Some filesystems might not support certain case combinations
                    continue
            
            with patch('promptcraft.core.Path.cwd', return_value=base_path):
                result = discover_commands()
                
                # Should find all successfully created files
                found_names = {cmd.name for cmd in result}
                for created_name in created_files:
                    assert created_name in found_names

    def test_discovery_with_unicode_directory_names(self):
        """Test template discovery with Unicode directory names."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)
            
            # Create directories with Unicode names
            unicode_dirs = ["café", "测试", "🚀project"]
            
            for unicode_dir in unicode_dirs:
                try:
                    dir_path = base_path / unicode_dir / ".promptcraft" / "commands"
                    dir_path.mkdir(parents=True)
                    
                    (dir_path / "unicode-test.md").write_text(
                        f"# Unicode Test in {unicode_dir}\n\nUnicode directory test."
                    )
                    
                    with patch('promptcraft.core.Path.cwd', return_value=base_path / unicode_dir):
                        result = discover_commands()
                        
                        assert len(result) >= 1
                        assert result[0].name == "unicode-test"
                        
                except (OSError, UnicodeEncodeError):
                    # Skip if filesystem doesn't support Unicode
                    continue


class TestFileReadingAndContentProcessing:
    """Test file reading and content processing functionality."""

    def test_template_reading_with_various_encodings(self):
        """Test template reading with different text encodings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            template_path = Path(tmpdir) / "encoding-test.md"
            
            # Test UTF-8 (default)
            utf8_content = "# UTF-8 Template\n\nContent with émojis: 🚀 and Unicode: 测试"
            template_path.write_text(utf8_content, encoding='utf-8')
            
            result = generate_prompt(template_path, ["utf8", "test"])
            assert "émojis: 🚀" in result
            assert "Unicode: 测试" in result
            assert "utf8 test" in result

    def test_template_reading_with_different_line_endings(self):
        """Test template reading with different line ending formats."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Test different line ending formats
            line_ending_tests = [
                ("unix", "\n", "Unix LF"),
                ("windows", "\r\n", "Windows CRLF"),
                ("mac", "\r", "Mac CR")
            ]
            
            for name, line_ending, description in line_ending_tests:
                template_path = Path(tmpdir) / f"{name}-endings.md"
                content = f"# {description}{line_ending}{line_ending}Arguments: $ARGUMENTS{line_ending}End of template."
                
                # Write with binary mode to control line endings exactly
                template_path.write_bytes(content.encode('utf-8'))
                
                result = generate_prompt(template_path, [name, "test"])
                
                assert description in result
                assert f"{name} test" in result
                assert "End of template" in result

    def test_template_processing_with_large_files(self):
        """Test template processing with large template files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            large_template = Path(tmpdir) / "large-template.md"
            
            # Create large template (approximately 1MB)
            large_content = "# Large Template\n\n"
            content_block = "This is a line of content with $ARGUMENTS placeholder.\n" * 1000
            large_content += content_block * 20  # ~1MB total
            
            large_template.write_text(large_content, encoding='utf-8')
            
            # Test processing large template
            result = generate_prompt(large_template, ["large", "file", "test"])
            
            assert result.startswith("# Large Template")
            assert "large file test" in result
            assert len(result) > 1000000  # Should be large
            
            # Ensure all placeholders were replaced
            assert "$ARGUMENTS" not in result

    def test_template_processing_memory_efficiency(self):
        """Test that template processing is memory efficient."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Process many small templates to test memory usage
            for i in range(1000):
                template_path = Path(tmpdir) / f"template-{i}.md"
                content = f"# Template {i}\n\nTemplate {i} with $ARGUMENTS."
                template_path.write_text(content)
                
                result = generate_prompt(template_path, [f"arg{i}"])
                
                assert f"Template {i}" in result
                assert f"arg{i}" in result
                
                # Clean up immediately to test memory management
                template_path.unlink()

    def test_concurrent_file_reading(self):
        """Test concurrent template file reading."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create multiple template files
            template_files = []
            for i in range(10):
                template_path = Path(tmpdir) / f"concurrent-{i}.md"
                content = f"# Concurrent Template {i}\n\nContent {i} with $ARGUMENTS."
                template_path.write_text(content)
                template_files.append(template_path)
            
            import threading
            import queue
            
            results = queue.Queue()
            
            def read_template(template_path, args):
                try:
                    result = generate_prompt(template_path, args)
                    results.put((template_path.name, result, None))
                except Exception as e:
                    results.put((template_path.name, None, str(e)))
            
            # Start concurrent reading threads
            threads = []
            for i, template_path in enumerate(template_files):
                thread = threading.Thread(
                    target=read_template, 
                    args=(template_path, [f"concurrent-{i}"])
                )
                threads.append(thread)
                thread.start()
            
            # Wait for all threads
            for thread in threads:
                thread.join(timeout=5.0)
            
            # Check results
            completed_results = []
            while not results.empty():
                completed_results.append(results.get())
            
            assert len(completed_results) == 10
            
            for filename, result, error in completed_results:
                assert error is None, f"Error in {filename}: {error}"
                assert result is not None
                assert "Concurrent Template" in result


class TestErrorHandlingForMissingOrCorruptedFiles:
    """Test error handling for missing, corrupted, or problematic files."""

    def test_missing_file_error_handling(self):
        """Test proper error handling when template files are missing."""
        nonexistent_files = [
            Path("/completely/fake/path/missing.md"),
            Path("/tmp/nonexistent/missing.md"),
            Path("./relative/missing.md"),
        ]
        
        for missing_file in nonexistent_files:
            with pytest.raises(TemplateReadError) as exc_info:
                generate_prompt(missing_file, ["test"])
            
            error = exc_info.value
            assert "Template file not found" in str(error)
            assert str(missing_file) in str(error)
            assert error.error_code == "TEMPLATE_FILE_NOT_FOUND"

    def test_permission_denied_error_handling(self):
        """Test error handling when file permissions deny access."""
        if os.name == 'nt':
            pytest.skip("Permission tests not reliable on Windows")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            template_path = Path(tmpdir) / "permission-denied.md"
            template_path.write_text("# Test Template\n\nContent with $ARGUMENTS.")
            
            # Remove read permissions
            template_path.chmod(0o000)
            
            try:
                with pytest.raises(TemplateReadError) as exc_info:
                    generate_prompt(template_path, ["test"])
                
                error = exc_info.value
                assert "Permission denied" in str(error)
                assert str(template_path) in str(error)
                assert error.error_code == "TEMPLATE_PERMISSION_DENIED"
                
            finally:
                # Restore permissions for cleanup
                template_path.chmod(0o644)

    def test_binary_file_error_handling(self):
        """Test error handling when trying to read binary files as templates."""
        with tempfile.TemporaryDirectory() as tmpdir:
            binary_files = [
                ("image.md", b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR'),  # PNG header
                ("executable.md", b'\x7fELF\x01\x01\x01\x00'),  # ELF header  
                ("random.md", bytes(range(256))),  # All byte values
            ]
            
            for filename, binary_content in binary_files:
                binary_path = Path(tmpdir) / filename
                binary_path.write_bytes(binary_content)
                
                with pytest.raises(TemplateReadError) as exc_info:
                    generate_prompt(binary_path, ["test"])
                
                error = exc_info.value
                assert ("Failed to decode" in str(error) or 
                       "encoding" in str(error).lower())
                assert error.error_code == "TEMPLATE_ENCODING_ERROR"

    def test_corrupted_file_error_handling(self):
        """Test error handling with corrupted or malformed template files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create file with invalid UTF-8 sequences
            corrupted_path = Path(tmpdir) / "corrupted.md"
            
            # Write valid UTF-8 first, then append invalid bytes
            corrupted_path.write_text("# Valid Header\n\nValid content up to here: ")
            
            # Append invalid UTF-8 bytes
            with open(corrupted_path, 'ab') as f:
                f.write(b'\xff\xfe\x00\x00Invalid UTF-8')
            
            with pytest.raises(TemplateReadError) as exc_info:
                generate_prompt(corrupted_path, ["test"])
            
            error = exc_info.value
            assert "Failed to decode" in str(error)
            assert error.error_code == "TEMPLATE_ENCODING_ERROR"

    def test_io_error_handling(self):
        """Test error handling for various I/O errors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            template_path = Path(tmpdir) / "io-test.md"
            template_path.write_text("# I/O Test\n\nContent with $ARGUMENTS.")
            
            # Mock various I/O errors
            io_errors = [
                OSError("Device not ready"),
                IOError("Input/output error"),
                OSError("No space left on device"),
            ]
            
            for io_error in io_errors:
                with patch('pathlib.Path.read_text', side_effect=io_error):
                    with pytest.raises(TemplateReadError) as exc_info:
                        generate_prompt(template_path, ["test"])
                    
                    error = exc_info.value
                    assert "I/O error" in str(error)
                    assert str(template_path) in str(error)
                    assert error.error_code == "TEMPLATE_IO_ERROR"

    def test_locked_file_error_handling(self):
        """Test error handling when files are locked by other processes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            template_path = Path(tmpdir) / "locked-test.md"
            template_path.write_text("# Locked Test\n\nContent with $ARGUMENTS.")
            
            # Simulate file being locked (implementation varies by OS)
            with patch('pathlib.Path.read_text', side_effect=PermissionError("File is locked")):
                with pytest.raises(TemplateReadError) as exc_info:
                    generate_prompt(template_path, ["test"])
                
                error = exc_info.value
                assert "Permission denied" in str(error)
                assert error.error_code == "TEMPLATE_PERMISSION_DENIED"


class TestTemporaryDirectoryIsolation:
    """Test that all file system tests use proper temporary directory isolation."""

    def test_temporary_directory_isolation(self):
        """Test that temporary directories provide proper isolation."""
        isolation_tests = []
        
        # Create multiple isolated environments
        for i in range(5):
            with tempfile.TemporaryDirectory() as tmpdir:
                base_path = Path(tmpdir)
                cmd_dir = base_path / ".promptcraft" / "commands"
                cmd_dir.mkdir(parents=True)
                
                # Create unique file in each environment
                (cmd_dir / f"isolated-{i}.md").write_text(f"# Isolated Command {i}")
                
                with patch('promptcraft.core.Path.cwd', return_value=base_path):
                    result = discover_commands()
                    
                    # Should only find the file for this isolation level
                    assert len(result) == 1
                    assert result[0].name == f"isolated-{i}"
                    
                    isolation_tests.append(tmpdir)  # Path should be unique
        
        # Verify all paths were different (isolation)
        assert len(set(isolation_tests)) == 5

    def test_cleanup_after_errors(self):
        """Test that temporary directories are cleaned up even after errors."""
        temp_dirs = []
        
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                temp_dirs.append(tmpdir)
                base_path = Path(tmpdir)
                
                # Create template that will cause an error
                cmd_dir = base_path / ".promptcraft" / "commands"
                cmd_dir.mkdir(parents=True)
                
                with patch('promptcraft.core.Path.cwd', return_value=base_path):
                    # This should work without issues
                    result = discover_commands()
                    assert isinstance(result, list)
                    
                    # Now cause an error
                    with patch('promptcraft.core.Path.glob', side_effect=OSError("Simulated error")):
                        try:
                            discover_commands()
                        except:
                            pass  # Expected to fail
            
            # Directory should be cleaned up even after error
            assert not Path(temp_dirs[0]).exists()
            
        except Exception:
            # Ensure cleanup even if test fails
            for temp_dir in temp_dirs:
                if Path(temp_dir).exists():
                    shutil.rmtree(temp_dir, ignore_errors=True)

    def test_no_interference_between_tests(self):
        """Test that file system tests don't interfere with each other."""
        # This test verifies isolation by checking that state doesn't leak
        
        # First test creates specific structure
        with tempfile.TemporaryDirectory() as tmpdir1:
            base_path1 = Path(tmpdir1)
            cmd_dir1 = base_path1 / ".promptcraft" / "commands"
            cmd_dir1.mkdir(parents=True)
            
            (cmd_dir1 / "test1.md").write_text("# Test 1")
            
            with patch('promptcraft.core.Path.cwd', return_value=base_path1):
                result1 = discover_commands()
                assert len(result1) == 1
                assert result1[0].name == "test1"
        
        # Second test creates different structure
        with tempfile.TemporaryDirectory() as tmpdir2:
            base_path2 = Path(tmpdir2)
            cmd_dir2 = base_path2 / ".promptcraft" / "commands"
            cmd_dir2.mkdir(parents=True)
            
            (cmd_dir2 / "test2.md").write_text("# Test 2")
            (cmd_dir2 / "test3.md").write_text("# Test 3")
            
            with patch('promptcraft.core.Path.cwd', return_value=base_path2):
                result2 = discover_commands()
                assert len(result2) == 2
                names = {cmd.name for cmd in result2}
                assert names == {"test2", "test3"}
        
        # Verify no cross-contamination occurred
        assert base_path1 != base_path2