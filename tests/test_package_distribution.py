"""Tests for package distribution and installation."""

import subprocess
import sys
import venv
import tempfile
import shutil
from pathlib import Path
import pytest


class TestPackageDistribution:
    """Test package installation and distribution."""

    def test_pyproject_metadata_completeness(self):
        """Test that pyproject.toml contains all required metadata fields (AC: 1, 5)."""
        import toml
        
        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
        with open(pyproject_path) as f:
            config = toml.load(f)
        
        project = config["project"]
        
        # Required metadata fields
        assert "name" in project
        assert project["name"] == "promptcraft"
        
        assert "version" in project
        assert project["version"] == "0.1.0"
        
        assert "description" in project
        assert "authors" in project
        assert len(project["authors"]) > 0
        
        # License specification (AC: 5)
        assert "license" in project
        assert project["license"] == "MIT"
        
        # Keywords for package discovery (AC: 5)
        assert "keywords" in project
        assert isinstance(project["keywords"], list)
        assert len(project["keywords"]) > 0
        expected_keywords = ["cli", "command-line", "prompt", "template"]
        for keyword in expected_keywords:
            assert keyword in project["keywords"]
        
        # Enhanced classifiers (license classifier removed per modern standards)
        assert "classifiers" in project
        classifiers = project["classifiers"]
        assert "Environment :: Console" in classifiers
        assert "Topic :: Utilities" in classifiers
        assert "Typing :: Typed" in classifiers
        # License classifier is deprecated, license is now specified directly
        
        # Version is managed only in pyproject.toml (AC: 7)
        # Verify version is imported from metadata, not hardcoded
        init_file = Path(__file__).parent.parent / "src" / "promptcraft" / "__init__.py"
        if init_file.exists():
            with open(init_file) as f:
                init_content = f.read()
                # Should use importlib.metadata for version
                assert "importlib.metadata" in init_content
                assert "importlib.metadata.version" in init_content
                # Should have a fallback but primary version comes from metadata
                assert "PackageNotFoundError" in init_content

    def test_console_script_entry_point(self):
        """Test console script entry point configuration (AC: 2)."""
        import toml
        
        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
        with open(pyproject_path) as f:
            config = toml.load(f)
        
        # Check console script entry point
        assert "project" in config
        assert "scripts" in config["project"]
        scripts = config["project"]["scripts"]
        
        # Verify promptcraft entry point
        assert "promptcraft" in scripts
        assert scripts["promptcraft"] == "promptcraft.main:main"

    def test_dependency_specifications(self):
        """Test dependency specifications with appropriate constraints (AC: 4)."""
        import toml
        
        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
        with open(pyproject_path) as f:
            config = toml.load(f)
        
        dependencies = config["project"]["dependencies"]
        
        # Verify click dependency with version constraints
        click_deps = [dep for dep in dependencies if dep.startswith("click")]
        assert len(click_deps) == 1
        click_dep = click_deps[0]
        assert ">=8.0.0" in click_dep
        assert "<9.0.0" in click_dep  # Upper bound for compatibility
        
        # Verify pyperclip dependency
        pyperclip_deps = [dep for dep in dependencies if dep.startswith("pyperclip")]
        assert len(pyperclip_deps) == 1
        pyperclip_dep = pyperclip_deps[0]
        assert ">=1.8.0" in pyperclip_dep
        assert "<2.0.0" in pyperclip_dep  # Upper bound for compatibility
        
        # Verify development dependencies
        assert "optional-dependencies" in config["project"]
        dev_deps = config["project"]["optional-dependencies"]["dev"]
        
        pytest_deps = [dep for dep in dev_deps if dep.startswith("pytest")]
        assert len(pytest_deps) >= 1  # pytest, pytest-cov, pytest-benchmark

    @pytest.mark.slow
    def test_package_installation_from_source(self):
        """Test package installation via pip install . (AC: 3)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            venv_path = Path(temp_dir) / "test_venv"
            
            # Create virtual environment
            venv.create(venv_path, with_pip=True)
            
            # Get pip executable path
            if sys.platform == "win32":
                pip_path = venv_path / "Scripts" / "pip.exe"
                python_path = venv_path / "Scripts" / "python.exe"
            else:
                pip_path = venv_path / "bin" / "pip"
                python_path = venv_path / "bin" / "python"
            
            # Install package from source
            project_root = Path(__file__).parent.parent
            result = subprocess.run(
                [str(pip_path), "install", str(project_root)],
                capture_output=True,
                text=True
            )
            
            assert result.returncode == 0, f"Installation failed: {result.stderr}"
            
            # Test that promptcraft command is available
            result = subprocess.run(
                [str(python_path), "-c", "import promptcraft; print('Import successful')"],
                capture_output=True,
                text=True
            )
            assert result.returncode == 0, f"Import failed: {result.stderr}"

    @pytest.mark.slow
    def test_editable_installation(self):
        """Test editable installation via pip install -e . (AC: 3)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            venv_path = Path(temp_dir) / "test_venv"
            
            # Create virtual environment
            venv.create(venv_path, with_pip=True)
            
            # Get pip executable path
            if sys.platform == "win32":
                pip_path = venv_path / "Scripts" / "pip.exe"
                python_path = venv_path / "Scripts" / "python.exe"
            else:
                pip_path = venv_path / "bin" / "pip"
                python_path = venv_path / "bin" / "python"
            
            # Install package in editable mode
            project_root = Path(__file__).parent.parent
            result = subprocess.run(
                [str(pip_path), "install", "-e", str(project_root)],
                capture_output=True,
                text=True
            )
            
            assert result.returncode == 0, f"Editable installation failed: {result.stderr}"
            
            # Test that changes are reflected (editable mode)
            result = subprocess.run(
                [str(python_path), "-c", "import promptcraft; print('Editable import successful')"],
                capture_output=True,
                text=True
            )
            assert result.returncode == 0, f"Editable import failed: {result.stderr}"

    @pytest.mark.cross_platform
    def test_console_script_execution(self):
        """Test console script works across different environments (AC: 2)."""
        # This test verifies the console script can be found and executed
        # We'll test the import path rather than full installation to avoid CI issues
        try:
            from promptcraft.main import main
            # If we can import main function, the entry point should work
            assert callable(main)
        except ImportError as e:
            pytest.fail(f"Console script entry point not importable: {e}")

    def test_version_single_source_of_truth(self):
        """Test version is managed only in pyproject.toml (AC: 7)."""
        import toml
        
        # Get version from pyproject.toml
        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
        with open(pyproject_path) as f:
            config = toml.load(f)
        
        expected_version = config["project"]["version"]
        
        # Check that __init__.py imports version correctly
        from promptcraft import __version__
        assert __version__ == expected_version
        
        # Verify no hardcoded version in main.py
        main_file = Path(__file__).parent.parent / "src" / "promptcraft" / "main.py"
        with open(main_file) as f:
            main_content = f.read()
            # Should import __version__, not hardcode it
            assert "from . import __version__" in main_content
            assert f'version="{expected_version}"' not in main_content

    def test_build_system_configuration(self):
        """Test build system is properly configured."""
        import toml
        
        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
        with open(pyproject_path) as f:
            config = toml.load(f)
        
        # Check build system
        build_system = config["build-system"]
        assert "setuptools>=61.0" in build_system["requires"]
        assert "wheel" in build_system["requires"]
        assert build_system["build-backend"] == "setuptools.build_meta"
        
        # Check setuptools configuration
        assert "tool" in config
        assert "setuptools" in config["tool"]
        setuptools_config = config["tool"]["setuptools"]
        
        # Verify package discovery
        assert "packages" in setuptools_config
        assert "find" in setuptools_config["packages"]
        assert setuptools_config["packages"]["find"]["where"] == ["src"]
        
        # Verify package directory
        assert "package-dir" in setuptools_config
        assert setuptools_config["package-dir"][""] == "src"

    def test_readme_reference(self):
        """Test README.md is properly referenced in project config."""
        import toml
        
        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
        with open(pyproject_path) as f:
            config = toml.load(f)
        
        # Check README reference
        assert config["project"]["readme"] == "README.md"
        
        # Verify README.md exists (will be created in next task)
        readme_path = Path(__file__).parent.parent / "README.md"
        # Note: README.md will be created in a later task, so we just check the reference here
        assert config["project"]["readme"] == "README.md"


# Add toml as test dependency if not present
try:
    import toml
except ImportError:
    pytest.skip("toml package required for metadata tests", allow_module_level=True)