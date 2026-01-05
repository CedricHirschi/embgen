"""Tests for embgen main functionality."""

import tempfile
from pathlib import Path

import pytest

from embgen.discovery import discover_domains, detect_domain
from embgen.generator import CodeGenerator


class TestDomainDiscovery:
    """Test domain auto-discovery."""

    def test_discover_domains(self):
        """Test that domains are discovered."""
        domains = discover_domains()
        assert "commands" in domains
        assert "registers" in domains

    def test_detect_commands_domain(self):
        """Test auto-detection of commands domain."""
        data = {"name": "Test", "commands": []}
        generator = detect_domain(data)
        assert generator is not None
        assert generator.name == "commands"

    def test_detect_registers_domain(self):
        """Test auto-detection of registers domain."""
        data = {"name": "Test", "regmap": []}
        generator = detect_domain(data)
        assert generator is not None
        assert generator.name == "registers"

    def test_detect_unknown_domain(self):
        """Test that unknown data returns None."""
        data = {"name": "Test", "unknown_key": []}
        generator = detect_domain(data)
        assert generator is None


class TestCommandsGeneration:
    """Test commands domain generation."""

    @pytest.fixture
    def commands_config(self) -> Path:
        return Path(__file__).parent / "configs" / "commands" / "simple.yml"

    def test_parse_commands_yaml(self, commands_config: Path):
        """Test parsing commands YAML."""
        domains = discover_domains()
        generator = domains["commands"]
        code_gen = CodeGenerator(generator, Path.cwd())
        data = code_gen.parse_yaml(commands_config)
        assert "name" in data
        assert "commands" in data
        assert data["name"] == "Simple"

    def test_validate_commands(self, commands_config: Path):
        """Test validating commands config."""
        from embgen.domains.commands.models import CommandsConfig

        domains = discover_domains()
        generator = domains["commands"]
        code_gen = CodeGenerator(generator, Path.cwd())
        data = code_gen.parse_yaml(commands_config)
        config = generator.validate(data)
        assert isinstance(config, CommandsConfig)
        assert config.name == "Simple"
        assert len(config.commands) == 11

    def test_generate_commands(self, commands_config: Path):
        """Test generating commands outputs."""
        domains = discover_domains()
        generator = domains["commands"]

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir)
            # Include Python to test that commands_base.py is copied
            templates = {
                "h": "template.h.j2",
                "md": "template.md.j2",
                "py": "template.py.j2",
            }

            code_gen = CodeGenerator(generator, output_path)
            filenames = code_gen.generate_from_file(commands_config, templates)

            assert "commands.h" in filenames
            assert "commands.md" in filenames
            assert "commands.py" in filenames
            assert "commands_base.py" in filenames  # Only copied when py is generated

            # Check files exist
            assert (output_path / "commands.h").exists()
            assert (output_path / "commands.md").exists()
            assert (output_path / "commands.py").exists()
            assert (output_path / "commands_base.py").exists()

    def test_generate_commands_no_python(self, commands_config: Path):
        """Test that commands_base.py is NOT copied when Python is not generated."""
        domains = discover_domains()
        generator = domains["commands"]

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir)
            templates = {"h": "template.h.j2", "md": "template.md.j2"}

            code_gen = CodeGenerator(generator, output_path)
            filenames = code_gen.generate_from_file(commands_config, templates)

            assert "commands.h" in filenames
            assert "commands.md" in filenames
            assert "commands_base.py" not in filenames

            # Check files exist
            assert (output_path / "commands.h").exists()
            assert (output_path / "commands.md").exists()
            assert not (output_path / "commands_base.py").exists()


class TestRegistersGeneration:
    """Test registers domain generation."""

    @pytest.fixture
    def registers_config(self) -> Path:
        return Path(__file__).parent / "configs" / "registers" / "simple.yml"

    def test_parse_registers_yaml(self, registers_config: Path):
        """Test parsing registers YAML."""
        domains = discover_domains()
        generator = domains["registers"]
        code_gen = CodeGenerator(generator, Path.cwd())
        data = code_gen.parse_yaml(registers_config)
        assert "name" in data
        assert "regmap" in data
        assert data["name"] == "SimpleRegmap"

    def test_validate_registers(self, registers_config: Path):
        """Test validating registers config."""
        from embgen.domains.registers.models import RegistersConfig

        domains = discover_domains()
        generator = domains["registers"]
        code_gen = CodeGenerator(generator, Path.cwd())
        data = code_gen.parse_yaml(registers_config)
        config = generator.validate(data)
        assert isinstance(config, RegistersConfig)
        assert config.name == "SimpleRegmap"
        assert len(config.regmap) == 4  # CONTROL, STATUS, DATA, CONFIG

    def test_generate_registers(self, registers_config: Path):
        """Test generating registers outputs."""
        domains = discover_domains()
        generator = domains["registers"]

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir)
            templates = {"h": "template.h.j2", "md": "template.md.j2"}

            code_gen = CodeGenerator(generator, output_path)
            filenames = code_gen.generate_from_file(registers_config, templates)

            assert "simple.h" in filenames
            assert "simple.md" in filenames

            # Check files exist
            assert (output_path / "simple.h").exists()
            assert (output_path / "simple.md").exists()
