import json
import logging
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from embgen.load import Loader, deep_merge
from embgen.plugin import Schema

from .assets.plugins.plugin_ok.schema import PluginOkSchema
from .common import PLUGINS_DIR


class DummyChildSchema(Schema):
    field_a: str
    field_b: int = 42


class DummySchema(Schema):
    name: str
    values: list[int]
    frequency: int = 16_000_000
    child: DummyChildSchema | None = None


class NestedSchema(Schema):
    title: str
    config: DummySchema


def test_deep_merge():
    base = {"a": 1, "nested": {"x": 10, "y": 20}}
    override = {"b": 2, "nested": {"y": 99, "z": 30}}
    merged = deep_merge(base, override)

    assert merged == {"a": 1, "b": 2, "nested": {"x": 10, "y": 99, "z": 30}}


def test_loader_init():
    loader = Loader(DummySchema)
    assert loader.schema_class is DummySchema


def test_load_dict():
    loader = Loader(DummySchema)
    result = loader.load_dict({"name": "dict_test", "values": [1, 2]})
    assert isinstance(result, DummySchema)
    assert result.name == "dict_test"
    assert result.values == [1, 2]


def test_load_json_file(tmp_path: Path):
    file_path = tmp_path / "config.json"
    data = {"name": "test_json", "values": [1, 2, 3]}
    file_path.write_text(json.dumps(data), encoding="utf-8")

    loader = Loader(DummySchema)
    result = loader.load(file_path)

    assert isinstance(result, DummySchema)
    assert result.name == "test_json"
    assert result.values == [1, 2, 3]


def test_load_yaml_file(tmp_path: Path):
    file_path = tmp_path / "config.yaml"
    data = {"name": "test_yaml", "values": [4, 5, 6]}
    file_path.write_text(yaml.safe_dump(data), encoding="utf-8")

    loader = Loader(DummySchema)
    result = loader.load(file_path)

    assert isinstance(result, DummySchema)
    assert result.name == "test_yaml"
    assert result.values == [4, 5, 6]


def test_load_yml_file(tmp_path: Path):
    file_path = tmp_path / "config.yml"
    data = {"name": "test_yml", "values": [7, 8, 9]}
    file_path.write_text(yaml.safe_dump(data), encoding="utf-8")

    loader = Loader(DummySchema)
    result = loader.load(file_path)

    assert isinstance(result, DummySchema)
    assert result.name == "test_yml"
    assert result.values == [7, 8, 9]


def test_load_toml_file(tmp_path: Path):
    file_path = tmp_path / "config.toml"
    file_path.write_text(
        'name = "test_toml"\nvalues = [11, 22]\nfrequency = 8000000\n',
        encoding="utf-8",
    )

    loader = Loader(DummySchema)
    result = loader.load(file_path)

    assert isinstance(result, DummySchema)
    assert result.name == "test_toml"
    assert result.values == [11, 22]
    assert result.frequency == 8_000_000


def test_load_hjson_file(tmp_path: Path):
    file_path = tmp_path / "config.hjson"
    file_path.write_text(
        """
        # HJSON with comments and unquoted keys
        name: test_hjson
        values: [
            33
            44
        ]
        frequency: 12000000
        """,
        encoding="utf-8",
    )

    loader = Loader(DummySchema)
    result = loader.load(file_path)

    assert isinstance(result, DummySchema)
    assert result.name == "test_hjson"
    assert result.values == [33, 44]
    assert result.frequency == 12_000_000


def test_load_string_path(tmp_path: Path):
    file_path = tmp_path / "config.json"
    file_path.write_text(
        json.dumps({"name": "str_path", "values": [1]}), encoding="utf-8"
    )

    loader = Loader(DummySchema)
    result = loader.load(str(file_path))

    assert result.name == "str_path"
    assert result.values == [1]


@pytest.mark.parametrize("extension", [".JSON", ".YAML", ".YML", ".TOML", ".HJSON"])
def test_load_uppercase_extension(tmp_path: Path, extension: str):
    file_path = tmp_path / f"config{extension}"
    if extension == ".JSON":
        file_path.write_text(
            json.dumps({"name": "upper", "values": [10]}), encoding="utf-8"
        )
    elif extension == ".TOML":
        file_path.write_text('name = "upper"\nvalues = [10]\n', encoding="utf-8")
    elif extension == ".HJSON":
        file_path.write_text("name: upper\nvalues: [10]\n", encoding="utf-8")
    else:
        file_path.write_text(
            yaml.safe_dump({"name": "upper", "values": [10]}), encoding="utf-8"
        )

    loader = Loader(DummySchema)
    result = loader.load(file_path)

    assert result.name == "upper"
    assert result.values == [10]


def test_load_utf8_content(tmp_path: Path):
    file_path = tmp_path / "config_utf8.json"
    data = {"name": "🚀 üñïçödé", "values": [1]}
    file_path.write_text(json.dumps(data), encoding="utf-8")

    loader = Loader(DummySchema)
    result = loader.load(file_path)

    assert result.name == "🚀 üñïçödé"


def test_load_nonexistent_file(tmp_path: Path):
    file_path = tmp_path / "nonexistent.yaml"
    loader = Loader(DummySchema)

    with pytest.raises(FileNotFoundError) as exc_info:
        loader.load(file_path)

    assert f"File not found: {file_path.as_posix()}" in str(exc_info.value)


def test_load_directory_raises_error(tmp_path: Path):
    dir_path = tmp_path / "a_directory"
    dir_path.mkdir()
    loader = Loader(DummySchema)

    with pytest.raises(IsADirectoryError) as exc_info:
        loader.load(dir_path)

    assert f"Path is not a file: {dir_path.as_posix()}" in str(exc_info.value)


def test_load_unsupported_extension(tmp_path: Path):
    file_path = tmp_path / "config.unknownext"
    file_path.write_text("dummy content", encoding="utf-8")
    loader = Loader(DummySchema)

    with pytest.raises(ValueError) as exc_info:
        loader.load(file_path)

    assert "Unsupported configuration format: '.unknownext'" in str(exc_info.value)


def test_load_validation_error(tmp_path: Path, caplog: pytest.LogCaptureFixture):
    file_path = tmp_path / "invalid_schema.json"
    data = {"name": "invalid", "extra_field": "disallowed"}
    file_path.write_text(json.dumps(data), encoding="utf-8")

    loader = Loader(DummySchema)
    with caplog.at_level(logging.ERROR):
        with pytest.raises(ValidationError):
            loader.load(file_path)

    assert "validation error" in caplog.text


def test_load_templated_file(tmp_path: Path):
    file_path = tmp_path / "config.yml"
    file_path.write_text(
        """
name: {{ device_name }}
values:
  - {{ first_val }}
  - 20
frequency: {{ freq }}
""",
        encoding="utf-8",
    )

    loader = Loader(DummySchema)
    result = loader.load(
        file_path,
        template=True,
        context={
            "device_name": "templated_device",
            "first_val": 10,
            "freq": 32_000_000,
        },
    )

    assert result.name == "templated_device"
    assert result.values == [10, 20]
    assert result.frequency == 32_000_000


# In-file includes (!include, !inc, $include, $ref)
def test_load_yaml_include_directive(tmp_path: Path):
    sub_file = tmp_path / "sub_child.yml"
    sub_file.write_text("field_a: included_child\nfield_b: 99\n", encoding="utf-8")

    main_file = tmp_path / "main.yml"
    main_file.write_text(
        """
name: parent_device
values: [1, 2]
child: !include sub_child.yml
""",
        encoding="utf-8",
    )

    loader = Loader(DummySchema)
    result = loader.load(main_file)

    assert result.name == "parent_device"
    assert result.child is not None
    assert result.child.field_a == "included_child"
    assert result.child.field_b == 99


def test_load_yaml_inc_directive(tmp_path: Path):
    sub_file = tmp_path / "sub_child.yml"
    sub_file.write_text("field_a: inc_tag_child\nfield_b: 77\n", encoding="utf-8")

    main_file = tmp_path / "main.yml"
    main_file.write_text(
        """
name: parent_device
values: [10]
child: !inc sub_child.yml
""",
        encoding="utf-8",
    )

    loader = Loader(DummySchema)
    result = loader.load(main_file)

    assert result.child is not None
    assert result.child.field_a == "inc_tag_child"
    assert result.child.field_b == 77


def test_load_json_include_and_ref(tmp_path: Path):
    child_json = tmp_path / "child.json"
    child_json.write_text(
        json.dumps({"field_a": "json_ref_child", "field_b": 88}), encoding="utf-8"
    )

    main_json = tmp_path / "main.json"
    main_json.write_text(
        json.dumps(
            {
                "name": "json_parent",
                "values": [5, 6],
                "child": {"$ref": "child.json"},
            }
        ),
        encoding="utf-8",
    )

    loader = Loader(DummySchema)
    result = loader.load(main_json)

    assert result.name == "json_parent"
    assert result.child is not None
    assert result.child.field_a == "json_ref_child"
    assert result.child.field_b == 88


def test_load_hjson_include(tmp_path: Path):
    child_hjson = tmp_path / "child.hjson"
    child_hjson.write_text("field_a: hjson_child\nfield_b: 55\n", encoding="utf-8")

    main_hjson = tmp_path / "main.hjson"
    main_hjson.write_text(
        """
        name: hjson_parent
        values: [1, 2]
        child: {
            $include: child.hjson
        }
        """,
        encoding="utf-8",
    )

    loader = Loader(DummySchema)
    result = loader.load(main_hjson)

    assert result.child is not None
    assert result.child.field_a == "hjson_child"
    assert result.child.field_b == 55


def test_load_cyclic_include(tmp_path: Path):
    file_a = tmp_path / "file_a.yml"
    file_b = tmp_path / "file_b.yml"

    file_a.write_text(
        "name: a\nvalues: [1]\nchild: !include file_b.yml\n", encoding="utf-8"
    )
    file_b.write_text("field_a: b\nfield_b: !include file_a.yml\n", encoding="utf-8")

    loader = Loader(DummySchema)
    with pytest.raises(ValueError) as exc_info:
        loader.load(file_a)

    assert "Cyclic include detected" in str(exc_info.value)


def test_load_missing_included_file(tmp_path: Path):
    main_file = tmp_path / "main.yml"
    main_file.write_text(
        "name: a\nvalues: [1]\nchild: !include nonexistent_sub.yml\n",
        encoding="utf-8",
    )

    loader = Loader(DummySchema)
    with pytest.raises(FileNotFoundError) as exc_info:
        loader.load(main_file)

    assert "Included file not found" in str(exc_info.value)


# Automatic Environment Variable Injection
def test_load_with_environment_variables(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("EMBGEN_TEST_DEVICE", "env_injected_device")
    monkeypatch.setenv("EMBGEN_TEST_FREQ", "64000000")

    file_path = tmp_path / "env_config.yml"
    file_path.write_text(
        """
name: {{ EMBGEN_TEST_DEVICE }}
values: [1, 2]
frequency: {{ EMBGEN_TEST_FREQ }}
""",
        encoding="utf-8",
    )

    loader = Loader(DummySchema)
    result = loader.load(file_path, template=True)

    assert result.name == "env_injected_device"
    assert result.frequency == 64_000_000


def test_load_with_env_override_by_context(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("EMBGEN_DEVICE", "env_name")

    file_path = tmp_path / "config.yml"
    file_path.write_text("name: {{ EMBGEN_DEVICE }}\nvalues: [1]", encoding="utf-8")

    loader = Loader(DummySchema)
    result = loader.load(
        file_path,
        template=True,
        context={"EMBGEN_DEVICE": "explicit_context_override"},
    )

    assert result.name == "explicit_context_override"


def test_load_with_env_disabled(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("MY_VAR", "visible_only_if_env_true")

    file_path = tmp_path / "config.yml"
    file_path.write_text(
        "name: {{ MY_VAR | default('fallback') }}\nvalues: [1]", encoding="utf-8"
    )

    loader = Loader(DummySchema)
    result = loader.load(file_path, template=True, env=False)

    assert result.name == "fallback"


# Multi-Document YAML (load_all, load_all_string)
def test_load_all_yaml_file(tmp_path: Path):
    file_path = tmp_path / "multi.yml"
    file_path.write_text(
        """
name: doc1
values: [1, 2]
frequency: 1000
---
name: doc2
values: [3, 4]
frequency: 2000
---
name: doc3
values: [5, 6]
frequency: 3000
""",
        encoding="utf-8",
    )

    loader = Loader(DummySchema)
    results = loader.load_all(file_path)

    assert len(results) == 3
    assert [r.name for r in results] == ["doc1", "doc2", "doc3"]
    assert [r.frequency for r in results] == [1000, 2000, 3000]


def test_load_all_string_with_template():
    content = """
name: {{ prefix }}_1
values: [1]
---
name: {{ prefix }}_2
values: [2]
"""
    loader = Loader(DummySchema)
    results = loader.load_all_string(
        content,
        format="yaml",
        template=True,
        context={"prefix": "item"},
    )

    assert len(results) == 2
    assert results[0].name == "item_1"
    assert results[1].name == "item_2"


def test_load_all_unsupported_format(tmp_path: Path):
    file_path = tmp_path / "multi.unsupported"
    file_path.write_text("dummy", encoding="utf-8")

    loader = Loader(DummySchema)
    with pytest.raises(ValueError) as exc_info:
        loader.load_all(file_path)

    assert "Unsupported format for multi-document loading" in str(exc_info.value)


# Multi-File & String Loading
def test_load_multi_files(tmp_path: Path):
    base_file = tmp_path / "base.yml"
    base_file.write_text(
        """
name: base_name
values:
  - 1
  - 2
frequency: 1000
""",
        encoding="utf-8",
    )

    overlay_file = tmp_path / "overlay.json"
    overlay_file.write_text(
        json.dumps({"values": [3, 4], "frequency": 8000}),
        encoding="utf-8",
    )

    loader = Loader(DummySchema)
    result = loader.load_multi([base_file, overlay_file])

    assert result.name == "base_name"
    assert result.values == [3, 4]
    assert result.frequency == 8000


def test_load_multi_mixed_formats(tmp_path: Path):
    yaml_file = tmp_path / "base.yaml"
    yaml_file.write_text(
        "title: base_title\nconfig:\n  name: dev\n  values: [1]\n", encoding="utf-8"
    )

    toml_file = tmp_path / "overlay.toml"
    toml_file.write_text("[config]\nfrequency = 48000000\n", encoding="utf-8")

    loader = Loader(NestedSchema)
    result = loader.load_multi([yaml_file, toml_file])

    assert result.title == "base_title"
    assert result.config.name == "dev"
    assert result.config.values == [1]
    assert result.config.frequency == 48_000_000


def test_load_multi_nonexistent_file(tmp_path: Path):
    file1 = tmp_path / "file1.yml"
    file1.write_text("name: test\nvalues: [1]", encoding="utf-8")
    file2 = tmp_path / "missing.yml"

    loader = Loader(DummySchema)
    with pytest.raises(FileNotFoundError) as exc_info:
        loader.load_multi([file1, file2])

    assert f"File not found: {file2.as_posix()}" in str(exc_info.value)


def test_load_multi_unsupported_type(tmp_path: Path):
    file1 = tmp_path / "file1.yml"
    file1.write_text("name: test\nvalues: [1]", encoding="utf-8")
    file2 = tmp_path / "file2.unsupported"
    file2.write_text("dummy", encoding="utf-8")

    loader = Loader(DummySchema)
    with pytest.raises(ValueError) as exc_info:
        loader.load_multi([file1, file2])

    assert "Unsupported configuration format: '.unsupported'" in str(exc_info.value)


def test_load_multi_with_template(tmp_path: Path):
    base_file = tmp_path / "base.yml"
    base_file.write_text("name: {{ base_name }}\nvalues: [1]", encoding="utf-8")
    overlay_file = tmp_path / "overlay.yml"
    overlay_file.write_text("values: [{{ overlay_val }}]", encoding="utf-8")

    loader = Loader(DummySchema)
    result = loader.load_multi(
        [base_file, overlay_file],
        template=True,
        context={"base_name": "rendered_base", "overlay_val": 99},
    )

    assert result.name == "rendered_base"
    assert result.values == [99]


def test_load_string_yaml():
    content = """
name: string_yaml
values:
  - 100
  - 200
"""
    loader = Loader(DummySchema)
    result = loader.load_string(content, format="yaml")

    assert result.name == "string_yaml"
    assert result.values == [100, 200]


def test_load_string_json():
    content = json.dumps({"name": "string_json", "values": [300]})
    loader = Loader(DummySchema)
    result = loader.load_string(content, format=".json")

    assert result.name == "string_json"
    assert result.values == [300]


def test_load_string_toml():
    content = 'name = "string_toml"\nvalues = [400]\n'
    loader = Loader(DummySchema)
    result = loader.load_string(content, format="toml")

    assert result.name == "string_toml"
    assert result.values == [400]


def test_load_string_hjson():
    content = "name: string_hjson\nvalues: [500]\n"
    loader = Loader(DummySchema)
    result = loader.load_string(content, format="hjson")

    assert result.name == "string_hjson"
    assert result.values == [500]


def test_load_string_with_template():
    content = "name: {{ name }}\nvalues: [{{ val }}]"
    loader = Loader(DummySchema)
    result = loader.load_string(
        content,
        format="yaml",
        template=True,
        context={"name": "templated_str", "val": 42},
    )

    assert result.name == "templated_str"
    assert result.values == [42]


def test_load_string_unsupported_format():
    loader = Loader(DummySchema)
    with pytest.raises(ValueError) as exc_info:
        loader.load_string("dummy", format="unknown_format")

    assert "Unsupported configuration format: 'unknown_format'" in str(exc_info.value)


def test_load_plugin_ok_asset():
    asset_file = PLUGINS_DIR / "plugin_ok" / "schema.yml"
    loader = Loader(PluginOkSchema)
    result = loader.load(asset_file)

    assert isinstance(result, PluginOkSchema)
    assert result.name == "uwu"
    assert result.greetings == ["hello", "hi"]
