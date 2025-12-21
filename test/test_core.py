"""Tests for the embgen core module and domain system."""

import tempfile
from pathlib import Path

import pytest
import yaml

from embgen.core import parse_yaml, parse_and_render, ensure_output_dir
from embgen.domains import (
    BaseConfig,
    DomainGenerator,
    discover_domains,
)
from embgen.templates import file_type, get_env


class TestParseYaml:
    """Test YAML parsing functionality."""

    def test_parse_valid_yaml(self):
        """Test parsing a valid YAML file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump({"name": "Test", "value": 42}, f)
            f.flush()

            data = parse_yaml(Path(f.name))
            assert data["name"] == "Test"
            assert data["value"] == 42

    def test_parse_yaml_with_lists(self):
        """Test parsing YAML with lists."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump({"items": [1, 2, 3], "nested": {"a": 1}}, f)
            f.flush()

            data = parse_yaml(Path(f.name))
            assert data["items"] == [1, 2, 3]
            assert data["nested"]["a"] == 1

    def test_parse_nonexistent_file(self):
        """Test that parsing nonexistent file raises error."""
        with pytest.raises(FileNotFoundError):
            parse_yaml(Path("/nonexistent/file.yml"))


class TestEnsureOutputDir:
    """Test output directory creation."""

    def test_creates_directory(self):
        """Test that output directory is created when parent exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "new_dir"
            result = ensure_output_dir(output_dir)
            assert result.exists()
            assert result.is_dir()

    def test_existing_directory(self):
        """Test that existing directory is handled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            ensure_output_dir(output_dir)  # Should not raise
            assert output_dir.exists()

    def test_raises_if_parent_missing(self):
        """Test that error is raised if parent directory doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "nonexistent" / "nested" / "dir"
            with pytest.raises(FileNotFoundError):
                ensure_output_dir(output_dir)


class TestFileType:
    """Test file type descriptions."""

    def test_known_types(self):
        assert file_type("h") == "C Header"
        assert file_type("py") == "Python"
        assert file_type("md") == "Markdown"
        assert file_type("json") == "JSON"
        assert file_type("yml") == "YAML"

    def test_unknown_type(self):
        """Test unknown file type returns 'Unknown'."""
        result = file_type("xyz")
        assert result == "Unknown"


class TestTemplateEnv:
    """Test Jinja2 template environment."""

    def test_get_env(self):
        """Test creating a template environment."""
        with tempfile.TemporaryDirectory() as tmpdir:
            templates_dir = Path(tmpdir)
            (templates_dir / "test.j2").write_text("Hello {{ name }}!")

            env = get_env(templates_dir)
            template = env.get_template("test.j2")
            result = template.render(name="World")
            assert result == "Hello World!"


class TestBaseConfig:
    """Test BaseConfig base class."""

    def test_basic_config(self):
        """Test basic config creation."""
        cfg = BaseConfig(name="Test")
        assert cfg.name == "Test"
        assert cfg.file is None

    def test_config_with_file(self):
        """Test config with explicit file."""
        cfg = BaseConfig(name="Test", file="custom")
        assert cfg.file == "custom"

    def test_output_filename_default(self):
        """Test output_filename defaults to lowercase name."""
        cfg = BaseConfig(name="TestConfig")
        assert cfg.output_filename == "testconfig"

    def test_output_filename_explicit(self):
        """Test output_filename uses explicit file."""
        cfg = BaseConfig(name="TestConfig", file="custom_output")
        assert cfg.output_filename == "custom_output"


class TestDomainGeneratorInterface:
    """Test the DomainGenerator abstract interface."""

    def test_builtin_domains_implement_interface(self):
        """Test that builtin domains implement all required methods."""
        domains = discover_domains()

        for name, generator in domains.items():
            # Check properties
            assert isinstance(generator.name, str)
            assert len(generator.name) > 0
            assert isinstance(generator.description, str)
            assert len(generator.description) > 0

            # Check templates path exists
            assert generator.templates_path.exists()
            assert generator.templates_path.is_dir()

    def test_detect_returns_bool(self):
        """Test that detect returns boolean."""
        domains = discover_domains()
        for generator in domains.values():
            result = generator.detect({"name": "Test"})
            assert isinstance(result, bool)


class TestParseAndRender:
    """Test the parse_and_render function."""

    @pytest.fixture
    def commands_config(self) -> Path:
        return Path(__file__).parent / "configs" / "commands" / "tinyprobe.yml"

    @pytest.fixture
    def registers_config(self) -> Path:
        return Path(__file__).parent / "configs" / "registers" / "simple.yml"

    def test_parse_and_render_commands(self, commands_config: Path):
        """Test full pipeline for commands."""
        domains = discover_domains()
        generator = domains["commands"]

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir)
            templates = {"h": "template.h.j2"}

            filenames = parse_and_render(
                generator, commands_config, output_path, templates
            )

            assert len(filenames) >= 1
            assert any("tinyprobecommands" in f for f in filenames)

    def test_parse_and_render_registers(self, registers_config: Path):
        """Test full pipeline for registers."""
        domains = discover_domains()
        generator = domains["registers"]

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir)
            templates = {"h": "template.h.j2"}

            filenames = parse_and_render(
                generator, registers_config, output_path, templates
            )

            assert len(filenames) >= 1
            assert any("simple" in f for f in filenames)

    def test_parse_and_render_creates_output_dir(self, commands_config: Path):
        """Test that output directory is created if parent exists."""
        domains = discover_domains()
        generator = domains["commands"]

        with tempfile.TemporaryDirectory() as tmpdir:
            # Parent exists, but "output" subdir doesn't
            output_path = Path(tmpdir) / "output"
            templates = {"h": "template.h.j2"}

            parse_and_render(generator, commands_config, output_path, templates)

            assert output_path.exists()


class TestDomainDiscoveryMechanism:
    """Test the domain discovery mechanism in detail."""

    def test_discover_returns_dict(self):
        """Test that discover_domains returns a dict."""
        domains = discover_domains()
        assert isinstance(domains, dict)

    def test_discover_keys_are_strings(self):
        """Test that domain keys are strings."""
        domains = discover_domains()
        for key in domains.keys():
            assert isinstance(key, str)

    def test_discover_values_are_generators(self):
        """Test that domain values are DomainGenerator instances."""
        domains = discover_domains()
        for generator in domains.values():
            assert isinstance(generator, DomainGenerator)

    def test_domain_names_match_keys(self):
        """Test that generator.name matches its key in the dict."""
        domains = discover_domains()
        for key, generator in domains.items():
            assert generator.name == key


class TestUserDomainsOverride:
    """Test that user domains can override builtin domains."""

    def test_user_domain_overrides_builtin(self):
        """Test that a user domain with same name overrides builtin."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a "commands" domain that overrides the builtin
            domain_dir = Path(tmpdir) / "commands"
            domain_dir.mkdir()
            (domain_dir / "__init__.py").write_text(
                """
from embgen.domains import DomainGenerator, BaseConfig
from typing import Any
from jinja2 import Template
from pathlib import Path

class CustomCommandsGenerator(DomainGenerator):
    @property
    def name(self): return "commands"
    @property
    def description(self): return "Custom commands - overridden"
    def detect(self, data): return False  # Different behavior
    def validate(self, data): return BaseConfig.model_validate(data)
    def render(self, config, template): return "custom"
    @property
    def templates_path(self): return Path(__file__).parent / "templates"

generator = CustomCommandsGenerator()
"""
            )
            (domain_dir / "templates").mkdir()

            domains = discover_domains(tmpdir)
            assert domains["commands"].description == "Custom commands - overridden"
            # User domain's detect should return False
            assert domains["commands"].detect({"commands": []}) is False
