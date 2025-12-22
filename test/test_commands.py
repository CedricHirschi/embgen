"""Thorough tests for the commands domain."""

import tempfile
from pathlib import Path

import pytest
from pydantic import ValidationError

from embgen.domains.commands.models import (
    CommandsConfig,
    Command,
    Argument,
    ArgumentType,
    Endianness,
    Enum,
)
from embgen.domains.commands.generator import CommandsGenerator
from embgen.core import parse_yaml, parse_and_render


class TestArgumentType:
    """Test ArgumentType enum."""

    def test_all_types_defined(self):
        """Ensure all expected types are available."""
        expected = [
            "UINT8",
            "UINT16",
            "UINT32",
            "UINT64",
            "INT8",
            "INT16",
            "INT32",
            "INT64",
            "FLOAT16",
            "FLOAT32",
            "FLOAT64",
            "BOOL",
            "BYTES",
        ]
        for name in expected:
            assert hasattr(ArgumentType, name)

    def test_type_values(self):
        """Test type values match struct format codes."""
        assert ArgumentType.UINT8 == "B"
        assert ArgumentType.INT32 == "i"
        assert ArgumentType.FLOAT32 == "f"
        assert ArgumentType.BOOL == "?"
        assert ArgumentType.BYTES == "s"


class TestEndianness:
    """Test Endianness enum."""

    def test_big_endian(self):
        assert Endianness.BIG == ">"

    def test_little_endian(self):
        assert Endianness.LITTLE == "<"


class TestEnumModel:
    """Test Enum model."""

    def test_basic_enum(self):
        e = Enum(name="TEST", value=42)
        assert e.name == "TEST"
        assert e.value == 42
        assert e.description is None

    def test_enum_with_description(self):
        e = Enum(name="TEST", value=42, description="Test enum")
        assert e.description == "Test enum"


class TestArgumentModel:
    """Test Argument model."""

    def test_basic_argument(self):
        arg = Argument(
            name="test_arg",
            description="A test argument",
            type=ArgumentType.UINT8,
        )
        assert arg.name == "test_arg"
        assert arg.description == "A test argument"
        assert arg.type == ArgumentType.UINT8
        assert arg.enums is None
        assert arg.default is None

    def test_argument_with_default_int(self):
        arg = Argument(
            name="test_arg",
            description="With default",
            type=ArgumentType.UINT32,
            default=100,
        )
        assert arg.default == 100

    def test_argument_with_default_bool(self):
        arg = Argument(
            name="enable",
            description="Enable flag",
            type=ArgumentType.BOOL,
            default=True,
        )
        assert arg.default is True

    def test_argument_with_enums(self):
        enums = [
            Enum(name="OFF", value=0),
            Enum(name="ON", value=1),
        ]
        arg = Argument(
            name="state",
            description="State",
            type=ArgumentType.UINT8,
            enums=enums,
        )
        assert arg.enums is not None
        assert len(arg.enums) == 2
        assert arg.enums[0].name == "OFF"

    def test_argument_default_enum_conversion(self):
        """Test that string default is converted to Enum when enums are defined."""
        # Use model_validate to test the validator which converts string to Enum
        arg = Argument.model_validate(
            {
                "name": "mode",
                "description": "Mode",
                "type": "B",
                "enums": [
                    {"name": "OFF", "value": 0},
                    {"name": "ON", "value": 1},
                ],
                "default": "ON",
            }
        )
        # After validation, default should be the Enum object
        assert isinstance(arg.default, Enum)
        assert arg.default.name == "ON"
        assert arg.default.value == 1

    def test_type_python_property(self):
        """Test computed type_python property."""
        int_types = [
            ArgumentType.UINT8,
            ArgumentType.UINT16,
            ArgumentType.UINT32,
            ArgumentType.UINT64,
            ArgumentType.INT8,
            ArgumentType.INT16,
            ArgumentType.INT32,
            ArgumentType.INT64,
        ]
        for t in int_types:
            arg = Argument(name="x", description="x", type=t)
            assert arg.type_python == "int"

        float_types = [ArgumentType.FLOAT16, ArgumentType.FLOAT32, ArgumentType.FLOAT64]
        for t in float_types:
            arg = Argument(name="x", description="x", type=t)
            assert arg.type_python == "float"

        arg = Argument(name="x", description="x", type=ArgumentType.BOOL)
        assert arg.type_python == "bool"

        arg = Argument(name="x", description="x", type=ArgumentType.BYTES)
        assert arg.type_python == "bytes"


class TestCommandModel:
    """Test Command model."""

    def test_basic_command(self):
        cmd = Command(name="ping", id=0)
        assert cmd.name == "ping"
        assert cmd.id == 0
        assert cmd.description is None
        assert cmd.args == []
        assert cmd.returns == []

    def test_command_with_description(self):
        cmd = Command(name="ping", id=0, description="Ping the device")
        assert cmd.description == "Ping the device"

    def test_command_with_args(self):
        args = [
            Argument(name="value", description="Value", type=ArgumentType.UINT8),
        ]
        cmd = Command(name="set", id=1, args=args)
        assert len(cmd.args) == 1
        assert cmd.args[0].name == "value"

    def test_command_with_returns(self):
        returns = [
            Argument(name="status", description="Status", type=ArgumentType.UINT8),
        ]
        cmd = Command(name="get_status", id=2, returns=returns)
        assert cmd.returns is not None
        assert len(cmd.returns) == 1


class TestCommandsConfig:
    """Test CommandsConfig model."""

    def test_basic_config(self):
        cfg = CommandsConfig(
            name="TestCommands",
            commands=[Command(name="ping", id=0)],
        )
        assert cfg.name == "TestCommands"
        assert cfg.file is None
        assert cfg.endianness == Endianness.LITTLE  # default
        assert len(cfg.commands) == 1

    def test_output_filename_default(self):
        cfg = CommandsConfig(
            name="TestCommands",
            commands=[Command(name="ping", id=0)],
        )
        assert cfg.output_filename == "testcommands"

    def test_output_filename_explicit(self):
        cfg = CommandsConfig(
            name="TestCommands",
            file="custom_output",
            commands=[Command(name="ping", id=0)],
        )
        assert cfg.output_filename == "custom_output"

    def test_big_endian(self):
        cfg = CommandsConfig(
            name="TestCommands",
            endianness=Endianness.BIG,
            commands=[Command(name="ping", id=0)],
        )
        assert cfg.endianness == Endianness.BIG

    def test_validation_missing_name(self):
        with pytest.raises(ValidationError):
            CommandsConfig.model_validate({"commands": [{"name": "ping", "id": 0}]})

    def test_validation_missing_commands(self):
        with pytest.raises(ValidationError):
            CommandsConfig.model_validate({"name": "TestCommands"})


class TestCommandsGenerator:
    """Test CommandsGenerator."""

    @pytest.fixture
    def generator(self) -> CommandsGenerator:
        return CommandsGenerator()

    @pytest.fixture
    def sample_data(self) -> dict:
        return {
            "name": "TestCommands",
            "commands": [
                {"name": "ping", "id": 0, "description": "Ping"},
                {
                    "name": "set_value",
                    "id": 1,
                    "args": [
                        {"name": "value", "description": "Value to set", "type": "B"},
                    ],
                },
            ],
        }

    def test_name(self, generator: CommandsGenerator):
        assert generator.name == "commands"

    def test_description(self, generator: CommandsGenerator):
        assert "command" in generator.description.lower()

    def test_detect_positive(self, generator: CommandsGenerator, sample_data: dict):
        assert generator.detect(sample_data) is True

    def test_detect_negative(self, generator: CommandsGenerator):
        assert generator.detect({"name": "Test", "regmap": []}) is False

    def test_detect_empty(self, generator: CommandsGenerator):
        assert generator.detect({}) is False

    def test_validate(self, generator: CommandsGenerator, sample_data: dict):
        config = generator.validate(sample_data)
        # Returns BaseConfig but is actually CommandsConfig
        assert config.name == "TestCommands"

    def test_templates_path_exists(self, generator: CommandsGenerator):
        assert generator.templates_path.exists()
        assert generator.templates_path.is_dir()

    def test_templates_available(self, generator: CommandsGenerator):
        templates = list(generator.templates_path.glob("*.j2"))
        assert len(templates) >= 3  # At least h, py, md


class TestCommandsGeneration:
    """Test full commands generation pipeline."""

    @pytest.fixture
    def commands_config(self) -> Path:
        return Path(__file__).parent / "configs" / "commands" / "tinyprobe.yml"

    @pytest.fixture
    def generator(self) -> CommandsGenerator:
        return CommandsGenerator()

    def test_parse_yaml(self, commands_config: Path):
        data = parse_yaml(commands_config)
        assert data["name"] == "TinyProbeCommands"
        assert len(data["commands"]) == 11

    def test_validate_full_config(
        self, commands_config: Path, generator: CommandsGenerator
    ):
        data = parse_yaml(commands_config)
        config = generator.validate(data)
        assert config.name == "TinyProbeCommands"

    def test_generate_header(self, commands_config: Path, generator: CommandsGenerator):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir)
            templates = {"h": "template.h.j2"}

            filenames = parse_and_render(
                generator, commands_config, output_path, templates
            )

            assert "tinyprobecommands.h" in filenames
            header_file = output_path / "tinyprobecommands.h"
            assert header_file.exists()

            content = header_file.read_text()
            assert "TINYPROBECOMMANDS" in content  # Guard macro
            assert "ping" in content.lower()

    def test_generate_python(self, commands_config: Path, generator: CommandsGenerator):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir)
            templates = {"py": "template.py.j2"}

            filenames = parse_and_render(
                generator, commands_config, output_path, templates
            )

            assert "tinyprobecommands.py" in filenames
            assert "commands_base.py" in filenames  # Post-generate copies this

            py_file = output_path / "tinyprobecommands.py"
            base_file = output_path / "commands_base.py"
            assert py_file.exists()
            assert base_file.exists()

    def test_generate_markdown(
        self, commands_config: Path, generator: CommandsGenerator
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir)
            templates = {"md": "template.md.j2"}

            filenames = parse_and_render(
                generator, commands_config, output_path, templates
            )

            assert "tinyprobecommands.md" in filenames
            md_file = output_path / "tinyprobecommands.md"
            assert md_file.exists()

            content = md_file.read_text()
            assert "TinyProbeCommands" in content

    def test_generate_all_formats(
        self, commands_config: Path, generator: CommandsGenerator
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir)
            templates = {
                "h": "template.h.j2",
                "py": "template.py.j2",
                "md": "template.md.j2",
            }

            filenames = parse_and_render(
                generator, commands_config, output_path, templates
            )

            assert len(filenames) == 4  # 3 templates + commands_base.py

    def test_post_generate_skips_when_no_python(
        self, commands_config: Path, generator: CommandsGenerator
    ):
        """Test that commands_base.py is NOT copied when Python is not generated."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir)
            templates = {"h": "template.h.j2", "md": "template.md.j2"}

            filenames = parse_and_render(
                generator, commands_config, output_path, templates
            )

            assert "commands_base.py" not in filenames
            assert not (output_path / "commands_base.py").exists()


class TestCommandsEdgeCases:
    """Test edge cases for commands domain."""

    def test_empty_commands_list(self):
        """Config with no commands."""
        cfg = CommandsConfig(name="Empty", commands=[])
        assert len(cfg.commands) == 0

    def test_command_with_bytes_arg(self):
        """Command with bytes type argument."""
        arg = Argument(name="data", description="Raw data", type=ArgumentType.BYTES)
        cmd = Command(name="write_raw", id=10, args=[arg])
        assert cmd.args[0].type == ArgumentType.BYTES

    def test_multiple_enums_in_arg(self):
        """Argument with multiple enum values."""
        enums = [
            Enum(name="A", value=0, description="First"),
            Enum(name="B", value=1, description="Second"),
            Enum(name="C", value=2, description="Third"),
            Enum(name="D", value=3, description="Fourth"),
        ]
        arg = Argument(
            name="mode",
            description="Mode selection",
            type=ArgumentType.UINT8,
            enums=enums,
        )
        assert arg.enums is not None
        assert len(arg.enums) == 4

    def test_command_with_both_args_and_returns(self):
        """Command with both input args and return values."""
        cmd = Command(
            name="exchange",
            id=100,
            description="Exchange data",
            args=[
                Argument(name="input", description="Input", type=ArgumentType.UINT32),
            ],
            returns=[
                Argument(name="output", description="Output", type=ArgumentType.UINT32),
            ],
        )
        assert len(cmd.args) == 1
        assert cmd.returns is not None
        assert len(cmd.returns) == 1
