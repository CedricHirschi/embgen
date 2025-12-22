"""Tests for multifile template support."""

import tempfile
from pathlib import Path


from embgen.templates import (
    parse_template_name,
    discover_templates,
    TemplateInfo,
    MultifileGroup,
)
from embgen.core import parse_and_render
from embgen.domains.commands.generator import CommandsGenerator


class TestParseTemplateName:
    """Test template name parsing."""

    def test_single_file_template(self):
        """Test parsing single file template."""
        group, ext, suffix = parse_template_name("template.h.j2")
        assert group is None
        assert ext == "h"
        assert suffix is None

    def test_single_file_py_template(self):
        """Test parsing single file Python template."""
        group, ext, suffix = parse_template_name("template.py.j2")
        assert group is None
        assert ext == "py"
        assert suffix is None

    def test_single_file_jinja_extension(self):
        """Test parsing template with .jinja extension."""
        group, ext, suffix = parse_template_name("template.md.jinja")
        assert group is None
        assert ext == "md"
        assert suffix is None

    def test_multifile_c_header(self):
        """Test parsing multifile C header template."""
        group, ext, suffix = parse_template_name("template.c_multi.h.j2")
        assert group == "c"
        assert ext == "h"
        assert suffix is None

    def test_multifile_c_source(self):
        """Test parsing multifile C source template."""
        group, ext, suffix = parse_template_name("template.c_multi.c.j2")
        assert group == "c"
        assert ext == "c"
        assert suffix is None

    def test_multifile_sv_with_suffix(self):
        """Test parsing multifile SystemVerilog with suffix."""
        group, ext, suffix = parse_template_name("template.sv_multi.sv.1.j2")
        assert group == "sv"
        assert ext == "sv"
        assert suffix == "1"

    def test_multifile_sv_second_file(self):
        """Test parsing second multifile SystemVerilog template."""
        group, ext, suffix = parse_template_name("template.sv_multi.sv.2.j2")
        assert group == "sv"
        assert ext == "sv"
        assert suffix == "2"

    def test_multifile_custom_suffix(self):
        """Test parsing multifile with named suffix."""
        group, ext, suffix = parse_template_name("template.verilog_multi.v.top.j2")
        assert group == "verilog"
        assert ext == "v"
        assert suffix == "top"

    def test_non_template_file(self):
        """Test parsing non-template file returns empty."""
        group, ext, suffix = parse_template_name("readme.txt")
        assert group is None
        assert ext == ""
        assert suffix is None

    def test_complex_prefix(self):
        """Test parsing template with complex prefix."""
        group, ext, suffix = parse_template_name("my_domain.c_multi.h.j2")
        assert group == "c"
        assert ext == "h"
        assert suffix is None


class TestDiscoverTemplates:
    """Test template discovery."""

    def test_discover_commands_templates(self):
        """Test discovering commands templates."""
        generator = CommandsGenerator()
        single, multifile = discover_templates(generator.templates_path)

        # Commands domain has h, py, md templates
        assert "h" in single
        assert "py" in single
        assert "md" in single

        # No multifile templates in commands domain by default
        assert len(multifile) == 0

    def test_discover_with_multifile_templates(self):
        """Test discovering multifile templates from temp directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            templates_path = Path(tmpdir)

            # Create single-file template
            (templates_path / "template.py.j2").write_text("# Python template")

            # Create multifile C templates
            (templates_path / "template.c_multi.h.j2").write_text("// Header")
            (templates_path / "template.c_multi.c.j2").write_text("// Source")

            # Create multifile SV templates
            (templates_path / "template.sv_multi.sv.1.j2").write_text("// SV 1")
            (templates_path / "template.sv_multi.sv.2.j2").write_text("// SV 2")

            single, multifile = discover_templates(templates_path)

            # Check single templates
            assert "py" in single
            assert len(single) == 1

            # Check multifile groups
            assert "c" in multifile
            assert "sv" in multifile

            # Check C multifile group
            c_group = multifile["c"]
            assert c_group.group_name == "c"
            assert len(c_group.templates) == 2
            exts = [t.output_ext for t in c_group.templates]
            assert "h" in exts
            assert "c" in exts

            # Check SV multifile group
            sv_group = multifile["sv"]
            assert sv_group.group_name == "sv"
            assert len(sv_group.templates) == 2
            suffixes = [t.suffix for t in sv_group.templates]
            assert "1" in suffixes
            assert "2" in suffixes

    def test_discover_nonexistent_path(self):
        """Test discovering templates from nonexistent path."""
        single, multifile = discover_templates(Path("/nonexistent/path"))
        assert single == {}
        assert multifile == {}


class TestMultifileGroup:
    """Test MultifileGroup dataclass."""

    def test_output_extensions(self):
        """Test output_extensions property."""
        group = MultifileGroup(
            group_name="c",
            description="C Multi-file",
            templates=[
                TemplateInfo("template.c_multi.h.j2", "h", None),
                TemplateInfo("template.c_multi.c.j2", "c", None),
            ],
        )
        assert group.output_extensions == ["h", "c"]

    def test_output_extensions_same_ext(self):
        """Test output_extensions with same extensions."""
        group = MultifileGroup(
            group_name="sv",
            description="SV Multi-file",
            templates=[
                TemplateInfo("template.sv_multi.sv.1.j2", "sv", "1"),
                TemplateInfo("template.sv_multi.sv.2.j2", "sv", "2"),
            ],
        )
        assert group.output_extensions == ["sv", "sv"]


class TestMultifileGeneration:
    """Test multifile code generation."""

    def test_generate_multifile_different_extensions(self):
        """Test generating multifile with different extensions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            templates_path = Path(tmpdir) / "templates"
            templates_path.mkdir()

            # Create multifile C templates
            (templates_path / "template.c_multi.h.j2").write_text(
                "// {{ name }} header\n#ifndef {{ name | upper }}_H\n#define {{ name | upper }}_H\n#endif"
            )
            (templates_path / "template.c_multi.c.j2").write_text(
                '// {{ name }} source\n#include "{{ name }}.h"'
            )

            # Create output directory
            output_path = Path(tmpdir) / "output"
            output_path.mkdir()

            # Create minimal YAML config
            config_file = Path(tmpdir) / "config.yml"
            config_file.write_text("name: TestModule\ncommands: []")

            # Discover templates
            single, multifile = discover_templates(templates_path)

            # Verify multifile group was found
            assert "c" in multifile

            # Generate using parse_and_render with multifile
            from embgen.domains.commands.generator import CommandsGenerator

            generator = CommandsGenerator()

            try:
                # Monkey-patch templates_path for this test
                generator.__class__.templates_path = property(
                    lambda self: templates_path
                )

                filenames = parse_and_render(
                    generator,
                    config_file,
                    output_path,
                    {},  # No single templates
                    multifile,  # Use multifile group
                )

                # Check files were generated
                assert len(filenames) == 2
                assert any(
                    "testmodule" in f.lower() and f.endswith(".h") for f in filenames
                )
                assert any(
                    "testmodule" in f.lower() and f.endswith(".c") for f in filenames
                )

                # Check file contents
                h_file = output_path / "testmodule.h"
                c_file = output_path / "testmodule.c"
                assert h_file.exists()
                assert c_file.exists()
                assert "TESTMODULE_H" in h_file.read_text()
                assert '#include "TestModule.h"' in c_file.read_text()
            finally:
                # Restore original templates_path
                generator.__class__.templates_path = property(
                    lambda self: Path(__file__).parent.parent
                    / "src"
                    / "embgen"
                    / "domains"
                    / "commands"
                    / "templates"
                )

    def test_generate_multifile_same_extension(self):
        """Test generating multifile with same extension (using suffixes)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            templates_path = Path(tmpdir) / "templates"
            templates_path.mkdir()

            # Create multifile SV templates with numeric suffixes
            (templates_path / "template.sv_multi.sv.1.j2").write_text(
                "// {{ name }} module 1\nmodule {{ name }}_1;"
            )
            (templates_path / "template.sv_multi.sv.2.j2").write_text(
                "// {{ name }} module 2\nmodule {{ name }}_2;"
            )

            # Create output directory
            output_path = Path(tmpdir) / "output"
            output_path.mkdir()

            # Create minimal YAML config
            config_file = Path(tmpdir) / "config.yml"
            config_file.write_text("name: TestChip\ncommands: []")

            # Discover templates
            single, multifile = discover_templates(templates_path)

            # Verify multifile group was found
            assert "sv" in multifile
            assert len(multifile["sv"].templates) == 2

            # Generate using parse_and_render with multifile
            from embgen.domains.commands.generator import CommandsGenerator

            generator = CommandsGenerator()

            try:
                # Monkey-patch templates_path for this test
                generator.__class__.templates_path = property(
                    lambda self: templates_path
                )

                filenames = parse_and_render(
                    generator,
                    config_file,
                    output_path,
                    {},  # No single templates
                    multifile,  # Use multifile group
                )

                # Check files were generated with suffixes
                assert len(filenames) == 2
                assert "testchip_1.sv" in filenames
                assert "testchip_2.sv" in filenames

                # Check file contents
                sv1_file = output_path / "testchip_1.sv"
                sv2_file = output_path / "testchip_2.sv"
                assert sv1_file.exists()
                assert sv2_file.exists()
                assert "module TestChip_1" in sv1_file.read_text()
                assert "module TestChip_2" in sv2_file.read_text()
            finally:
                # Restore original templates_path
                generator.__class__.templates_path = property(
                    lambda self: Path(__file__).parent.parent
                    / "src"
                    / "embgen"
                    / "domains"
                    / "commands"
                    / "templates"
                )


class TestTemplateInfo:
    """Test TemplateInfo dataclass."""

    def test_basic_info(self):
        """Test basic template info creation."""
        info = TemplateInfo("template.h.j2", "h", None)
        assert info.filename == "template.h.j2"
        assert info.output_ext == "h"
        assert info.suffix is None

    def test_info_with_suffix(self):
        """Test template info with suffix."""
        info = TemplateInfo("template.sv_multi.sv.1.j2", "sv", "1")
        assert info.filename == "template.sv_multi.sv.1.j2"
        assert info.output_ext == "sv"
        assert info.suffix == "1"
