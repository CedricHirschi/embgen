"""Thorough tests for the registers domain."""

import tempfile
from pathlib import Path

import pytest
from pydantic import ValidationError

from embgen.domains.registers_shallow.models import (
    RegistersConfig,
    Register,
    BitField,
    Access,
)
from embgen.domains.registers_shallow.generator import RegistersGenerator
from embgen.models import Enum
from embgen.generator import CodeGenerator


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
            regmap_shallow=[
                Register(
                    name="REG0",
                    address=0,
                    bitfields=[BitField(name="BIT", reset=0, width=1, offset=0)],
                ),
            ],
        )
        assert cfg.name == "TestRegmap"
        assert cfg.file is None
        assert len(cfg.regmap_shallow) == 1

    def test_output_filename_default(self):
        cfg = RegistersConfig(
            name="TestRegmap",
            regmap_shallow=[
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
            regmap_shallow=[
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
                    "regmap_shallow": [
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
            "generate_shallow": True,
            "regmap_shallow": [
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
        assert generator.name == "registers_shallow"

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
        return Path(__file__).parent / "configs" / "registers_shallow" / "simple.yml"

    @pytest.fixture
    def generator(self) -> RegistersGenerator:
        return RegistersGenerator()

    def test_parse_yaml(self, registers_config: Path, generator: RegistersGenerator):
        code_gen = CodeGenerator(generator, Path.cwd())
        data = code_gen.parse_yaml(registers_config)
        assert data["name"] == "SimpleRegmap"
        assert len(data["regmap_shallow"]) == 4  # CONTROL, STATUS, DATA, CONFIG

    def test_validate_full_config(
        self, registers_config: Path, generator: RegistersGenerator
    ):
        code_gen = CodeGenerator(generator, Path.cwd())
        data = code_gen.parse_yaml(registers_config)
        config = generator.validate(data)
        assert config.name == "SimpleRegmap"

    def test_generate_header(
        self, registers_config: Path, generator: RegistersGenerator
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir)
            templates = {"h": "template.h.j2"}

            code_gen = CodeGenerator(generator, output_path)
            filenames = code_gen.generate_from_file(registers_config, templates)

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

            code_gen = CodeGenerator(generator, output_path)
            filenames = code_gen.generate_from_file(registers_config, templates)

            assert "simple.py" in filenames
            assert "simple_base.py" in filenames

            py_file = output_path / "simple.py"
            base_py_file = output_path / "simple_base.py"
            assert py_file.exists()
            assert base_py_file.exists()

    def test_generate_markdown(
        self, registers_config: Path, generator: RegistersGenerator
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir)
            templates = {"md": "template.md.j2"}

            code_gen = CodeGenerator(generator, output_path)
            filenames = code_gen.generate_from_file(registers_config, templates)

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

            code_gen = CodeGenerator(generator, output_path)
            filenames = code_gen.generate_from_file(registers_config, templates)

            # 3 templates + 2 post_generate files (reg_common.h, reg_common.c) when h is generated
            assert len(filenames) >= 3
            assert "simple.h" in filenames
            assert "simple.py" in filenames
            assert "simple.md" in filenames


class TestRegistersEdgeCases:
    """Test edge cases for registers domain."""

    def test_empty_regmap(self):
        """Config with no registers."""
        cfg = RegistersConfig(name="Empty", regmap_shallow=[])
        assert len(cfg.regmap_shallow) == 0

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
            regmap_shallow=[
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
        assert len(cfg.regmap_shallow) == 4
        assert cfg.regmap_shallow[0].access == Access.RO
        assert cfg.regmap_shallow[1].access == Access.RW
        assert cfg.regmap_shallow[2].access == Access.WO
        assert cfg.regmap_shallow[3].access == Access.RWC


class TestGeneratedPythonInterface:
    """Test the generated Python register interface for correct behavior."""

    @pytest.fixture
    def registers_config(self) -> Path:
        return Path(__file__).parent / "configs" / "registers_shallow" / "simple.yml"

    @pytest.fixture
    def generator(self) -> RegistersGenerator:
        return RegistersGenerator()

    @pytest.fixture
    def generated_module(self, registers_config: Path, generator: RegistersGenerator):
        """Generate the Python module and import it."""
        import sys
        import importlib.util
        import types

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir)
            templates = {"py": "template.py.j2"}

            code_gen = CodeGenerator(generator, output_path)
            code_gen.generate_from_file(registers_config, templates)

            # Add temp directory to sys.path
            sys.path.insert(0, str(output_path))

            # Create a fake package for relative imports to work
            pkg_name = "simple_pkg"
            pkg = types.ModuleType(pkg_name)
            pkg.__path__ = [str(output_path)]
            sys.modules[pkg_name] = pkg

            # Load the base module first
            base_file = output_path / "simple_base.py"
            base_spec = importlib.util.spec_from_file_location(
                f"{pkg_name}.simple_base",
                base_file,
            )
            assert base_spec is not None and base_spec.loader is not None
            base_module = importlib.util.module_from_spec(base_spec)
            sys.modules[f"{pkg_name}.simple_base"] = base_module
            base_spec.loader.exec_module(base_module)

            # Load the main module
            py_file = output_path / "simple.py"
            spec = importlib.util.spec_from_file_location(
                f"{pkg_name}.simple",
                py_file,
            )
            assert spec is not None, "Failed to create module spec"
            assert spec.loader is not None, "Module spec has no loader"
            module = importlib.util.module_from_spec(spec)
            sys.modules[f"{pkg_name}.simple"] = module
            spec.loader.exec_module(module)
            yield module
            # Cleanup
            del sys.modules[f"{pkg_name}.simple"]
            del sys.modules[f"{pkg_name}.simple_base"]
            del sys.modules[pkg_name]
            sys.path.remove(str(output_path))

    def test_nonzero_reset_integer_bitfield(self, generated_module):
        """Test that integer bitfields with non-zero reset values are read correctly."""

        Interface = generated_module.Interface
        SimpleRegmap = generated_module.SimpleRegmap

        rm = SimpleRegmap(Interface())

        # STATUS.READY has reset=1
        assert rm.status.ready == 1

        # CONFIG.GAIN has reset=5
        assert rm.config.gain == 5

        # CONFIG.OFFSET has reset=128
        assert rm.config.offset == 128

    def test_nonzero_reset_enum_bitfield(self, generated_module):
        """Test that enum bitfields with non-zero reset values return correct enum."""

        Interface = generated_module.Interface
        SimpleRegmap = generated_module.SimpleRegmap

        rm = SimpleRegmap(Interface())

        # CONTROL.MODE has reset=1, which is EnumMode.NORMAL
        mode_value = rm.control.mode
        assert mode_value == SimpleRegmap.EnumMode.NORMAL
        assert mode_value.value == 1

        # CONFIG.POLARITY has reset=1, which is EnumPolarity.INVERTED
        polarity_value = rm.config.polarity
        assert polarity_value == SimpleRegmap.EnumPolarity.INVERTED
        assert polarity_value.value == 1

    def test_nonzero_reset_hex_value(self, generated_module):
        """Test that hex reset values (like 0xCAFE) are correctly handled."""

        Interface = generated_module.Interface
        SimpleRegmap = generated_module.SimpleRegmap

        rm = SimpleRegmap(Interface())

        # DATA.VALUE has reset=0xCAFE (51966)
        assert rm.data.value == 0xCAFE
        assert rm.data.value == 51966

    def test_write_then_read_preserves_value(self, generated_module):
        """Test that writing a value and reading it back returns the written value."""

        Interface = generated_module.Interface
        SimpleRegmap = generated_module.SimpleRegmap

        rm = SimpleRegmap(Interface())

        # Write a new value to GAIN
        rm.config.gain = 10
        assert rm.config.gain == 10

        # Write a new value to MODE (enum)
        rm.control.mode = SimpleRegmap.EnumMode.STANDBY
        assert rm.control.mode == SimpleRegmap.EnumMode.STANDBY

    def test_reset_restores_reset_values(self, generated_module):
        """Test that interface reset restores all bitfields to their reset values."""

        Interface = generated_module.Interface
        SimpleRegmap = generated_module.SimpleRegmap

        interface = Interface()
        rm = SimpleRegmap(interface)

        # Change some values
        rm.config.gain = 15
        rm.control.mode = SimpleRegmap.EnumMode.SLEEP
        assert rm.config.gain == 15
        assert rm.control.mode == SimpleRegmap.EnumMode.SLEEP

        # Reset interface
        interface.reset()

        # Values should now be back to reset values
        assert rm.config.gain == 5  # reset value
        assert rm.control.mode == SimpleRegmap.EnumMode.NORMAL  # reset=1

    def test_bitfield_width_validation(self, generated_module):
        """Test that bitfield width validation works correctly."""

        Interface = generated_module.Interface
        SimpleRegmap = generated_module.SimpleRegmap

        rm = SimpleRegmap(Interface())

        # ENABLE has width=1, so max value is 1
        rm.control.enable = 1
        assert rm.control.enable == 1

        # Try to write a value that exceeds the width
        with pytest.raises(ValueError, match="exceeds width"):
            rm.control.enable = 2

    def test_bitfield_negative_value_validation(self, generated_module):
        """Test that negative values are rejected."""

        Interface = generated_module.Interface
        SimpleRegmap = generated_module.SimpleRegmap

        rm = SimpleRegmap(Interface())

        with pytest.raises(ValueError, match="cannot be negative"):
            rm.control.enable = -1

    def test_enum_bitfield_type_validation(self, generated_module):
        """Test that enum bitfields reject non-enum values."""

        Interface = generated_module.Interface
        SimpleRegmap = generated_module.SimpleRegmap

        rm = SimpleRegmap(Interface())

        # MODE requires an EnumMode, not an int
        with pytest.raises(TypeError, match="Expected type"):
            rm.control.mode = 1

    def test_zero_reset_bitfields(self, generated_module):
        """Test that bitfields with zero reset values still work correctly."""

        Interface = generated_module.Interface
        SimpleRegmap = generated_module.SimpleRegmap

        rm = SimpleRegmap(Interface())

        # ENABLE has reset=0
        assert rm.control.enable == 0

        # BUSY has reset=0
        assert rm.status.busy == 0

        # ERROR has reset=0
        assert rm.status.error == 0

    def test_shallow_properties_follow_read_write_access(self, generated_module):
        """Test that shallow properties expose only supported accessors."""

        rm = generated_module.SimpleRegmap(generated_module.Interface())

        assert type(rm.control).enable.fget is not None
        assert type(rm.control).enable.fset is not None
        assert type(rm.status).ready.fget is not None
        assert type(rm.status).ready.fset is None

        rm.control.enable = 1
        assert rm.control.enable == 1

        with pytest.raises(AttributeError):
            rm.status.ready = 0

    def test_shallow_write_only_properties_have_setter_only(self, generator):
        """Test write-only shallow bitfields can be written but not read."""
        import importlib.util
        import sys
        import types

        config_path = (
            Path(__file__).parent
            / "configs"
            / "registers_shallow"
            / "pulser_general.yml"
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir)
            code_gen = CodeGenerator(generator, output_path)
            code_gen.generate_from_file(config_path, {"py": "template.py.j2"})

            pkg_name = "pulser_pkg"
            pkg = types.ModuleType(pkg_name)
            pkg.__path__ = [str(output_path)]
            sys.modules[pkg_name] = pkg

            base_spec = importlib.util.spec_from_file_location(
                f"{pkg_name}.pulser_general_base",
                output_path / "pulser_general_base.py",
            )
            assert base_spec is not None and base_spec.loader is not None
            base_module = importlib.util.module_from_spec(base_spec)
            sys.modules[f"{pkg_name}.pulser_general_base"] = base_module
            base_spec.loader.exec_module(base_module)

            spec = importlib.util.spec_from_file_location(
                f"{pkg_name}.pulser_general",
                output_path / "pulser_general.py",
            )
            assert spec is not None and spec.loader is not None
            module = importlib.util.module_from_spec(spec)
            sys.modules[f"{pkg_name}.pulser_general"] = module
            spec.loader.exec_module(module)

            interface = module.Interface()
            rm = module.pulser_general(interface)

            assert type(rm.ctrl).start.fget is None
            assert type(rm.ctrl).start.fset is not None

            rm.ctrl.start = 1
            assert interface.memory[0][0] == 1

            with pytest.raises(AttributeError):
                _ = rm.ctrl.start

            del sys.modules[f"{pkg_name}.pulser_general"]
            del sys.modules[f"{pkg_name}.pulser_general_base"]
            del sys.modules[pkg_name]


class TestRegisterGroupModel:
    """Test RegisterGroup model for numbered registers."""

    def test_basic_register_group(self):
        from embgen.domains.registers_shallow.models import (
            RegisterGroup,
            BitField,
            Access,
        )

        group = RegisterGroup(
            name="DATA",
            description="Data register",
            base_address=0,
            access=Access.RW,
            bitfields=[BitField(name="VALUE", reset=0, width=16, offset=0)],
            count=4,
        )
        assert group.name == "DATA"
        assert group.base_address == 0
        assert group.count == 4
        assert len(group.bitfields) == 1


class TestRegisterGroupGeneration:
    """Test generation of register groups (numbered registers) using numbers.yml."""

    @pytest.fixture
    def numbers_config(self) -> Path:
        return Path(__file__).parent / "configs" / "registers_shallow" / "numbers.yml"

    @pytest.fixture
    def generator(self) -> RegistersGenerator:
        return RegistersGenerator()

    def test_validate_creates_register_groups(
        self, numbers_config: Path, generator: RegistersGenerator
    ):
        """Test that validation creates RegisterGroup objects."""
        code_gen = CodeGenerator(generator, Path.cwd())
        data = code_gen.parse_yaml(numbers_config)
        config = generator.validate(data)  # type: ignore

        config: RegistersConfig = config  # type: ignore

        # Should have one register group
        assert len(config.register_groups) == 1
        group = config.register_groups[0]
        assert group.name == "DATA"
        assert group.base_address == 0
        assert group.count == 16

        assert len(config.hjson_entries) == 1
        assert config.hjson_entries[0].kind == "multireg"

        # Expanded registers should still exist for backward compatibility
        assert len(config.regmap_shallow) == 16

    def test_generate_python_with_register_groups(
        self, numbers_config: Path, generator: RegistersGenerator
    ):
        """Test that Python generation creates a single base class for grouped registers."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir)
            templates = {"py": "template.py.j2"}

            code_gen = CodeGenerator(generator, output_path)
            filenames = code_gen.generate_from_file(numbers_config, templates)

            assert "numbers.py" in filenames
            py_file = output_path / "numbers.py"
            content = py_file.read_text()

            # Should have a single RegisterDATA class (not RegisterDATA0, RegisterDATA1, etc.)
            assert "class RegisterDATA(Register):" in content
            assert "class RegisterDATA0" not in content
            assert "class RegisterDATA15" not in content

            # Should use dictionary comprehension for the register map
            assert "self.data: dict[int, RegisterDATA]" in content

    def test_generate_header_with_register_groups(
        self, numbers_config: Path, generator: RegistersGenerator
    ):
        """Test that C header generation creates a single union for grouped registers."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir)
            templates = {"h": "template.h.j2"}

            code_gen = CodeGenerator(generator, output_path)
            filenames = code_gen.generate_from_file(numbers_config, templates)

            assert "numbers.h" in filenames
            header_file = output_path / "numbers.h"
            content = header_file.read_text()

            # Should have a single numbers_data union (not numbers_data0, numbers_data1, etc.)
            assert "typedef union numbers_data_u" in content
            assert "typedef union numbers_data0_u" not in content

            # Should use array in the struct
            assert "data[16]" in content

            # Should have COUNT macro
            assert "#define NUMBERS_DATA_COUNT 16" in content

            # Should have address macro
            assert "#define NUMBERS_ADDR_DATA(index)" in content

    def test_generate_hjson_with_multireg(
        self, numbers_config: Path, generator: RegistersGenerator
    ):
        """Test that hjson generation emits multireg blocks instead of flat registers."""
        import subprocess
        import sys

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir)
            templates = {"hjson": "template.hjson.j2"}

            code_gen = CodeGenerator(generator, output_path)
            filenames = code_gen.generate_from_file(numbers_config, templates)

            assert "numbers.hjson" in filenames
            hjson_file = output_path / "numbers.hjson"
            content = hjson_file.read_text()

            assert "multireg:" in content
            assert 'count: "16"' in content
            assert 'name: "DATA0"' not in content

            result = subprocess.run(
                [
                    sys.executable,
                    "regtool.py",
                    "-r",
                    "-t",
                    output_path.as_posix(),
                    hjson_file.as_posix(),
                ],
                cwd=Path(__file__).parent.parent
                / "src"
                / "embgen"
                / "domains"
                / "registers_shallow"
                / "regtool",
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0, result.stderr


class TestGeneratedPythonRegisterGroups:
    """Test the generated Python register interface for register groups."""

    @pytest.fixture
    def numbers_config(self) -> Path:
        return Path(__file__).parent / "configs" / "registers_shallow" / "numbers.yml"

    @pytest.fixture
    def generator(self) -> RegistersGenerator:
        return RegistersGenerator()

    @pytest.fixture
    def generated_module(self, numbers_config: Path, generator: RegistersGenerator):
        """Generate the Python module and import it."""
        import sys
        import importlib.util
        import types

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir)
            templates = {"py": "template.py.j2"}

            code_gen = CodeGenerator(generator, output_path)
            code_gen.generate_from_file(numbers_config, templates)

            # Add temp directory to sys.path
            sys.path.insert(0, str(output_path))

            # Create a fake package for relative imports to work
            pkg_name = "numbers_pkg"
            pkg = types.ModuleType(pkg_name)
            pkg.__path__ = [str(output_path)]
            sys.modules[pkg_name] = pkg

            # Load the base module first
            base_file = output_path / "numbers_base.py"
            base_spec = importlib.util.spec_from_file_location(
                f"{pkg_name}.numbers_base",
                base_file,
            )
            assert base_spec is not None and base_spec.loader is not None
            base_module = importlib.util.module_from_spec(base_spec)
            sys.modules[f"{pkg_name}.numbers_base"] = base_module
            base_spec.loader.exec_module(base_module)

            # Load the main module
            py_file = output_path / "numbers.py"
            spec = importlib.util.spec_from_file_location(
                f"{pkg_name}.numbers",
                py_file,
            )
            assert spec is not None, "Failed to create module spec"
            assert spec.loader is not None, "Module spec has no loader"
            module = importlib.util.module_from_spec(spec)
            sys.modules[f"{pkg_name}.numbers"] = module
            spec.loader.exec_module(module)
            yield module
            # Cleanup
            del sys.modules[f"{pkg_name}.numbers"]
            del sys.modules[f"{pkg_name}.numbers_base"]
            del sys.modules[pkg_name]
            sys.path.remove(str(output_path))

    def test_register_group_dict_access(self, generated_module):
        """Test accessing registers through dictionary-like interface."""

        Interface = generated_module.Interface
        Numbers = generated_module.Numbers

        rm = Numbers(Interface())

        # Access registers via dictionary key
        assert 0 in rm.data
        assert 15 in rm.data
        assert 16 not in rm.data

        # Each register should be accessible
        for i in [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]:
            assert i in rm.data
            # Each register should have the value bitfield
            assert hasattr(rm.data[i], "value")

    def test_register_group_reset_values(self, generated_module):
        """Test that all registers in a group have correct reset values."""

        Interface = generated_module.Interface
        Numbers = generated_module.Numbers

        rm = Numbers(Interface())

        # All DATA registers should have reset value 0xCAFE (51966)
        for i in range(16):
            assert rm.data[i].value == 0xCAFE

    def test_register_group_independent_values(self, generated_module):
        """Test that registers in a group have independent values."""

        Interface = generated_module.Interface
        Numbers = generated_module.Numbers

        rm = Numbers(Interface())

        # Write different values to different registers
        rm.data[0].value = 0x1111
        rm.data[5].value = 0x5555
        rm.data[15].value = 0xFFFF

        # Verify values are independent
        assert rm.data[0].value == 0x1111
        assert rm.data[5].value == 0x5555
        assert rm.data[15].value == 0xFFFF

        # Other registers should still have reset value
        assert rm.data[1].value == 0xCAFE
        assert rm.data[10].value == 0xCAFE

    def test_register_group_addresses(self, generated_module):
        """Test that each register in a group has the correct address."""

        Interface = generated_module.Interface
        Numbers = generated_module.Numbers

        rm = Numbers(Interface())

        # Each register should have sequential addresses starting from base_address
        for i in range(16):
            assert rm.data[i]._address == i

    def test_register_group_iteration(self, generated_module):
        """Test iterating over registers in a group."""

        Interface = generated_module.Interface
        Numbers = generated_module.Numbers

        rm = Numbers(Interface())

        # Should be able to iterate over all registers
        count = 0
        for idx, reg in rm.data.items():
            assert reg._address == idx
            count += 1
        assert count == 16


class TestRegisterMapMethods:
    """Test RegisterMap methods work with instance attributes."""

    @pytest.fixture
    def simple_config(self) -> Path:
        return Path(__file__).parent / "configs" / "registers_shallow" / "simple.yml"

    @pytest.fixture
    def numbers_config(self) -> Path:
        return Path(__file__).parent / "configs" / "registers_shallow" / "numbers.yml"

    @pytest.fixture
    def generated_simple(self, simple_config: Path):
        """Generate and import the simple module."""
        import sys
        import importlib.util
        import types
        import warnings

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir)
            templates = {"py": "template.py.j2"}

            generator = RegistersGenerator()
            code_gen = CodeGenerator(generator, output_path)
            code_gen.generate_from_file(simple_config, templates)

            sys.path.insert(0, str(output_path))

            pkg_name = "simple_test_pkg"
            pkg = types.ModuleType(pkg_name)
            pkg.__path__ = [str(output_path)]
            sys.modules[pkg_name] = pkg

            # Load the base module first
            base_file = output_path / "simple_base.py"
            base_spec = importlib.util.spec_from_file_location(
                f"{pkg_name}.simple_base",
                base_file,
            )
            assert base_spec is not None and base_spec.loader is not None
            base_module = importlib.util.module_from_spec(base_spec)
            sys.modules[f"{pkg_name}.simple_base"] = base_module
            base_spec.loader.exec_module(base_module)

            # Load the main module
            py_file = output_path / "simple.py"
            spec = importlib.util.spec_from_file_location(
                f"{pkg_name}.simple",
                py_file,
            )
            assert spec is not None and spec.loader is not None
            module = importlib.util.module_from_spec(spec)
            sys.modules[f"{pkg_name}.simple"] = module

            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=SyntaxWarning)
                spec.loader.exec_module(module)

            yield module

            sys.path.remove(str(output_path))
            if f"{pkg_name}.simple" in sys.modules:
                del sys.modules[f"{pkg_name}.simple"]
            if f"{pkg_name}.simple_base" in sys.modules:
                del sys.modules[f"{pkg_name}.simple_base"]
            if pkg_name in sys.modules:
                del sys.modules[pkg_name]

    @pytest.fixture
    def generated_numbers(self, numbers_config: Path):
        """Generate and import the numbers module."""
        import sys
        import importlib.util
        import types
        import warnings

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir)
            templates = {"py": "template.py.j2"}

            generator = RegistersGenerator()
            code_gen = CodeGenerator(generator, output_path)
            code_gen.generate_from_file(numbers_config, templates)

            sys.path.insert(0, str(output_path))

            pkg_name = "numbers_test_pkg"
            pkg = types.ModuleType(pkg_name)
            pkg.__path__ = [str(output_path)]
            sys.modules[pkg_name] = pkg

            # Load the base module first
            base_file = output_path / "numbers_base.py"
            base_spec = importlib.util.spec_from_file_location(
                f"{pkg_name}.numbers_base",
                base_file,
            )
            assert base_spec is not None and base_spec.loader is not None
            base_module = importlib.util.module_from_spec(base_spec)
            sys.modules[f"{pkg_name}.numbers_base"] = base_module
            base_spec.loader.exec_module(base_module)

            # Load the main module
            py_file = output_path / "numbers.py"
            spec = importlib.util.spec_from_file_location(
                f"{pkg_name}.numbers",
                py_file,
            )
            assert spec is not None and spec.loader is not None
            module = importlib.util.module_from_spec(spec)
            sys.modules[f"{pkg_name}.numbers"] = module

            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=SyntaxWarning)
                spec.loader.exec_module(module)

            yield module

            sys.path.remove(str(output_path))
            if f"{pkg_name}.numbers" in sys.modules:
                del sys.modules[f"{pkg_name}.numbers"]
            if f"{pkg_name}.numbers_base" in sys.modules:
                del sys.modules[f"{pkg_name}.numbers_base"]
            if pkg_name in sys.modules:
                del sys.modules[pkg_name]

    def test_registermap_reset_works_with_instance_attrs(self, generated_simple):
        """Test that RegisterMap.reset() works when registers are instance attributes.

        This also verifies that bitfields named 'reset' don't conflict with the reset() method.
        """

        Interface = generated_simple.Interface
        SimpleRegmap = generated_simple.SimpleRegmap

        rm = SimpleRegmap(Interface())

        # Modify multiple register values
        rm.data.value = 0x1234
        rm.config.gain = 15  # Max value for 4-bit field
        assert rm.data.value == 0x1234
        assert rm.config.gain == 15

        # Reset should restore all registers to reset values
        rm.regmap_reset()
        assert rm.data.value == 0xCAFE  # Reset value from config
        assert rm.config.gain == 5  # Reset value from config

    def test_registermap_raw_works_with_instance_attrs(self, generated_simple):
        """Test that RegisterMap.regmap_raw property works when registers are instance attributes."""

        Interface = generated_simple.Interface
        SimpleRegmap = generated_simple.SimpleRegmap

        rm = SimpleRegmap(Interface())

        # raw should return a dict of register addresses to values
        raw = rm.regmap_raw
        assert isinstance(raw, dict)
        assert len(raw) > 0
        assert all(isinstance(k, int) for k in raw.keys())
        assert all(isinstance(v, int) for v in raw.values())

    def test_registermap_addresses_works_with_instance_attrs(self, generated_simple):
        """Test that RegisterMap.regmap_addresses property works when registers are instance attributes."""

        Interface = generated_simple.Interface
        SimpleRegmap = generated_simple.SimpleRegmap

        rm = SimpleRegmap(Interface())

        # addresses should return a set of register addresses
        addresses = rm.regmap_addresses
        assert isinstance(addresses, set)
        assert len(addresses) > 0
        assert all(isinstance(addr, int) for addr in addresses)

    def test_registermap_registers_works_with_instance_attrs(self, generated_simple):
        """Test that RegisterMap.regmap_registers property works when registers are instance attributes."""

        Interface = generated_simple.Interface
        SimpleRegmap = generated_simple.SimpleRegmap

        rm = SimpleRegmap(Interface())

        # registers should return a dict of address -> Register
        registers = rm.regmap_registers
        assert isinstance(registers, dict)
        assert len(registers) > 0
        assert all(isinstance(k, int) for k in registers.keys())

    def test_registermap_reset_with_register_groups(self, generated_numbers):
        """Test that RegisterMap.regmap_reset() works with register groups."""

        Interface = generated_numbers.Interface
        Numbers = generated_numbers.Numbers

        rm = Numbers(Interface())

        # Modify values in register group
        rm.data[0].value = 0x1111
        rm.data[5].value = 0x5555
        assert rm.data[0].value == 0x1111
        assert rm.data[5].value == 0x5555

        # Reset should restore all registers including groups
        rm.regmap_reset()
        assert rm.data[0].value == 0xCAFE  # Reset value from config
        assert rm.data[5].value == 0xCAFE

    def test_registermap_raw_with_register_groups(self, generated_numbers):
        """Test that RegisterMap.regmap_raw works with register groups."""

        Interface = generated_numbers.Interface
        Numbers = generated_numbers.Numbers

        rm = Numbers(Interface())

        raw = rm.regmap_raw
        assert isinstance(raw, dict)
        # Should include all 16 registers from the group
        assert len(raw) >= 16

    def test_registermap_addresses_with_register_groups(self, generated_numbers):
        """Test that RegisterMap.regmap_addresses works with register groups."""

        Interface = generated_numbers.Interface
        Numbers = generated_numbers.Numbers

        rm = Numbers(Interface())

        addresses = rm.regmap_addresses
        assert isinstance(addresses, set)
        # Should include all addresses from register groups
        assert len(addresses) >= 16
        # Should include sequential addresses for the group
        for i in range(16):
            assert i in addresses

    def test_registermap_registers_with_register_groups(self, generated_numbers):
        """Test that RegisterMap.regmap_registers works with register groups."""

        Interface = generated_numbers.Interface
        Numbers = generated_numbers.Numbers

        rm = Numbers(Interface())

        registers = rm.regmap_registers
        assert isinstance(registers, dict)
        # Should include all registers from groups
        assert len(registers) >= 16
        # Verify we can access registers from the dict
        for i in range(16):
            assert i in registers
            assert registers[i]._address == i


class TestInterfaceWidthValidation:
    """Test that Interface validates width parameter."""

    def test_interface_write_validates_width(self):
        """Test that Interface.write() validates value against width."""
        from embgen.domains.registers_shallow.templates.registers_base import Interface

        interface = Interface()

        # Valid write should succeed
        interface.write(register_address=0, offset=0, width=4, value=15)
        assert interface.memory[0][0] == 15

        # Value exceeding width should raise ValueError
        with pytest.raises(ValueError, match="exceeds maximum"):
            interface.write(register_address=0, offset=0, width=4, value=16)

    def test_interface_write_validates_negative(self):
        """Test that Interface.write() rejects negative values."""
        from embgen.domains.registers_shallow.templates.registers_base import Interface

        interface = Interface()

        # Negative value should raise ValueError
        with pytest.raises(ValueError, match="cannot be negative"):
            interface.write(register_address=0, offset=0, width=4, value=-1)

    def test_interface_write_accepts_zero(self):
        """Test that Interface.write() accepts zero."""
        from embgen.domains.registers_shallow.templates.registers_base import Interface

        interface = Interface()

        # Zero should always be valid
        interface.write(register_address=0, offset=0, width=1, value=0)
        assert interface.memory[0][0] == 0

    def test_interface_write_validates_max_value(self):
        """Test that Interface.write() accepts maximum value for width."""
        from embgen.domains.registers_shallow.templates.registers_base import Interface

        interface = Interface()

        # Max value for width should be accepted
        interface.write(register_address=0, offset=0, width=8, value=255)
        assert interface.memory[0][0] == 255

        # One more should fail
        with pytest.raises(ValueError, match="exceeds maximum"):
            interface.write(register_address=0, offset=0, width=8, value=256)


class TestMultipleRegisterMapInstances:
    """Test that multiple RegisterMap instances work independently."""

    @pytest.fixture
    def simple_config(self) -> Path:
        return Path(__file__).parent / "configs" / "registers_shallow" / "simple.yml"

    @pytest.fixture
    def generated_simple(self, simple_config: Path):
        """Generate and import the simple module."""
        import sys
        import importlib.util
        import types
        import warnings

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir)
            templates = {"py": "template.py.j2"}

            generator = RegistersGenerator()
            code_gen = CodeGenerator(generator, output_path)
            code_gen.generate_from_file(simple_config, templates)

            sys.path.insert(0, str(output_path))

            pkg_name = "shared_test_pkg"
            pkg = types.ModuleType(pkg_name)
            pkg.__path__ = [str(output_path)]
            sys.modules[pkg_name] = pkg

            # Load the base module first
            base_file = output_path / "simple_base.py"
            base_spec = importlib.util.spec_from_file_location(
                f"{pkg_name}.simple_base",
                base_file,
            )
            assert base_spec is not None and base_spec.loader is not None
            base_module = importlib.util.module_from_spec(base_spec)
            sys.modules[f"{pkg_name}.simple_base"] = base_module
            base_spec.loader.exec_module(base_module)

            # Load the main module
            py_file = output_path / "simple.py"
            spec = importlib.util.spec_from_file_location(
                f"{pkg_name}.simple",
                py_file,
            )
            assert spec is not None and spec.loader is not None
            module = importlib.util.module_from_spec(spec)
            sys.modules[f"{pkg_name}.simple"] = module

            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=SyntaxWarning)
                spec.loader.exec_module(module)

            yield module

            sys.path.remove(str(output_path))
            if f"{pkg_name}.simple" in sys.modules:
                del sys.modules[f"{pkg_name}.simple"]
            if f"{pkg_name}.simple_base" in sys.modules:
                del sys.modules[f"{pkg_name}.simple_base"]
            if pkg_name in sys.modules:
                del sys.modules[pkg_name]

    def test_multiple_registermap_instances_work_independently(self, generated_simple):
        """Verify that multiple RegisterMap instances work independently.

        With instance-level BitFields, multiple RegisterMap instances can coexist
        without interfering with each other.
        """

        Interface = generated_simple.Interface
        SimpleRegmap = generated_simple.SimpleRegmap

        # Create two RegisterMaps with different interfaces
        rm1 = SimpleRegmap(Interface())
        rm2 = SimpleRegmap(Interface())

        # Write different values
        rm1.data.value = 0x1111
        rm2.data.value = 0x2222

        # Values should be independent - each RegisterMap has its own BitField instances
        assert rm1.data.value == 0x1111
        assert rm2.data.value == 0x2222

        # Reset one shouldn't affect the other
        rm1.regmap_reset()
        assert rm1.data.value == 0xCAFE  # Reset value
        assert rm2.data.value == 0x2222  # Unchanged


class TestBitFieldHelpers:
    """Test BitField helper methods."""

    @pytest.fixture
    def generated_module(self):
        """Generate and load test module."""
        import sys
        import importlib.util
        import types

        config_path = (
            Path(__file__).parent / "configs" / "registers_shallow" / "simple.yml"
        )
        generator = RegistersGenerator()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir)
            templates = {"py": "template.py.j2"}

            code_gen = CodeGenerator(generator, output_path)
            code_gen.generate_from_file(config_path, templates)

            sys.path.insert(0, str(output_path))

            fake_package = types.ModuleType("test_pkg_bf")
            fake_package.__path__ = [str(output_path)]
            sys.modules["test_pkg_bf"] = fake_package

            base_path = output_path / "simple_base.py"
            main_path = output_path / "simple.py"

            base_spec = importlib.util.spec_from_file_location(
                "test_pkg_bf.simple_base", base_path
            )
            assert base_spec is not None
            base_module = importlib.util.module_from_spec(base_spec)
            sys.modules["test_pkg_bf.simple_base"] = base_module
            assert base_spec.loader is not None
            base_spec.loader.exec_module(base_module)

            spec = importlib.util.spec_from_file_location(
                "test_pkg_bf.simple", main_path
            )
            assert spec is not None
            module = importlib.util.module_from_spec(spec)
            sys.modules["test_pkg_bf.simple"] = module
            assert spec.loader is not None
            spec.loader.exec_module(module)

            yield module

            sys.path.remove(str(output_path))
            for key in list(sys.modules.keys()):
                if key.startswith("test_pkg_bf"):
                    del sys.modules[key]

    def test_bitfield_is_valid_integer(self, generated_module):
        """Test is_valid() for integer bitfields."""
        interface = generated_module.Interface()
        rm = generated_module.SimpleRegmap(interface)
        bf = rm.data.reg_get_bitfield("VALUE")

        assert bf.is_valid(0)
        assert bf.is_valid(100)
        assert bf.is_valid(65535)  # 16-bit max
        assert not bf.is_valid(-1)
        assert not bf.is_valid(65536)  # Beyond 16-bit

    def test_bitfield_is_valid_enum(self, generated_module):
        """Test is_valid() for enum bitfields."""
        interface = generated_module.Interface()
        rm = generated_module.SimpleRegmap(interface)
        bf = rm.control.reg_get_bitfield("MODE")

        # Valid enum values
        assert bf.is_valid(generated_module.SimpleRegmap.EnumMode.NORMAL)
        assert bf.is_valid(generated_module.SimpleRegmap.EnumMode.STANDBY)

        # Invalid types
        assert not bf.is_valid(0)
        assert not bf.is_valid(1)

    def test_bitfield_maximum_property(self, generated_module):
        """Test maximum property for integer bitfields."""
        interface = generated_module.Interface()
        rm = generated_module.SimpleRegmap(interface)
        bf = rm.data.reg_get_bitfield("VALUE")

        max_val = bf.maximum
        assert max_val == 65535  # 16-bit

    def test_bitfield_str_with_interface(self, generated_module):
        """Test __str__() with interface bound."""
        interface = generated_module.Interface()
        rm = generated_module.SimpleRegmap(interface)
        bf = rm.data.reg_get_bitfield("VALUE")

        s = str(bf)
        assert "VALUE" in s
        assert "bits 0:15" in s
        assert "RW" in s

    def test_bitfield_str_with_enum(self, generated_module):
        """Test __str__() with enum bitfield."""
        interface = generated_module.Interface()
        rm = generated_module.SimpleRegmap(interface)
        bf = rm.control.reg_get_bitfield("MODE")

        # Mode enum should show name
        s = str(bf)
        assert "MODE" in s
        assert "bits" in s


class TestRegisterHelpers:
    """Test Register helper methods."""

    @pytest.fixture
    def generated_module(self):
        """Generate and load test module."""
        import sys
        import importlib.util
        import types

        config_path = (
            Path(__file__).parent / "configs" / "registers_shallow" / "simple.yml"
        )
        generator = RegistersGenerator()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir)
            templates = {"py": "template.py.j2"}

            code_gen = CodeGenerator(generator, output_path)
            code_gen.generate_from_file(config_path, templates)

            sys.path.insert(0, str(output_path))

            fake_package = types.ModuleType("test_pkg_rh")
            fake_package.__path__ = [str(output_path)]
            sys.modules["test_pkg_rh"] = fake_package

            base_path = output_path / "simple_base.py"
            main_path = output_path / "simple.py"

            base_spec = importlib.util.spec_from_file_location(
                "test_pkg_rh.simple_base", base_path
            )
            assert base_spec is not None
            base_module = importlib.util.module_from_spec(base_spec)
            sys.modules["test_pkg_rh.simple_base"] = base_module
            assert base_spec.loader is not None
            base_spec.loader.exec_module(base_module)

            spec = importlib.util.spec_from_file_location(
                "test_pkg_rh.simple", main_path
            )
            assert spec is not None
            module = importlib.util.module_from_spec(spec)
            sys.modules["test_pkg_rh.simple"] = module
            assert spec.loader is not None
            spec.loader.exec_module(module)

            yield module

            sys.path.remove(str(output_path))
            for key in list(sys.modules.keys()):
                if key.startswith("test_pkg_rh"):
                    del sys.modules[key]

    def test_get_bitfield_by_name(self, generated_module):
        """Test get_bitfield() retrieves bitfield by name."""
        interface = generated_module.Interface()
        rm = generated_module.SimpleRegmap(interface)
        reg = rm.control

        bf = reg.reg_get_bitfield("MODE")
        assert bf._name == "MODE"

    def test_get_bitfield_not_found(self, generated_module):
        """Test get_bitfield() raises KeyError for missing bitfield."""
        interface = generated_module.Interface()
        rm = generated_module.SimpleRegmap(interface)
        reg = rm.control

        with pytest.raises(KeyError):
            reg.reg_get_bitfield("nonexistent")

    def test_bitfields_property_returns_dict(self, generated_module):
        """Test bitfields property returns all bitfields."""
        interface = generated_module.Interface()
        rm = generated_module.SimpleRegmap(interface)
        reg = rm.control

        bitfields = reg.reg_bitfields
        assert isinstance(bitfields, dict)
        assert "ENABLE" in bitfields
        assert "MODE" in bitfields
        assert len(bitfields) == 5  # ENABLE, MODE, RESET, START, STOP

    def test_register_str_shows_values(self, generated_module):
        """Test Register __str__() shows bitfield values."""
        interface = generated_module.Interface()
        rm = generated_module.SimpleRegmap(interface)
        reg = rm.control

        rm.control.enable = 1
        s = str(reg)
        assert "0x0000" in s  # Address
        assert "RW" in s  # Access
        assert "ENABLE" in s


class TestRegisterMapHelpers:
    """Test RegisterMap helper methods."""

    @pytest.fixture
    def generated_module_simple(self):
        """Generate and load simple module."""
        import sys
        import importlib.util
        import types

        config_path = (
            Path(__file__).parent / "configs" / "registers_shallow" / "simple.yml"
        )
        generator = RegistersGenerator()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir)
            templates = {"py": "template.py.j2"}

            code_gen = CodeGenerator(generator, output_path)
            code_gen.generate_from_file(config_path, templates)

            sys.path.insert(0, str(output_path))

            fake_package = types.ModuleType("test_pkg_rms")
            fake_package.__path__ = [str(output_path)]
            sys.modules["test_pkg_rms"] = fake_package

            base_path = output_path / "simple_base.py"
            main_path = output_path / "simple.py"

            base_spec = importlib.util.spec_from_file_location(
                "test_pkg_rms.simple_base", base_path
            )
            assert base_spec is not None
            base_module = importlib.util.module_from_spec(base_spec)
            sys.modules["test_pkg_rms.simple_base"] = base_module
            assert base_spec.loader is not None
            base_spec.loader.exec_module(base_module)

            spec = importlib.util.spec_from_file_location(
                "test_pkg_rms.simple", main_path
            )
            assert spec is not None
            module = importlib.util.module_from_spec(spec)
            sys.modules["test_pkg_rms.simple"] = module
            assert spec.loader is not None
            spec.loader.exec_module(module)

            yield module

            sys.path.remove(str(output_path))
            for key in list(sys.modules.keys()):
                if key.startswith("test_pkg_rms"):
                    del sys.modules[key]

    @pytest.fixture
    def generated_module_groups(self):
        """Generate and load module with register groups."""
        import sys
        import importlib.util
        import types

        config_path = (
            Path(__file__).parent / "configs" / "registers_shallow" / "numbers.yml"
        )
        generator = RegistersGenerator()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir)
            templates = {"py": "template.py.j2"}

            code_gen = CodeGenerator(generator, output_path)
            code_gen.generate_from_file(config_path, templates)

            sys.path.insert(0, str(output_path))

            fake_package = types.ModuleType("test_pkg_rmg")
            fake_package.__path__ = [str(output_path)]
            sys.modules["test_pkg_rmg"] = fake_package

            base_path = output_path / "numbers_base.py"
            main_path = output_path / "numbers.py"

            base_spec = importlib.util.spec_from_file_location(
                "test_pkg_rmg.numbers_base", base_path
            )
            assert base_spec is not None
            base_module = importlib.util.module_from_spec(base_spec)
            sys.modules["test_pkg_rmg.numbers_base"] = base_module
            assert base_spec.loader is not None
            base_spec.loader.exec_module(base_module)

            spec = importlib.util.spec_from_file_location(
                "test_pkg_rmg.numbers", main_path
            )
            assert spec is not None
            module = importlib.util.module_from_spec(spec)
            sys.modules["test_pkg_rmg.numbers"] = module
            assert spec.loader is not None
            spec.loader.exec_module(module)

            yield module

            sys.path.remove(str(output_path))
            for key in list(sys.modules.keys()):
                if key.startswith("test_pkg_rmg"):
                    del sys.modules[key]

    def test_get_register_by_address(self, generated_module_simple):
        """Test get_register() retrieves by address."""
        interface = generated_module_simple.Interface()
        rm = generated_module_simple.SimpleRegmap(interface)

        reg = rm.regmap_get_register(0)
        assert reg._address == 0

    def test_get_register_not_found(self, generated_module_simple):
        """Test get_register() raises KeyError for missing address."""
        interface = generated_module_simple.Interface()
        rm = generated_module_simple.SimpleRegmap(interface)

        with pytest.raises(KeyError):
            rm.regmap_get_register(0x9999)

    def test_get_register_by_name(self, generated_module_simple):
        """Test get_register() retrieves by name."""
        interface = generated_module_simple.Interface()
        rm = generated_module_simple.SimpleRegmap(interface)

        reg = rm.regmap_get_register("CONTROL")
        assert reg._address == 0

    def test_get_register_by_name_not_found(self, generated_module_simple):
        """Test get_register() raises KeyError for missing name."""
        interface = generated_module_simple.Interface()
        rm = generated_module_simple.SimpleRegmap(interface)

        with pytest.raises(KeyError):
            rm.regmap_get_register("nonexistent")

    def test_get_bitfield_deep_access(self, generated_module_simple):
        """Test get_bitfield() with register address and bitfield name."""
        interface = generated_module_simple.Interface()
        rm = generated_module_simple.SimpleRegmap(interface)

        bf = rm.regmap_get_bitfield(0, "MODE")
        assert bf._name == "MODE"

    def test_dump_property_format(self, generated_module_simple):
        """Test dump property produces multi-line output."""
        interface = generated_module_simple.Interface()
        rm = generated_module_simple.SimpleRegmap(interface)

        dump = rm.regmap_dump
        assert "SimpleRegmap:" in dump
        assert "0x0000" in dump
        assert "0x0002" in dump
        assert "MODE" in dump
        assert "VALUE" in dump

    def test_dump_property_with_register_groups(self, generated_module_groups):
        """Test dump property works with register groups."""
        interface = generated_module_groups.Interface()
        rm = generated_module_groups.Numbers(interface)

        dump = rm.regmap_dump
        assert "Numbers:" in dump
        assert "0x0000" in dump  # First register
        assert "RegisterDATA" in dump

    def test_restore_single_register(self, generated_module_simple):
        """Test restore() loads state from dict."""
        interface = generated_module_simple.Interface()
        rm = generated_module_simple.SimpleRegmap(interface)

        # Restore with specific values - enable=0, mode=1 (MODE_NORMAL)
        rm.regmap_restore({0: 0x0102})

        assert rm.control.enable == 0
        assert rm.control.mode == generated_module_simple.SimpleRegmap.EnumMode.NORMAL

    def test_restore_multiple_registers(self, generated_module_simple):
        """Test restore() with multiple registers."""
        interface = generated_module_simple.Interface()
        rm = generated_module_simple.SimpleRegmap(interface)

        rm.regmap_restore({0: 0x0102, 2: 0xCAFE})

        assert rm.control.mode == generated_module_simple.SimpleRegmap.EnumMode.NORMAL
        assert rm.data.value == 0xCAFE

    def test_compare_identical_maps(self, generated_module_simple):
        """Test compare() returns empty dict for identical maps."""
        interface1 = generated_module_simple.Interface()
        interface2 = generated_module_simple.Interface()
        rm1 = generated_module_simple.SimpleRegmap(interface1)
        rm2 = generated_module_simple.SimpleRegmap(interface2)

        diffs = rm1.regmap_compare(rm2)
        assert diffs == {}

    def test_compare_different_maps(self, generated_module_simple):
        """Test compare() shows differences."""
        interface1 = generated_module_simple.Interface()
        interface2 = generated_module_simple.Interface()
        rm1 = generated_module_simple.SimpleRegmap(interface1)
        rm2 = generated_module_simple.SimpleRegmap(interface2)

        rm1.data.value = 0x1111
        rm2.data.value = 0x2222

        diffs = rm1.regmap_compare(rm2)
        assert 2 in diffs
        assert diffs[2] == (0x1111, 0x2222)

    def test_write_raw_decomposes_value(self, generated_module_simple):
        """Test write_raw() decomposes and writes bitfields."""
        interface = generated_module_simple.Interface()
        rm = generated_module_simple.SimpleRegmap(interface)

        rm.regmap_write_raw(0, 0x0102)

        assert rm.control.enable == 0
        assert rm.control.mode == generated_module_simple.SimpleRegmap.EnumMode.NORMAL

    def test_read_raw_returns_register_value(self, generated_module_simple):
        """Test read_raw() returns full register value."""
        interface = generated_module_simple.Interface()
        rm = generated_module_simple.SimpleRegmap(interface)

        rm.control.enable = 1
        rm.control.mode = generated_module_simple.SimpleRegmap.EnumMode.SLEEP

        raw = rm.regmap_read_raw(0)
        # ENABLE=1 at bit 0, MODE=SLEEP(3) at bits 1-3
        # bits 1-3 = 3 << 1 = 6, so total = 1 | 6 = 7
        assert raw == 0x0007

    def test_registermap_str_shows_addresses(self, generated_module_simple):
        """Test RegisterMap __str__() shows register addresses."""
        interface = generated_module_simple.Interface()
        rm = generated_module_simple.SimpleRegmap(interface)

        s = str(rm)
        assert "SimpleRegmap" in s
        assert "0x0000" in s
        assert "0x0002" in s
