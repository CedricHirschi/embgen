import json
from pathlib import Path

import anyconfig
import pytest
import yaml
from pydantic import ValidationError

from embgen.load import Loader
from embgen.plugin import Schema

from .assets.plugins.plugin_ok.schema import PluginOkSchema
from .common import PLUGINS_DIR


class DummySchema(Schema):
    name: str
    values: list[int]
    frequency: int = 16_000_000


class NestedSchema(Schema):
    title: str
    config: DummySchema


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


def test_load_string_path(tmp_path: Path):
    file_path = tmp_path / "config.json"
    file_path.write_text(
        json.dumps({"name": "str_path", "values": [1]}), encoding="utf-8"
    )

    loader = Loader(DummySchema)
    result = loader.load(str(file_path))

    assert result.name == "str_path"
    assert result.values == [1]


@pytest.mark.parametrize("extension", [".JSON", ".YAML", ".YML"])
def test_load_uppercase_extension(tmp_path: Path, extension: str):
    file_path = tmp_path / f"config{extension}"
    data = {"name": "upper", "values": [10]}
    if extension == ".JSON":
        file_path.write_text(json.dumps(data), encoding="utf-8")
    else:
        file_path.write_text(yaml.safe_dump(data), encoding="utf-8")

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

    assert "Unsupported configuration file type" in str(exc_info.value)


def test_load_validation_error(tmp_path: Path):
    file_path = tmp_path / "invalid_schema.json"
    data = {"name": "invalid", "extra_field": "disallowed"}
    file_path.write_text(json.dumps(data), encoding="utf-8")

    loader = Loader(DummySchema)
    with pytest.raises(ValidationError):
        loader.load(file_path)


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


def test_load_multi_merge_strategy(tmp_path: Path):
    base_file = tmp_path / "base.json"
    base_file.write_text(
        json.dumps({"title": "main", "config": {"name": "base_dev", "values": [1]}}),
        encoding="utf-8",
    )

    overlay_file = tmp_path / "overlay.json"
    overlay_file.write_text(
        json.dumps({"config": {"frequency": 48000000}}),
        encoding="utf-8",
    )

    loader = Loader(NestedSchema)
    result = loader.load_multi(
        [base_file, overlay_file], merge_strategy=anyconfig.MS_DICTS
    )

    assert result.title == "main"
    assert result.config.name == "base_dev"
    assert result.config.values == [1]
    assert result.config.frequency == 48000000


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

    assert "Unsupported configuration file type" in str(exc_info.value)


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

    assert "Unsupported format 'unknown_format'" in str(exc_info.value)


def test_load_plugin_ok_asset():
    asset_file = PLUGINS_DIR / "plugin_ok" / "schema.yml"
    loader = Loader(PluginOkSchema)
    result = loader.load(asset_file)

    assert isinstance(result, PluginOkSchema)
    assert result.name == "uwu"
    assert result.greetings == ["hello", "hi"]
