"""Comprehensive tests for the testing domain.

The testing domain is designed to exercise all embgen features:
- Config parsing and validation
- Single-file template generation
- Multi-file template generation (different extensions like .h/.c)
- Multi-file template generation (same extension like .dat.1/.dat.2/.dat.3)
- Post-generate hooks
- Pydantic model features (validators, computed fields, nested models)
- Jinja2 template features (macros, loops, conditionals, filters)
"""

import tempfile
from pathlib import Path

import pytest
from pydantic import ValidationError

from embgen.domains.testing.models import (
    ConfigTesting,
    Item,
    Tag,
    NestedItem,
    ItemType,
)
from embgen.domains.testing.generator import TestingGenerator
from embgen.discovery import discover_domains, detect_domain
from embgen.generator import CodeGenerator
from embgen.templates import discover_templates


# =============================================================================
# Model Tests
# =============================================================================


class TestItemType:
    """Test ItemType enum."""

    def test_all_types_defined(self):
        """Ensure all expected types are available."""
        assert ItemType.SIMPLE == "simple"
        assert ItemType.COMPLEX == "complex"
        assert ItemType.NESTED == "nested"

    def test_from_string(self):
        """Test enum from string value."""
        assert ItemType("simple") == ItemType.SIMPLE
        assert ItemType("complex") == ItemType.COMPLEX
        assert ItemType("nested") == ItemType.NESTED


class TestTagModel:
    """Test Tag model."""

    def test_basic_tag(self):
        tag = Tag(name="test")
        assert tag.name == "test"
        assert tag.value is None
        assert tag.description is None

    def test_tag_with_value(self):
        tag = Tag(name="version", value=42)
        assert tag.name == "version"
        assert tag.value == 42

    def test_tag_with_all_fields(self):
        tag = Tag(name="priority", value=1, description="High priority")
        assert tag.name == "priority"
        assert tag.value == 1
        assert tag.description == "High priority"


class TestNestedItemModel:
    """Test NestedItem model."""

    def test_basic_nested_item(self):
        item = NestedItem(id=1, label="Test")
        assert item.id == 1
        assert item.label == "Test"
        assert item.tags == []

    def test_nested_item_with_tags(self):
        tags = [Tag(name="a", value=1), Tag(name="b")]
        item = NestedItem(id=2, label="Tagged", tags=tags)
        assert len(item.tags) == 2
        assert item.tags[0].name == "a"
        assert item.tags[0].value == 1


class TestItemModel:
    """Test Item model."""

    def test_basic_item(self):
        item = Item(name="test")
        assert item.name == "test"
        assert item.item_type == ItemType.SIMPLE
        assert item.value == 0
        assert item.enabled is True
        assert item.description is None
        assert item.tags == []
        assert item.children == []
        assert item.metadata == {}

    def test_item_with_all_fields(self):
        item = Item(
            name="full",
            item_type=ItemType.COMPLEX,
            value=100,
            enabled=False,
            description="Full item",
            tags=[Tag(name="t1")],
            children=[NestedItem(id=1, label="Child")],
            metadata={"key": "value"},
        )
        assert item.name == "full"
        assert item.item_type == ItemType.COMPLEX
        assert item.value == 100
        assert item.enabled is False
        assert item.description == "Full item"
        assert len(item.tags) == 1
        assert len(item.children) == 1
        assert item.metadata == {"key": "value"}

    def test_name_validator_strips_whitespace(self):
        """Test that name validator strips whitespace."""
        item = Item(name="  spaced  ")
        assert item.name == "spaced"

    def test_name_validator_rejects_empty(self):
        """Test that empty name is rejected."""
        with pytest.raises(ValidationError):
            Item(name="   ")

    def test_computed_name_upper(self):
        """Test computed name_upper property."""
        item = Item(name="lowercase")
        assert item.name_upper == "LOWERCASE"

    def test_computed_tag_count(self):
        """Test computed tag_count property."""
        item = Item(
            name="counted",
            tags=[Tag(name="t1"), Tag(name="t2")],
            children=[
                NestedItem(id=1, label="c1", tags=[Tag(name="ct1")]),
                NestedItem(id=2, label="c2", tags=[Tag(name="ct2"), Tag(name="ct3")]),
            ],
        )
        # 2 direct tags + 1 child tag + 2 child tags = 5
        assert item.tag_count == 5


class TestTestingConfig:
    """Test TestingConfig model."""

    def test_minimal_config(self):
        cfg = ConfigTesting(name="Test")
        assert cfg.name == "Test"
        assert cfg.file is None
        assert cfg.version == "1.0"
        assert cfg.description is None
        assert cfg.items == []
        assert cfg.global_tags == []
        assert cfg.settings == {}

    def test_output_filename_default(self):
        cfg = ConfigTesting(name="TestConfig")
        assert cfg.output_filename == "testconfig"

    def test_output_filename_explicit(self):
        cfg = ConfigTesting(name="TestConfig", file="custom_output")
        assert cfg.output_filename == "custom_output"

    def test_full_config(self):
        cfg = ConfigTesting(
            name="FullTest",
            file="fulltest",
            version="2.0",
            description="Full test config",
            items=[
                Item(name="item1", item_type=ItemType.SIMPLE),
                Item(name="item2", item_type=ItemType.COMPLEX, enabled=False),
            ],
            global_tags=[Tag(name="author", value=1)],
            settings={"debug": True, "timeout": 1000},
        )
        assert cfg.name == "FullTest"
        assert cfg.version == "2.0"
        assert len(cfg.items) == 2
        assert len(cfg.global_tags) == 1
        assert cfg.settings["debug"] is True

    def test_computed_item_count(self):
        cfg = ConfigTesting(
            name="CountTest",
            items=[Item(name="a"), Item(name="b"), Item(name="c")],
        )
        assert cfg.item_count == 3

    def test_computed_enabled_items(self):
        cfg = ConfigTesting(
            name="EnabledTest",
            items=[
                Item(name="a", enabled=True),
                Item(name="b", enabled=False),
                Item(name="c", enabled=True),
            ],
        )
        enabled = cfg.enabled_items
        assert len(enabled) == 2
        assert all(i.enabled for i in enabled)

    def test_computed_items_by_type(self):
        cfg = ConfigTesting(
            name="TypeTest",
            items=[
                Item(name="a", item_type=ItemType.SIMPLE),
                Item(name="b", item_type=ItemType.COMPLEX),
                Item(name="c", item_type=ItemType.SIMPLE),
                Item(name="d", item_type=ItemType.NESTED),
            ],
        )
        by_type = cfg.items_by_type
        assert len(by_type["simple"]) == 2
        assert len(by_type["complex"]) == 1
        assert len(by_type["nested"]) == 1

    def test_validation_missing_name(self):
        with pytest.raises(ValidationError):
            ConfigTesting.model_validate({"items": []})


# =============================================================================
# Generator Tests
# =============================================================================


class TestTestingGenerator:
    """Test TestingGenerator."""

    @pytest.fixture
    def generator(self) -> TestingGenerator:
        return TestingGenerator()

    @pytest.fixture
    def sample_data(self) -> dict:
        return {
            "name": "SampleTest",
            "items": [
                {"name": "item1", "item_type": "simple", "value": 100},
                {
                    "name": "item2",
                    "item_type": "complex",
                    "tags": [{"name": "t1", "value": 42}],
                },
            ],
        }

    def test_name(self, generator: TestingGenerator):
        assert generator.name == "testing"

    def test_description(self, generator: TestingGenerator):
        assert "testing" in generator.description.lower()

    def test_detect_positive(self, generator: TestingGenerator, sample_data: dict):
        assert generator.detect(sample_data) is True

    def test_detect_negative_no_items(self, generator: TestingGenerator):
        assert generator.detect({"name": "Test", "other": []}) is False

    def test_detect_negative_commands(self, generator: TestingGenerator):
        """Test that commands domain takes precedence."""
        assert generator.detect({"name": "Test", "items": [], "commands": []}) is False

    def test_detect_negative_registers(self, generator: TestingGenerator):
        """Test that registers domain takes precedence."""
        assert generator.detect({"name": "Test", "items": [], "regmap": []}) is False

    def test_detect_empty(self, generator: TestingGenerator):
        assert generator.detect({}) is False

    def test_validate(self, generator: TestingGenerator, sample_data: dict):
        config = generator.validate(sample_data)
        assert config.name == "SampleTest"

    def test_templates_path_exists(self, generator: TestingGenerator):
        assert generator.templates_path.exists()
        assert generator.templates_path.is_dir()

    def test_templates_available(self, generator: TestingGenerator):
        single_templates, multifile_groups = discover_templates(
            generator.templates_path
        )
        # Single-file templates
        assert "txt" in single_templates
        assert "json" in single_templates
        # Multi-file groups (keyed by group name, not full template pattern)
        assert "c" in multifile_groups
        assert "dat" in multifile_groups


# =============================================================================
# Discovery Tests
# =============================================================================


class TestTestingDomainDiscovery:
    """Test that testing domain is properly discovered."""

    def test_discover_includes_testing(self):
        domains = discover_domains()
        assert "testing" in domains

    def test_detect_testing_domain(self):
        data = {"name": "Test", "items": []}
        generator = detect_domain(data)
        assert generator is not None
        assert generator.name == "testing"


# =============================================================================
# Template Discovery Tests
# =============================================================================


class TestTestingTemplateDiscovery:
    """Test template discovery for testing domain."""

    @pytest.fixture
    def generator(self) -> TestingGenerator:
        return TestingGenerator()

    def test_single_file_templates(self, generator: TestingGenerator):
        single, _ = discover_templates(generator.templates_path)
        assert "txt" in single
        assert "json" in single

    def test_multifile_different_ext(self, generator: TestingGenerator):
        _, multifile = discover_templates(generator.templates_path)
        assert "c" in multifile
        c_group = multifile["c"]
        extensions = {t.output_ext for t in c_group.templates}
        assert "h" in extensions
        assert "c" in extensions

    def test_multifile_same_ext(self, generator: TestingGenerator):
        _, multifile = discover_templates(generator.templates_path)
        assert "dat" in multifile
        dat_group = multifile["dat"]
        # All have same extension but different suffixes
        suffixes = [t.suffix for t in dat_group.templates]
        assert len(suffixes) == 3
        assert suffixes == ["1", "2", "3"]


# =============================================================================
# Generation Tests - Single File
# =============================================================================


class TestSingleFileGeneration:
    """Test single-file template generation."""

    @pytest.fixture
    def testing_config(self) -> Path:
        return Path(__file__).parent / "configs" / "testing" / "full_config.yml"

    @pytest.fixture
    def generator(self) -> TestingGenerator:
        return TestingGenerator()

    def test_generate_txt(self, testing_config: Path, generator: TestingGenerator):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir)
            templates = {"txt": "template.txt.j2"}

            code_gen = CodeGenerator(generator, output_path)
            filenames = code_gen.generate_from_file(testing_config, templates)

            # txt + testing_helper.txt from post_generate
            assert "testconfig.txt" in filenames
            assert "testing_helper.txt" in filenames  # post-generate hook

            txt_file = output_path / "testconfig.txt"
            assert txt_file.exists()
            content = txt_file.read_text()
            assert "TESTCONFIG" in content
            assert "simple_item" in content or "SIMPLE_ITEM" in content

    def test_generate_json(self, testing_config: Path, generator: TestingGenerator):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir)
            templates = {"json": "template.json.j2"}

            code_gen = CodeGenerator(generator, output_path)
            filenames = code_gen.generate_from_file(testing_config, templates)

            assert "testconfig.json" in filenames
            json_file = output_path / "testconfig.json"
            assert json_file.exists()

            # Verify valid JSON
            import json

            with open(json_file) as f:
                data = json.load(f)
            assert data["name"] == "TestConfig"
            assert "items" in data

    def test_post_generate_skips_when_no_txt(
        self, testing_config: Path, generator: TestingGenerator
    ):
        """Test that testing_helper.txt is NOT copied when txt is not generated."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir)
            templates = {"json": "template.json.j2"}

            code_gen = CodeGenerator(generator, output_path)
            filenames = code_gen.generate_from_file(testing_config, templates)

            assert "testing_helper.txt" not in filenames
            assert not (output_path / "testing_helper.txt").exists()


# =============================================================================
# Generation Tests - Multi-file Different Extensions
# =============================================================================


class TestMultiFileDifferentExtGeneration:
    """Test multi-file generation with different extensions (.h/.c)."""

    @pytest.fixture
    def testing_config(self) -> Path:
        return Path(__file__).parent / "configs" / "testing" / "full_config.yml"

    @pytest.fixture
    def generator(self) -> TestingGenerator:
        return TestingGenerator()

    def test_generate_c_multi(self, testing_config: Path, generator: TestingGenerator):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir)
            templates = {
                "c.h": "template.c_multi.h.j2",
                "c.c": "template.c_multi.c.j2",
            }

            code_gen = CodeGenerator(generator, output_path)
            filenames = code_gen.generate_from_file(testing_config, templates)

            assert "testconfig.c.h" in filenames
            assert "testconfig.c.c" in filenames

            # Check header file
            header_file = output_path / "testconfig.c.h"
            assert header_file.exists()
            header_content = header_file.read_text()
            assert "#ifndef" in header_content  # Include guard
            assert "TESTCONFIG" in header_content.upper()

            # Check source file
            source_file = output_path / "testconfig.c.c"
            assert source_file.exists()
            source_content = source_file.read_text()
            assert '#include "testconfig.h"' in source_content

    def test_c_multi_header_only(
        self, testing_config: Path, generator: TestingGenerator
    ):
        """Test generating only header from c_multi group."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir)
            templates = {"c.h": "template.c_multi.h.j2"}

            code_gen = CodeGenerator(generator, output_path)
            filenames = code_gen.generate_from_file(testing_config, templates)

            assert "testconfig.c.h" in filenames
            assert "testconfig.c.c" not in filenames


# =============================================================================
# Generation Tests - Multi-file Same Extension
# =============================================================================


class TestMultiFileSameExtGeneration:
    """Test multi-file generation with same extension (.dat.1/.dat.2/.dat.3)."""

    @pytest.fixture
    def testing_config(self) -> Path:
        return Path(__file__).parent / "configs" / "testing" / "full_config.yml"

    @pytest.fixture
    def generator(self) -> TestingGenerator:
        return TestingGenerator()

    def test_generate_dat_multi(
        self, testing_config: Path, generator: TestingGenerator
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir)
            templates = {
                "dat.1": "template.dat_multi.dat.1.j2",
                "dat.2": "template.dat_multi.dat.2.j2",
                "dat.3": "template.dat_multi.dat.3.j2",
            }

            code_gen = CodeGenerator(generator, output_path)
            filenames = code_gen.generate_from_file(testing_config, templates)

            assert "testconfig.dat.1" in filenames
            assert "testconfig.dat.2" in filenames
            assert "testconfig.dat.3" in filenames

            # All files should exist
            for suffix in ["1", "2", "3"]:
                dat_file = output_path / f"testconfig.dat.{suffix}"
                assert dat_file.exists()

    def test_dat_multi_partial(self, testing_config: Path, generator: TestingGenerator):
        """Test generating only some files from dat_multi group."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir)
            templates = {
                "dat.1": "template.dat_multi.dat.1.j2",
                "dat.3": "template.dat_multi.dat.3.j2",
            }

            code_gen = CodeGenerator(generator, output_path)
            filenames = code_gen.generate_from_file(testing_config, templates)

            assert "testconfig.dat.1" in filenames
            assert "testconfig.dat.2" not in filenames
            assert "testconfig.dat.3" in filenames


# =============================================================================
# Generation Tests - All Templates
# =============================================================================


class TestAllTemplatesGeneration:
    """Test generating all template types at once."""

    @pytest.fixture
    def testing_config(self) -> Path:
        return Path(__file__).parent / "configs" / "testing" / "full_config.yml"

    @pytest.fixture
    def generator(self) -> TestingGenerator:
        return TestingGenerator()

    def test_generate_all(self, testing_config: Path, generator: TestingGenerator):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir)
            templates = {
                "txt": "template.txt.j2",
                "json": "template.json.j2",
                "c.h": "template.c_multi.h.j2",
                "c.c": "template.c_multi.c.j2",
                "dat.1": "template.dat_multi.dat.1.j2",
                "dat.2": "template.dat_multi.dat.2.j2",
                "dat.3": "template.dat_multi.dat.3.j2",
            }

            code_gen = CodeGenerator(generator, output_path)
            filenames = code_gen.generate_from_file(testing_config, templates)

            # 7 template outputs + 1 post-generate file
            assert len(filenames) == 8

            expected_files = [
                "testconfig.txt",
                "testconfig.json",
                "testconfig.c.h",
                "testconfig.c.c",
                "testconfig.dat.1",
                "testconfig.dat.2",
                "testconfig.dat.3",
                "testing_helper.txt",
            ]
            for f in expected_files:
                assert f in filenames
                assert (output_path / f).exists()


# =============================================================================
# Edge Cases
# =============================================================================


class TestEdgeCases:
    """Test edge cases for testing domain."""

    def test_empty_items_list(self):
        """Config with no items."""
        cfg = ConfigTesting(name="Empty", items=[])
        assert len(cfg.items) == 0
        assert cfg.item_count == 0

    def test_deeply_nested_children(self):
        """Item with many nested children with tags."""
        children = [
            NestedItem(
                id=i,
                label=f"Child_{i}",
                tags=[Tag(name=f"tag_{j}", value=j) for j in range(5)],
            )
            for i in range(10)
        ]
        item = Item(name="parent", children=children)
        assert len(item.children) == 10
        assert item.tag_count == 50  # 10 children * 5 tags each

    def test_complex_metadata(self):
        """Item with complex metadata dictionary."""
        item = Item(
            name="complex_meta",
            metadata={
                "string": "value",
                "number": 42,
                "float": 3.14,
                "bool": True,
                "list": [1, 2, 3],
                "nested": {"a": 1, "b": 2},
            },
        )
        assert item.metadata["string"] == "value"
        assert item.metadata["nested"]["a"] == 1

    def test_all_item_types(self):
        """Config with all item types."""
        cfg = ConfigTesting(
            name="AllTypes",
            items=[
                Item(name="s", item_type=ItemType.SIMPLE),
                Item(name="c", item_type=ItemType.COMPLEX),
                Item(name="n", item_type=ItemType.NESTED),
            ],
        )
        by_type = cfg.items_by_type
        assert "simple" in by_type
        assert "complex" in by_type
        assert "nested" in by_type

    def test_special_characters_in_name(self):
        """Names with special characters (that get stripped)."""
        item = Item(name="  item_with_underscores  ")
        assert item.name == "item_with_underscores"
        assert item.name_upper == "ITEM_WITH_UNDERSCORES"
