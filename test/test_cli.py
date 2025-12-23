"""Thorough tests for the embgen CLI."""

import os
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from embgen.scaffold import scaffold_domain
from embgen.discovery import (
    discover_domains,
    detect_domain,
    BUILTIN_DOMAINS_PATH,
    EMBGEN_DOMAINS_DIR_ENV,
)
from embgen.templates import discover_templates
from embgen.domains.commands.generator import CommandsGenerator


class TestDiscoverDomains:
    """Test domain discovery functionality."""

    def test_discover_builtin_domains(self):
        """Test that built-in domains are discovered."""
        domains = discover_domains()
        assert "commands" in domains
        assert "registers" in domains

    def test_discover_with_none_extra_dir(self):
        """Test discovery with None as extra directory."""
        domains = discover_domains(None)
        assert "commands" in domains
        assert "registers" in domains

    def test_discover_with_nonexistent_extra_dir(self):
        """Test discovery with non-existent extra directory."""
        domains = discover_domains("/nonexistent/path/to/domains")
        # Should still have built-in domains
        assert "commands" in domains
        assert "registers" in domains

    def test_discover_with_env_var(self):
        """Test discovery using environment variable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a minimal domain
            domain_dir = Path(tmpdir) / "envtest"
            domain_dir.mkdir()
            (domain_dir / "__init__.py").write_text(
                """
from embgen.domains import DomainGenerator, BaseConfig
from typing import Any
from jinja2 import Template

class EnvTestGenerator(DomainGenerator):
    @property
    def name(self): return "envtest"
    @property
    def description(self): return "Env test"
    def detect(self, data): return "envtest" in data
    def validate(self, data): return BaseConfig.model_validate(data)
    def render(self, config, template): return ""

generator = EnvTestGenerator()
"""
            )

            with patch.dict(os.environ, {EMBGEN_DOMAINS_DIR_ENV: tmpdir}):
                domains = discover_domains()
                assert "envtest" in domains


class TestDetectDomain:
    """Test domain auto-detection."""

    def test_detect_commands(self):
        """Test detection of commands domain."""
        data = {"name": "Test", "commands": []}
        generator = detect_domain(data)
        assert generator is not None
        assert generator.name == "commands"

    def test_detect_registers(self):
        """Test detection of registers domain."""
        data = {"name": "Test", "regmap": []}
        generator = detect_domain(data)
        assert generator is not None
        assert generator.name == "registers"

    def test_detect_unknown_returns_none(self):
        """Test that unknown data returns None."""
        data = {"name": "Test", "unknown_key": []}
        generator = detect_domain(data)
        assert generator is None

    def test_detect_empty_data(self):
        """Test detection with empty data."""
        generator = detect_domain({})
        assert generator is None


class TestDiscoverTemplates:
    """Test template discovery."""

    def test_commands_templates(self):
        """Test that commands templates are discovered."""
        generator = CommandsGenerator()
        single_templates, multifile_groups = discover_templates(
            generator.templates_path
        )

        assert "h" in single_templates
        assert "py" in single_templates
        assert "md" in single_templates

    def test_template_format(self):
        """Test template info format."""
        generator = CommandsGenerator()
        single_templates, multifile_groups = discover_templates(
            generator.templates_path
        )

        for ext, (desc, filename) in single_templates.items():
            assert isinstance(desc, str)
            assert filename.endswith((".j2", ".jinja"))


class TestScaffoldDomain:
    """Test domain scaffolding."""

    def test_scaffold_creates_files(self):
        """Test that scaffold creates all required files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            location = Path(tmpdir)
            created = scaffold_domain("testdomain", location)

            assert len(created) == 6  # __init__, models, generator, 3 templates

            domain_dir = location / "testdomain"
            assert (domain_dir / "__init__.py").exists()
            assert (domain_dir / "models.py").exists()
            assert (domain_dir / "generator.py").exists()
            assert (domain_dir / "templates" / "template.h.j2").exists()
            assert (domain_dir / "templates" / "template.py.j2").exists()
            assert (domain_dir / "templates" / "template.md.j2").exists()

    def test_scaffold_init_content(self):
        """Test that __init__.py has correct content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            location = Path(tmpdir)
            scaffold_domain("mydom", location)

            init_content = (location / "mydom" / "__init__.py").read_text()
            assert "MydomGenerator" in init_content
            assert "generator = MydomGenerator()" in init_content

    def test_scaffold_generator_content(self):
        """Test that generator.py has correct content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            location = Path(tmpdir)
            scaffold_domain("mydom", location)

            gen_content = (location / "mydom" / "generator.py").read_text()
            assert "class MydomGenerator(DomainGenerator)" in gen_content
            assert 'return "mydom"' in gen_content

    def test_scaffold_is_loadable(self):
        """Test that scaffolded domain can be loaded."""
        with tempfile.TemporaryDirectory() as tmpdir:
            location = Path(tmpdir)
            scaffold_domain("loadtest", location)

            domains = discover_domains(location)
            assert "loadtest" in domains

    def test_scaffold_name_normalization(self):
        """Test that names with spaces/hyphens are normalized."""
        with tempfile.TemporaryDirectory() as tmpdir:
            location = Path(tmpdir)
            # Note: The main function normalizes the name, not scaffold_domain
            # But scaffold_domain should handle the normalized name correctly
            scaffold_domain("my_domain", location)

            assert (location / "my_domain").exists()


class TestCLIHelp:
    """Test CLI help output."""

    def test_main_help(self):
        """Test main help output."""
        result = subprocess.run(
            [sys.executable, "-m", "embgen", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )
        assert result.returncode == 0
        assert "embgen" in result.stdout
        assert "commands" in result.stdout
        assert "registers" in result.stdout
        assert "auto" in result.stdout
        assert "new" in result.stdout
        assert "--domains-dir" in result.stdout

    def test_commands_help(self):
        """Test commands subcommand help."""
        result = subprocess.run(
            [sys.executable, "-m", "embgen", "commands", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )
        assert result.returncode == 0
        assert "input" in result.stdout.lower()
        assert "--output" in result.stdout
        assert "--h" in result.stdout or "-c" in result.stdout  # C header flag

    def test_registers_help(self):
        """Test registers subcommand help."""
        result = subprocess.run(
            [sys.executable, "-m", "embgen", "registers", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )
        assert result.returncode == 0
        assert "input" in result.stdout.lower()
        assert "--output" in result.stdout

    def test_new_help(self):
        """Test new subcommand help."""
        result = subprocess.run(
            [sys.executable, "-m", "embgen", "new", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )
        assert result.returncode == 0
        assert "name" in result.stdout.lower()
        assert "--builtin" in result.stdout
        assert "--location" in result.stdout

    def test_auto_help(self):
        """Test auto subcommand help."""
        result = subprocess.run(
            [sys.executable, "-m", "embgen", "auto", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )
        assert result.returncode == 0
        assert "input" in result.stdout.lower()


class TestCLIGeneration:
    """Test CLI generation commands."""

    @pytest.fixture
    def commands_config(self) -> Path:
        return Path(__file__).parent / "configs" / "commands" / "tinyprobe.yml"

    @pytest.fixture
    def registers_config(self) -> Path:
        return Path(__file__).parent / "configs" / "registers" / "simple.yml"

    def test_generate_commands_header(self, commands_config: Path):
        """Test generating commands header via CLI."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "embgen",
                    "commands",
                    str(commands_config),
                    "-o",
                    tmpdir,
                    "--h",
                ],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent,
            )
            assert result.returncode == 0
            assert (Path(tmpdir) / "commands.h").exists()

    def test_generate_registers_header(self, registers_config: Path):
        """Test generating registers header via CLI."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "embgen",
                    "registers",
                    str(registers_config),
                    "-o",
                    tmpdir,
                    "--h",
                ],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent,
            )
            assert result.returncode == 0
            assert (Path(tmpdir) / "simple.h").exists()

    def test_generate_multiple_formats(self, commands_config: Path):
        """Test generating multiple formats at once."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "embgen",
                    "commands",
                    str(commands_config),
                    "-o",
                    tmpdir,
                    "--h",
                    "--py",
                    "--md",
                ],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent,
            )
            assert result.returncode == 0
            assert (Path(tmpdir) / "commands.h").exists()
            assert (Path(tmpdir) / "commands.py").exists()
            assert (Path(tmpdir) / "commands.md").exists()
            assert (Path(tmpdir) / "commands_base.py").exists()

    def test_auto_detect_commands(self, commands_config: Path):
        """Test auto-detection with commands config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "embgen",
                    "auto",
                    str(commands_config),
                    "-o",
                    tmpdir,
                    "--h",
                ],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent,
            )
            assert result.returncode == 0
            # Output can be in stdout or stderr depending on logging config
            combined = result.stdout + result.stderr
            assert "auto-detected" in combined.lower() or "commands" in combined.lower()

    def test_auto_detect_registers(self, registers_config: Path):
        """Test auto-detection with registers config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "embgen",
                    "auto",
                    str(registers_config),
                    "-o",
                    tmpdir,
                    "--h",
                ],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent,
            )
            assert result.returncode == 0
            combined = result.stdout + result.stderr
            assert "registers" in combined.lower()

    def test_debug_flag(self, commands_config: Path):
        """Test debug flag enables detailed output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "embgen",
                    "-d",
                    "commands",
                    str(commands_config),
                    "-o",
                    tmpdir,
                    "--h",
                ],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent,
            )
            assert result.returncode == 0
            # Debug mode should show timing info
            combined = result.stdout + result.stderr
            assert "done after" in combined.lower() or "debug" in combined.lower()


class TestCLIErrorHandling:
    """Test CLI error handling."""

    def test_no_subcommand_shows_help(self):
        """Test that running without subcommand shows help."""
        result = subprocess.run(
            [sys.executable, "-m", "embgen"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )
        assert result.returncode == 1
        assert "usage:" in result.stdout.lower() or "embgen" in result.stdout

    def test_missing_input_file(self):
        """Test error when input file is missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "embgen",
                    "commands",
                    "/nonexistent/file.yml",
                    "-o",
                    tmpdir,
                    "--h",
                ],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent,
            )
            assert result.returncode == 1
            combined = result.stdout + result.stderr
            assert "error" in combined.lower() or "failed" in combined.lower()

    def test_no_output_format_specified(self):
        """Test error when no output format is specified."""
        config = Path(__file__).parent / "configs" / "commands" / "tinyprobe.yml"
        with tempfile.TemporaryDirectory() as tmpdir:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "embgen",
                    "commands",
                    str(config),
                    "-o",
                    tmpdir,
                ],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent,
            )
            assert result.returncode == 1
            combined = result.stdout + result.stderr
            assert "no output formats" in combined.lower()

    def test_auto_detect_fails_on_unknown(self):
        """Test error when auto-detect fails."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a YAML file with unknown structure
            unknown_yaml = Path(tmpdir) / "unknown.yml"
            unknown_yaml.write_text("name: Test\nunknown_key: value\n")

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "embgen",
                    "auto",
                    str(unknown_yaml),
                    "-o",
                    tmpdir,
                    "--h",
                ],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent,
            )
            assert result.returncode == 1
            combined = result.stdout + result.stderr
            assert "could not auto-detect" in combined.lower()

    def test_invalid_yaml(self):
        """Test error with invalid YAML file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            invalid_yaml = Path(tmpdir) / "invalid.yml"
            invalid_yaml.write_text("name: [unclosed bracket\n")

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "embgen",
                    "commands",
                    str(invalid_yaml),
                    "-o",
                    tmpdir,
                    "--h",
                ],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent,
            )
            assert result.returncode == 1


class TestCLINewSubcommand:
    """Test CLI 'new' subcommand."""

    def test_new_creates_domain(self):
        """Test that 'new' creates a domain."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "embgen",
                    "new",
                    "testdom",
                    "--location",
                    tmpdir,
                ],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent,
            )
            assert result.returncode == 0
            assert (Path(tmpdir) / "testdom" / "__init__.py").exists()
            assert (Path(tmpdir) / "testdom" / "models.py").exists()
            assert (Path(tmpdir) / "testdom" / "generator.py").exists()

    def test_new_domain_is_discoverable(self):
        """Test that newly created domain can be discovered."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "embgen",
                    "new",
                    "discovertest",
                    "--location",
                    tmpdir,
                ],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent,
            )

            # Check that it appears in help with --domains-dir
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "embgen",
                    "--domains-dir",
                    tmpdir,
                    "--help",
                ],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent,
            )
            assert "discovertest" in result.stdout

    def test_new_fails_if_exists(self):
        """Test that 'new' fails if domain already exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create domain first time
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "embgen",
                    "new",
                    "existstest",
                    "--location",
                    tmpdir,
                ],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent,
            )

            # Try to create again
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "embgen",
                    "new",
                    "existstest",
                    "--location",
                    tmpdir,
                ],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent,
            )
            assert result.returncode == 1
            combined = result.stdout + result.stderr
            assert "already exists" in combined.lower()

    def test_new_normalizes_name(self):
        """Test that 'new' normalizes domain names."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "embgen",
                    "new",
                    "My-Domain-Name",
                    "--location",
                    tmpdir,
                ],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent,
            )
            assert result.returncode == 0
            assert (Path(tmpdir) / "my_domain_name").exists()


class TestCLIDomainsDir:
    """Test CLI --domains-dir option."""

    def test_domains_dir_option(self):
        """Test that --domains-dir loads additional domains."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a custom domain
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "embgen",
                    "new",
                    "customdom",
                    "--location",
                    tmpdir,
                ],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent,
            )

            # Verify it's available
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "embgen",
                    "--domains-dir",
                    tmpdir,
                    "--help",
                ],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent,
            )
            assert "customdom" in result.stdout

    def test_user_domain_can_generate(self):
        """Test that user domain can generate output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            domains_dir = Path(tmpdir) / "domains"
            domains_dir.mkdir()

            # Create a custom domain
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "embgen",
                    "new",
                    "mydom",
                    "--location",
                    str(domains_dir),
                ],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent,
            )

            # Create a YAML file for this domain
            config_file = Path(tmpdir) / "test.yml"
            config_file.write_text("name: TestConfig\nmydom: true\n")

            output_dir = Path(tmpdir) / "output"
            output_dir.mkdir()

            # Generate using the custom domain
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "embgen",
                    "--domains-dir",
                    str(domains_dir),
                    "mydom",
                    str(config_file),
                    "-o",
                    str(output_dir),
                    "--h",
                ],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent,
            )
            assert result.returncode == 0
            assert (output_dir / "testconfig.h").exists()


class TestBuiltinDomainsPath:
    """Test BUILTIN_DOMAINS_PATH constant."""

    def test_is_valid_path(self):
        """Test that it is a valid path."""
        assert BUILTIN_DOMAINS_PATH.exists()
        assert BUILTIN_DOMAINS_PATH.is_dir()

    def test_contains_builtin_domains(self):
        """Test that path contains builtin domains."""
        assert (BUILTIN_DOMAINS_PATH / "commands").exists()
        assert (BUILTIN_DOMAINS_PATH / "registers").exists()
