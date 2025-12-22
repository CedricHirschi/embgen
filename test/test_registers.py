"""Thorough tests for the registers domain."""

import tempfile
from pathlib import Path

import pytest
from pydantic import ValidationError

from embgen.domains.registers.models import (
    RegistersConfig,
    Register,
    BitField,
    Access,
)
from embgen.domains.registers.generator import RegistersGenerator
from embgen.models import Enum
from embgen.core import parse_yaml, parse_and_render


class TestAccessEnum:
    """Test Access enum."""

    def test_all_access_types_defined(self):
        """Ensure all expected access types are available."""
        expected = ["RO", "RW", "WO", "RWC", "WOS", "ROLH"]
        for name in expected:
            assert hasattr(Access, name)

    def test_access_values(self):
        assert Access.RO.value == "ro"
        assert Access.RW.value == "rw"
        assert Access.WO.value == "wo"
        assert Access.RWC.value == "rw1c"
        assert Access.WOS.value == "wosc"
        assert Access.ROLH.value == "rolh"

    def test_access_str(self):
        assert str(Access.RO) == "RO"
        assert str(Access.RW) == "RW"

    def test_access_repr(self):
        assert repr(Access.RO) == "Access.RO"


class TestBitFieldModel:
    """Test BitField model."""

    def test_basic_bitfield(self):
        bf = BitField(
            name="ENABLE",
            reset=0,
            width=1,
            offset=0,
        )
        assert bf.name == "ENABLE"
        assert bf.description is None
        assert bf.reset == 0
        assert bf.width == 1
        assert bf.offset == 0
        assert bf.enums is None

    def test_bitfield_with_description(self):
        bf = BitField(
            name="ENABLE",
            description="Enable bit",
            reset=0,
            width=1,
            offset=0,
        )
        assert bf.description == "Enable bit"

    def test_bitfield_with_enums(self):
        enums = [
            Enum(name="OFF", value=0, description="Disabled"),
            Enum(name="ON", value=1, description="Enabled"),
        ]
        bf = BitField(
            name="STATE",
            reset=0,
            width=1,
            offset=0,
            enums=enums,
        )
        assert bf.enums is not None
        assert len(bf.enums) == 2
        assert bf.enums[0].name == "OFF"
        assert bf.enums[1].name == "ON"

    def test_multibit_field(self):
        """BitField spanning multiple bits."""
        bf = BitField(
            name="MODE",
            reset=0,
            width=4,
            offset=4,
        )
        assert bf.width == 4
        assert bf.offset == 4

    def test_bitfield_with_nonzero_reset(self):
        bf = BitField(
            name="DEFAULT_ON",
            reset=1,
            width=1,
            offset=0,
        )
        assert bf.reset == 1


class TestRegisterModel:
    """Test Register model."""

    def test_basic_register(self):
        reg = Register(
            name="CONTROL",
            address=0,
            bitfields=[
                BitField(name="ENABLE", reset=0, width=1, offset=0),
            ],
        )
        assert reg.name == "CONTROL"
        assert reg.description is None
        assert reg.address == 0
        assert reg.access == Access.RW  # default
        assert len(reg.bitfields) == 1

    def test_register_with_description(self):
        reg = Register(
            name="CONTROL",
            description="Control register",
            address=0,
            bitfields=[
                BitField(name="ENABLE", reset=0, width=1, offset=0),
            ],
        )
        assert reg.description == "Control register"

    def test_read_only_register(self):
        reg = Register(
            name="STATUS",
            address=4,
            access=Access.RO,
            bitfields=[
                BitField(name="READY", reset=0, width=1, offset=0),
            ],
        )
        assert reg.access == Access.RO

    def test_write_only_register(self):
        reg = Register(
            name="TRIGGER",
            address=8,
            access=Access.WO,
            bitfields=[
                BitField(name="START", reset=0, width=1, offset=0),
            ],
        )
        assert reg.access == Access.WO

    def test_register_with_multiple_bitfields(self):
        reg = Register(
            name="CONFIG",
            address=0x10,
            bitfields=[
                BitField(name="BIT0", reset=0, width=1, offset=0),
                BitField(name="BIT1", reset=0, width=1, offset=1),
                BitField(name="NIBBLE", reset=0, width=4, offset=4),
                BitField(name="BYTE", reset=0, width=8, offset=8),
            ],
        )
        assert len(reg.bitfields) == 4


class TestRegistersConfig:
    """Test RegistersConfig model."""

    def test_basic_config(self):
        cfg = RegistersConfig(
            name="TestRegmap",
            regmap=[
                Register(
                    name="REG0",
                    address=0,
                    bitfields=[BitField(name="BIT", reset=0, width=1, offset=0)],
                ),
            ],
        )
        assert cfg.name == "TestRegmap"
        assert cfg.file is None
        assert len(cfg.regmap) == 1

    def test_output_filename_default(self):
        cfg = RegistersConfig(
            name="TestRegmap",
            regmap=[
                Register(
                    name="REG0",
                    address=0,
                    bitfields=[BitField(name="BIT", reset=0, width=1, offset=0)],
                ),
            ],
        )
        assert cfg.output_filename == "testregmap"

    def test_output_filename_explicit(self):
        cfg = RegistersConfig(
            name="TestRegmap",
            file="custom_regmap",
            regmap=[
                Register(
                    name="REG0",
                    address=0,
                    bitfields=[BitField(name="BIT", reset=0, width=1, offset=0)],
                ),
            ],
        )
        assert cfg.output_filename == "custom_regmap"

    def test_validation_missing_name(self):
        with pytest.raises(ValidationError):
            RegistersConfig.model_validate(
                {
                    "regmap": [
                        {
                            "name": "REG0",
                            "address": 0,
                            "bitfields": [
                                {"name": "BIT", "reset": 0, "width": 1, "offset": 0}
                            ],
                        },
                    ]
                }
            )

    def test_validation_missing_regmap(self):
        with pytest.raises(ValidationError):
            RegistersConfig.model_validate({"name": "TestRegmap"})


class TestRegistersGenerator:
    """Test RegistersGenerator."""

    @pytest.fixture
    def generator(self) -> RegistersGenerator:
        return RegistersGenerator()

    @pytest.fixture
    def sample_data(self) -> dict:
        return {
            "name": "TestRegmap",
            "regmap": [
                {
                    "name": "CONTROL",
                    "address": 0,
                    "bitfields": [
                        {"name": "ENABLE", "reset": 0, "width": 1, "offset": 0},
                    ],
                },
            ],
        }

    def test_name(self, generator: RegistersGenerator):
        assert generator.name == "registers"

    def test_description(self, generator: RegistersGenerator):
        assert "register" in generator.description.lower()

    def test_detect_positive(self, generator: RegistersGenerator, sample_data: dict):
        assert generator.detect(sample_data) is True

    def test_detect_negative(self, generator: RegistersGenerator):
        assert generator.detect({"name": "Test", "commands": []}) is False

    def test_detect_empty(self, generator: RegistersGenerator):
        assert generator.detect({}) is False

    def test_validate(self, generator: RegistersGenerator, sample_data: dict):
        config = generator.validate(sample_data)
        assert config.name == "TestRegmap"

    def test_templates_path_exists(self, generator: RegistersGenerator):
        assert generator.templates_path.exists()
        assert generator.templates_path.is_dir()

    def test_templates_available(self, generator: RegistersGenerator):
        templates = list(generator.templates_path.glob("*.j2"))
        assert len(templates) >= 3  # At least h, py, md


class TestRegistersGeneration:
    """Test full registers generation pipeline."""

    @pytest.fixture
    def registers_config(self) -> Path:
        return Path(__file__).parent / "configs" / "registers" / "simple.yml"

    @pytest.fixture
    def generator(self) -> RegistersGenerator:
        return RegistersGenerator()

    def test_parse_yaml(self, registers_config: Path):
        data = parse_yaml(registers_config)
        assert data["name"] == "SimpleRegmap"
        assert len(data["regmap"]) == 4  # CONTROL, STATUS, DATA, CONFIG

    def test_validate_full_config(
        self, registers_config: Path, generator: RegistersGenerator
    ):
        data = parse_yaml(registers_config)
        config = generator.validate(data)
        assert config.name == "SimpleRegmap"

    def test_generate_header(
        self, registers_config: Path, generator: RegistersGenerator
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir)
            templates = {"h": "template.h.j2"}

            filenames = parse_and_render(
                generator, registers_config, output_path, templates
            )

            assert "simple.h" in filenames
            header_file = output_path / "simple.h"
            assert header_file.exists()

            content = header_file.read_text()
            assert "SIMPLE" in content.upper()  # Guard macro or defines

    def test_generate_python(
        self, registers_config: Path, generator: RegistersGenerator
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir)
            templates = {"py": "template.py.j2"}

            filenames = parse_and_render(
                generator, registers_config, output_path, templates
            )

            assert "simple.py" in filenames
            py_file = output_path / "simple.py"
            assert py_file.exists()

    def test_generate_markdown(
        self, registers_config: Path, generator: RegistersGenerator
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir)
            templates = {"md": "template.md.j2"}

            filenames = parse_and_render(
                generator, registers_config, output_path, templates
            )

            assert "simple.md" in filenames
            md_file = output_path / "simple.md"
            assert md_file.exists()

            content = md_file.read_text()
            assert "SimpleRegmap" in content

    def test_generate_all_formats(
        self, registers_config: Path, generator: RegistersGenerator
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir)
            templates = {
                "h": "template.h.j2",
                "py": "template.py.j2",
                "md": "template.md.j2",
            }

            filenames = parse_and_render(
                generator, registers_config, output_path, templates
            )

            # 3 templates + 2 post_generate files (reg_common.h, reg_common.c) when h is generated
            assert len(filenames) >= 3
            assert "simple.h" in filenames
            assert "simple.py" in filenames
            assert "simple.md" in filenames


class TestRegistersEdgeCases:
    """Test edge cases for registers domain."""

    def test_empty_regmap(self):
        """Config with no registers."""
        cfg = RegistersConfig(name="Empty", regmap=[])
        assert len(cfg.regmap) == 0

    def test_register_high_address(self):
        """Register at high address."""
        reg = Register(
            name="HIGH_ADDR",
            address=0xFFFFFFFF,
            bitfields=[BitField(name="BIT", reset=0, width=1, offset=0)],
        )
        assert reg.address == 0xFFFFFFFF

    def test_full_32bit_register(self):
        """Register with 32-bit bitfield."""
        reg = Register(
            name="DATA",
            address=0,
            bitfields=[
                BitField(name="VALUE", reset=0, width=32, offset=0),
            ],
        )
        assert reg.bitfields[0].width == 32

    def test_bitfield_with_many_enums(self):
        """BitField with many enum values."""
        enums = [
            Enum(name=f"VAL_{i}", value=i, description=f"Value {i}") for i in range(8)
        ]
        bf = BitField(
            name="MODE",
            reset=0,
            width=3,
            offset=0,
            enums=enums,
        )
        assert bf.enums is not None
        assert len(bf.enums) == 8

    def test_all_access_types_in_config(self):
        """Config with all access types."""
        cfg = RegistersConfig(
            name="AllAccess",
            regmap=[
                Register(
                    name="RO_REG",
                    address=0,
                    access=Access.RO,
                    bitfields=[BitField(name="BIT", reset=0, width=1, offset=0)],
                ),
                Register(
                    name="RW_REG",
                    address=4,
                    access=Access.RW,
                    bitfields=[BitField(name="BIT", reset=0, width=1, offset=0)],
                ),
                Register(
                    name="WO_REG",
                    address=8,
                    access=Access.WO,
                    bitfields=[BitField(name="BIT", reset=0, width=1, offset=0)],
                ),
                Register(
                    name="RWC_REG",
                    address=12,
                    access=Access.RWC,
                    bitfields=[BitField(name="BIT", reset=0, width=1, offset=0)],
                ),
            ],
        )
        assert len(cfg.regmap) == 4
        assert cfg.regmap[0].access == Access.RO
        assert cfg.regmap[1].access == Access.RW
        assert cfg.regmap[2].access == Access.WO
        assert cfg.regmap[3].access == Access.RWC


class TestGeneratedPythonInterface:
    """Test the generated Python register interface for correct behavior."""

    @pytest.fixture
    def registers_config(self) -> Path:
        return Path(__file__).parent / "configs" / "registers" / "simple.yml"

    @pytest.fixture
    def generator(self) -> RegistersGenerator:
        return RegistersGenerator()

    @pytest.fixture
    def generated_module(self, registers_config: Path, generator: RegistersGenerator):
        """Generate the Python module and import it."""
        import sys
        import importlib.util

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir)
            templates = {"py": "template.py.j2"}

            parse_and_render(generator, registers_config, output_path, templates)

            py_file = output_path / "simple.py"
            spec = importlib.util.spec_from_file_location("simple_test_module", py_file)
            assert spec is not None, "Failed to create module spec"
            assert spec.loader is not None, "Module spec has no loader"
            module = importlib.util.module_from_spec(spec)
            sys.modules["simple_test_module"] = module
            spec.loader.exec_module(module)
            yield module
            del sys.modules["simple_test_module"]

    def test_nonzero_reset_integer_bitfield(self, generated_module):
        """Test that integer bitfields with non-zero reset values are read correctly."""
        import logging

        Interface = generated_module.Interface
        SimpleRegmap = generated_module.SimpleRegmap

        rm = SimpleRegmap(Interface(logging.getLogger()))

        # STATUS.READY has reset=1
        assert rm.status.ready.value == 1

        # CONFIG.GAIN has reset=5
        assert rm.config.gain.value == 5

        # CONFIG.OFFSET has reset=128
        assert rm.config.offset.value == 128

    def test_nonzero_reset_enum_bitfield(self, generated_module):
        """Test that enum bitfields with non-zero reset values return correct enum."""
        import logging

        Interface = generated_module.Interface
        SimpleRegmap = generated_module.SimpleRegmap

        rm = SimpleRegmap(Interface(logging.getLogger()))

        # CONTROL.MODE has reset=1, which is EnumMode.NORMAL
        mode_value = rm.control.mode.value
        assert mode_value == SimpleRegmap.EnumMode.NORMAL
        assert mode_value.value == 1

        # CONFIG.POLARITY has reset=1, which is EnumPolarity.INVERTED
        polarity_value = rm.config.polarity.value
        assert polarity_value == SimpleRegmap.EnumPolarity.INVERTED
        assert polarity_value.value == 1

    def test_nonzero_reset_hex_value(self, generated_module):
        """Test that hex reset values (like 0xCAFE) are correctly handled."""
        import logging

        Interface = generated_module.Interface
        SimpleRegmap = generated_module.SimpleRegmap

        rm = SimpleRegmap(Interface(logging.getLogger()))

        # DATA.VALUE has reset=0xCAFE (51966)
        assert rm.data.value.value == 0xCAFE
        assert rm.data.value.value == 51966

    def test_write_then_read_preserves_value(self, generated_module):
        """Test that writing a value and reading it back returns the written value."""
        import logging

        Interface = generated_module.Interface
        SimpleRegmap = generated_module.SimpleRegmap

        rm = SimpleRegmap(Interface(logging.getLogger()))

        # Write a new value to GAIN
        rm.config.gain.value = 10
        assert rm.config.gain.value == 10

        # Write a new value to MODE (enum)
        rm.control.mode.value = SimpleRegmap.EnumMode.STANDBY
        assert rm.control.mode.value == SimpleRegmap.EnumMode.STANDBY

    def test_reset_restores_reset_values(self, generated_module):
        """Test that interface reset restores all bitfields to their reset values."""
        import logging

        Interface = generated_module.Interface
        SimpleRegmap = generated_module.SimpleRegmap

        interface = Interface(logging.getLogger())
        rm = SimpleRegmap(interface)

        # Change some values
        rm.config.gain.value = 15
        rm.control.mode.value = SimpleRegmap.EnumMode.SLEEP
        assert rm.config.gain.value == 15
        assert rm.control.mode.value == SimpleRegmap.EnumMode.SLEEP

        # Reset interface
        interface.reset()

        # Values should now be back to reset values
        assert rm.config.gain.value == 5  # reset value
        assert rm.control.mode.value == SimpleRegmap.EnumMode.NORMAL  # reset=1

    def test_bitfield_width_validation(self, generated_module):
        """Test that bitfield width validation works correctly."""
        import logging

        Interface = generated_module.Interface
        SimpleRegmap = generated_module.SimpleRegmap

        rm = SimpleRegmap(Interface(logging.getLogger()))

        # ENABLE has width=1, so max value is 1
        rm.control.enable.value = 1
        assert rm.control.enable.value == 1

        # Try to write a value that exceeds the width
        with pytest.raises(ValueError, match="exceeds width"):
            rm.control.enable.value = 2

    def test_bitfield_negative_value_validation(self, generated_module):
        """Test that negative values are rejected."""
        import logging

        Interface = generated_module.Interface
        SimpleRegmap = generated_module.SimpleRegmap

        rm = SimpleRegmap(Interface(logging.getLogger()))

        with pytest.raises(ValueError, match="cannot be negative"):
            rm.control.enable.value = -1

    def test_enum_bitfield_type_validation(self, generated_module):
        """Test that enum bitfields reject non-enum values."""
        import logging

        Interface = generated_module.Interface
        SimpleRegmap = generated_module.SimpleRegmap

        rm = SimpleRegmap(Interface(logging.getLogger()))

        # MODE requires an EnumMode, not an int
        with pytest.raises(TypeError, match="must be of type"):
            rm.control.mode.value = 1

    def test_zero_reset_bitfields(self, generated_module):
        """Test that bitfields with zero reset values still work correctly."""
        import logging

        Interface = generated_module.Interface
        SimpleRegmap = generated_module.SimpleRegmap

        rm = SimpleRegmap(Interface(logging.getLogger()))

        # ENABLE has reset=0
        assert rm.control.enable.value == 0

        # BUSY has reset=0
        assert rm.status.busy.value == 0

        # ERROR has reset=0
        assert rm.status.error.value == 0
