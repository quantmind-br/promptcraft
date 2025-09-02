"""Comprehensive tests for template discovery functionality."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock

import pytest
from promptcraft.core import discover_commands, _extract_description, CommandInfo
from promptcraft.exceptions import PromptCraftError


class TestTemplateDiscoveryComprehensive:
    """Comprehensive tests for template discovery functionality."""

    def test_discover_commands_empty_search_paths(self):
        """Test command discovery when search paths don't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Use directories that don't have .promptcraft folders
            empty_cwd = Path(tmpdir) / "empty_cwd"
            empty_cwd.mkdir()
            empty_home = Path(tmpdir) / "empty_home"
            empty_home.mkdir()
            
            with patch('promptcraft.core.Path.cwd', return_value=empty_cwd), \
                 patch('promptcraft.core.Path.home', return_value=empty_home):
                
                result = discover_commands()
                assert result == []

    def test_discover_commands_partial_search_paths(self):
        """Test command discovery when only some search paths exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create only home directory structure
            home_dir = Path(tmpdir) / "home"
            home_cmd_dir = home_dir / ".promptcraft" / "commands"
            home_cmd_dir.mkdir(parents=True)
            
            (home_cmd_dir / "global-only.md").write_text("# Global Only\n\nGlobal command.")
            
            # Use non-existent current directory
            fake_cwd = Path(tmpdir) / "nonexistent"
            
            with patch('promptcraft.core.Path.cwd', return_value=fake_cwd), \
                 patch('promptcraft.core.Path.home', return_value=home_dir):
                
                result = discover_commands()
                
                assert len(result) == 1
                assert result[0].name == "global-only"
                assert result[0].source == "Global"

    def test_discover_commands_with_duplicate_names(self):
        """Test command discovery when same command exists in both locations."""
        with tempfile.TemporaryDirectory() as cwd_tmpdir, \
             tempfile.TemporaryDirectory() as home_tmpdir:
            
            # Create both directory structures
            cwd_cmd_dir = Path(cwd_tmpdir) / ".promptcraft" / "commands"
            cwd_cmd_dir.mkdir(parents=True)
            home_cmd_dir = Path(home_tmpdir) / ".promptcraft" / "commands"
            home_cmd_dir.mkdir(parents=True)
            
            # Create same command in both locations
            (cwd_cmd_dir / "duplicate.md").write_text("# Local Duplicate\n\nLocal version.")
            (home_cmd_dir / "duplicate.md").write_text("# Global Duplicate\n\nGlobal version.")
            
            # Create unique commands too
            (cwd_cmd_dir / "local-only.md").write_text("# Local Only\n\nLocal command.")
            (home_cmd_dir / "global-only.md").write_text("# Global Only\n\nGlobal command.")
            
            with patch('promptcraft.core.Path.cwd', return_value=Path(cwd_tmpdir)), \
                 patch('promptcraft.core.Path.home', return_value=Path(home_tmpdir)):
                
                result = discover_commands()
                
                # Should find all 4 commands (both duplicates + unique ones)
                assert len(result) == 4
                
                # Find the duplicate commands
                duplicate_commands = [cmd for cmd in result if cmd.name == "duplicate"]
                assert len(duplicate_commands) == 2
                
                # Should have both sources represented
                sources = {cmd.source for cmd in duplicate_commands}
                assert sources == {"Project", "Global"}

    def test_discover_commands_with_broken_template_files(self):
        """Test command discovery with some broken template files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cmd_dir = Path(tmpdir) / ".promptcraft" / "commands"
            cmd_dir.mkdir(parents=True)
            
            # Create valid templates
            (cmd_dir / "valid1.md").write_text("# Valid Command 1\n\nValid.")
            (cmd_dir / "valid2.md").write_text("# Valid Command 2\n\nValid.")
            
            # Create files that might cause issues
            (cmd_dir / "empty.md").write_text("")
            (cmd_dir / "whitespace-only.md").write_text("   \n\t\n   ")
            
            # Create binary file with .md extension
            try:
                (cmd_dir / "binary.md").write_bytes(b'\x00\x01\x02\x03\xff\xfe')
            except:
                pass  # Skip if can't create binary file
            
            with patch('promptcraft.core.Path.cwd', return_value=Path(tmpdir)), \
                 patch('promptcraft.core.Path.home', return_value=Path("/fake/home")):
                
                result = discover_commands()
                
                # Should find valid commands despite broken ones
                valid_commands = [cmd for cmd in result if cmd.name.startswith('valid')]
                assert len(valid_commands) >= 2
                
                # Broken files should still be discovered (just with "No description available")
                total_md_files = len([f for f in cmd_dir.glob("*.md") if f.is_file()])
                assert len(result) == total_md_files

    def test_discover_commands_performance_with_many_files(self):
        """Test command discovery performance with many template files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cmd_dir = Path(tmpdir) / ".promptcraft" / "commands"
            cmd_dir.mkdir(parents=True)
            
            # Create many template files
            for i in range(100):
                (cmd_dir / f"cmd{i:03d}.md").write_text(f"# Command {i}\n\nCommand {i} description.")
            
            with patch('promptcraft.core.Path.cwd', return_value=Path(tmpdir)), \
                 patch('promptcraft.core.Path.home', return_value=Path("/fake/home")):
                
                import time
                start_time = time.time()
                result = discover_commands()
                end_time = time.time()
                
                # Should find all commands
                assert len(result) == 100
                
                # Should complete reasonably quickly (< 1 second)
                assert (end_time - start_time) < 1.0
                
                # Should be sorted correctly
                assert result[0].name == "cmd000"
                assert result[-1].name == "cmd099"


class TestDescriptionExtraction:
    """Comprehensive tests for description extraction functionality."""

    def test_extract_description_with_various_header_formats(self):
        """Test description extraction with various markdown header formats."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_cases = [
                ("# Simple Header", "Simple Header"),
                ("## Double Hash", "Double Hash"),
                ("### Triple Hash", "Triple Hash"),
                ("#### Quad Hash", "Quad Hash"),
                ("##### Penta Hash", "Penta Hash"),
                ("###### Hexa Hash", "Hexa Hash"),
                ("####### Too Many", "###### Too Many"),  # Only strip up to 6 #s
            ]
            
            for i, (content, expected) in enumerate(test_cases):
                test_file = Path(tmpdir) / f"test{i}.md"
                test_file.write_text(f"{content}\n\nContent here.")
                
                result = _extract_description(test_file)
                assert result == expected

    def test_extract_description_with_mixed_content(self):
        """Test description extraction with various content before first header."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_cases = [
                ("\n\n# After Empty Lines", "After Empty Lines"),
                ("Plain text first line\n# Then Header", "Plain text first line"),
                ("   Leading spaces   \n# Header", "Leading spaces"),
                ("<!-- HTML Comment -->\n# Header", "<!-- HTML Comment -->"),
                ("---\ntitle: YAML Frontmatter\n---\n# Header", "---"),
            ]
            
            for i, (content, expected) in enumerate(test_cases):
                test_file = Path(tmpdir) / f"mixed{i}.md"
                test_file.write_text(content)
                
                result = _extract_description(test_file)
                assert result == expected

    def test_extract_description_with_inline_markdown(self):
        """Test description extraction preserves inline markdown."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_cases = [
                ("# **Bold** Header", "**Bold** Header"),
                ("# *Italic* Header", "*Italic* Header"),
                ("# `Code` in Header", "`Code` in Header"),
                ("# [Link](url) Header", "[Link](url) Header"),
                ("# Header with ![Image](url)", "Header with ![Image](url)"),
                ("# Complex **bold** and *italic* with `code`", "Complex **bold** and *italic* with `code`"),
            ]
            
            for i, (content, expected) in enumerate(test_cases):
                test_file = Path(tmpdir) / f"inline{i}.md"
                test_file.write_text(f"{content}\n\nContent.")
                
                result = _extract_description(test_file)
                assert result == expected

    def test_extract_description_edge_cases(self):
        """Test description extraction with edge cases."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Very long header
            long_header = "# " + "Very " * 100 + "Long Header"
            long_file = Path(tmpdir) / "long.md"
            long_file.write_text(f"{long_header}\n\nContent.")
            
            result = _extract_description(long_file)
            assert result.startswith("Very Very Very")
            assert len(result) > 400  # Should preserve full length
            
            # Header with special Unicode characters
            unicode_file = Path(tmpdir) / "unicode.md"
            unicode_file.write_text("# \u6f22\u5b57 with \u00e9m\u00f4j\u00ee\ud83d\ude0a\n\nContent.")
            
            result = _extract_description(unicode_file)
            assert result == "\u6f22\u5b57 with \u00e9m\u00f4j\u00ee\ud83d\ude0a"

    def test_extract_description_error_recovery(self):
        """Test description extraction error recovery."""
        # Test with permission error
        with patch('builtins.open', side_effect=PermissionError("Access denied")):
            result = _extract_description(Path("/fake/permission.md"))
            assert result == "No description available"
        
        # Test with I/O error
        with patch('builtins.open', side_effect=OSError("I/O error")):
            result = _extract_description(Path("/fake/io-error.md"))
            assert result == "No description available"
        
        # Test with Unicode error
        with patch('builtins.open', side_effect=UnicodeDecodeError("utf-8", b"", 0, 1, "Invalid")):
            result = _extract_description(Path("/fake/unicode-error.md"))
            assert result == "No description available"


class TestTemplateDiscoveryIntegration:
    """Integration tests for template discovery with file system."""

    def test_discovery_with_symlinks(self):
        """Test template discovery with symbolic links (Unix only)."""
        if os.name == 'nt':
            pytest.skip("Symlink test not applicable on Windows")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            cmd_dir = Path(tmpdir) / ".promptcraft" / "commands"
            cmd_dir.mkdir(parents=True)
            
            # Create actual template file
            actual_file = Path(tmpdir) / "actual.md"
            actual_file.write_text("# Actual Template\n\nActual content.")
            
            # Create symlink to it
            symlink_file = cmd_dir / "symlink.md"
            try:
                symlink_file.symlink_to(actual_file)
            except OSError:
                pytest.skip("Cannot create symlinks on this system")
            
            # Create regular file too
            (cmd_dir / "regular.md").write_text("# Regular Template\n\nRegular content.")
            
            with patch('promptcraft.core.Path.cwd', return_value=Path(tmpdir)), \
                 patch('promptcraft.core.Path.home', return_value=Path("/fake/home")):
                
                result = discover_commands()
                
                # Should find both regular and symlinked files
                assert len(result) >= 2
                names = {cmd.name for cmd in result}
                assert "regular" in names
                assert "symlink" in names

    def test_discovery_with_read_only_directories(self):
        """Test template discovery with read-only directories."""
        if os.name == 'nt':
            pytest.skip("Permission test not reliable on Windows")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            cmd_dir = Path(tmpdir) / ".promptcraft" / "commands"
            cmd_dir.mkdir(parents=True)
            
            # Create template file
            (cmd_dir / "readonly-test.md").write_text("# Read Only Test\n\nContent.")
            
            try:
                # Make directory read-only
                cmd_dir.chmod(0o444)
                
                with patch('promptcraft.core.Path.cwd', return_value=Path(tmpdir)), \
                     patch('promptcraft.core.Path.home', return_value=Path("/fake/home")):
                    
                    result = discover_commands()
                    
                    # Should still discover commands despite read-only directory
                    assert len(result) >= 1
                    assert result[0].name == "readonly-test"
            
            finally:
                # Restore permissions for cleanup
                try:
                    cmd_dir.chmod(0o755)
                except:
                    pass

    def test_discovery_with_concurrent_modifications(self):
        """Test template discovery while files are being modified."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cmd_dir = Path(tmpdir) / ".promptcraft" / "commands"
            cmd_dir.mkdir(parents=True)
            
            # Create initial files
            for i in range(5):
                (cmd_dir / f"initial{i}.md").write_text(f"# Initial {i}\n\nContent {i}.")
            
            with patch('promptcraft.core.Path.cwd', return_value=Path(tmpdir)), \
                 patch('promptcraft.core.Path.home', return_value=Path("/fake/home")):
                
                # Simulate concurrent modifications
                def modify_files():
                    # Add files during discovery
                    (cmd_dir / "concurrent.md").write_text("# Concurrent\n\nAdded during discovery.")
                    # Modify existing file
                    (cmd_dir / "initial0.md").write_text("# Modified Initial 0\n\nModified content.")
                
                # Run discovery with concurrent modifications
                import threading
                modify_thread = threading.Thread(target=modify_files)
                modify_thread.start()
                
                result = discover_commands()
                
                modify_thread.join()
                
                # Should complete successfully (exact results may vary due to timing)
                assert len(result) >= 5  # At least the initial files
                assert all(isinstance(cmd, CommandInfo) for cmd in result)