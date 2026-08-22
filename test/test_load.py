import json
from pathlib import Path

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


def test_loader_init():
    loader = Loader(DummySchema)
    assert loader.schema_class is DummySchema


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
    file_path = tmp_path / "config.toml"
    file_path.write_text("name = 'test'", encoding="utf-8")
    loader = Loader(DummySchema)

    with pytest.raises(ValueError) as exc_info:
        loader.load(file_path)

    assert "Unsupported file extension: .toml" in str(exc_info.value)


def test_load_unimplemented_loader(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    file_path = tmp_path / "config.custom"
    file_path.write_text("dummy content", encoding="utf-8")

    custom_extensions = dict(Loader.EXTENSIONS)
    custom_extensions[".custom"] = "non_existent_method_name"
    monkeypatch.setattr(Loader, "EXTENSIONS", custom_extensions)

    loader = Loader(DummySchema)
    with pytest.raises(NotImplementedError) as exc_info:
        loader.load(file_path)

    assert "Loader for .custom is not implemented" in str(exc_info.value)


def test_load_validation_error(tmp_path: Path):
    file_path = tmp_path / "invalid_schema.json"
    data = {"name": "invalid", "extra_field": "disallowed"}
    file_path.write_text(json.dumps(data), encoding="utf-8")

    loader = Loader(DummySchema)
    with pytest.raises(ValidationError):
        loader.load(file_path)


def test_load_invalid_json(tmp_path: Path):
    file_path = tmp_path / "malformed.json"
    file_path.write_text("{ unclosed json: ", encoding="utf-8")

    loader = Loader(DummySchema)
    with pytest.raises(json.JSONDecodeError):
        loader.load(file_path)


def test_load_invalid_yaml(tmp_path: Path):
    file_path = tmp_path / "malformed.yaml"
    file_path.write_text(":\n  - :\n  bad yaml: [", encoding="utf-8")

    loader = Loader(DummySchema)
    with pytest.raises(yaml.YAMLError):
        loader.load(file_path)


def test_load_plugin_ok_asset():
    asset_file = PLUGINS_DIR / "plugin_ok" / "schema.yml"
    loader = Loader(PluginOkSchema)
    result = loader.load(asset_file)

    assert isinstance(result, PluginOkSchema)
    assert result.name == "uwu"
    assert result.greetings == ["hello", "hi"]
