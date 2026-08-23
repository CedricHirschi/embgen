import json
from pathlib import Path
from typing import Any

import pytest

from embgen.generator import Generator
from embgen.plugin import GeneratedFile, Generator as BaseGenerator, Schema
from embgen.plugins.models import Plugin

from .common import PLUGINS_DIR


class MultiDocSchema(Schema):
    title: str


class MultiDocGenerator(BaseGenerator[MultiDocSchema]):
    def generate(self, input: Any) -> list[GeneratedFile]:
        if isinstance(input, list):
            titles = ", ".join(doc.title for doc in input)
        else:
            titles = input.title
        return [GeneratedFile(path=Path("multi.txt"), content=f"Titles: {titles}")]


@pytest.fixture
def generator(tmp_path: Path) -> Generator:
    return Generator(output_dir=tmp_path, plugin_dirs=[PLUGINS_DIR])


def test_generator_init_discovers_plugins(tmp_path: Path):
    gen = Generator(output_dir=tmp_path, plugin_dirs=[PLUGINS_DIR])
    assert gen.output_dir == tmp_path
    assert "plugin_ok" in gen.plugins
    assert gen.plugins["plugin_ok"].id == "plugin_ok"


def test_generator_init_duplicate_plugin_id(tmp_path: Path):
    with pytest.raises(ValueError) as exc_info:
        Generator(output_dir=tmp_path, plugin_dirs=[PLUGINS_DIR, PLUGINS_DIR])

    assert "Duplicate plugin ID: 'plugin_ok'" in str(exc_info.value)


def test_generate_unknown_plugin_id(generator: Generator):
    with pytest.raises(ValueError) as exc_info:
        generator.generate("unknown_plugin", {"name": "test"})

    assert "Plugin ID not found: unknown_plugin" in str(exc_info.value)


def test_generate_from_path(generator: Generator):
    config_path = PLUGINS_DIR / "plugin_ok" / "schema.yml"
    files = generator.generate("plugin_ok", config_path)

    assert len(files) == 1
    assert files[0].path == Path("output.txt")
    assert isinstance(files[0].content, str)
    assert "Hello, uwu!" in files[0].content
    assert "Hi, uwu!" in files[0].content


def test_generate_from_existing_path_string(generator: Generator):
    config_path_str = str(PLUGINS_DIR / "plugin_ok" / "schema.yml")
    files = generator.generate("plugin_ok", config_path_str)

    assert len(files) == 1
    assert isinstance(files[0].content, str)
    assert "Hello, uwu!" in files[0].content


def test_generate_from_dict(generator: Generator):
    config_dict = {"name": "alice", "greetings": ["welcome", "howdy"]}
    files = generator.generate("plugin_ok", config_dict)

    assert len(files) == 1
    assert isinstance(files[0].content, str)
    assert "Welcome, alice!" in files[0].content
    assert "Howdy, alice!" in files[0].content


def test_generate_from_raw_string_with_format(generator: Generator):
    raw_yaml = "name: bob\ngreetings:\n  - hey\n"
    files = generator.generate("plugin_ok", raw_yaml, format="yaml")

    assert len(files) == 1
    assert isinstance(files[0].content, str)
    assert "Hey, bob!" in files[0].content


def test_generate_from_raw_string_missing_format(generator: Generator):
    raw_yaml = "name: bob\ngreetings:\n  - hey\n"
    with pytest.raises(ValueError) as exc_info:
        generator.generate("plugin_ok", raw_yaml, format=None)

    assert "Format must be specified when loading from a string" in str(exc_info.value)


def test_generate_from_sequence_of_paths(generator: Generator, tmp_path: Path):
    base_file = tmp_path / "base.yml"
    base_file.write_text("name: charlie\ngreetings:\n  - initial\n", encoding="utf-8")

    overlay_file = tmp_path / "overlay.json"
    overlay_file.write_text(json.dumps({"greetings": ["overridden"]}), encoding="utf-8")

    files = generator.generate("plugin_ok", [base_file, overlay_file])

    assert len(files) == 1
    assert isinstance(files[0].content, str)
    assert "Overridden, charlie!" in files[0].content


def test_generate_from_sequence_with_all_flag_raises(
    generator: Generator, tmp_path: Path
):
    base_file = tmp_path / "base.yml"
    base_file.write_text("name: charlie\ngreetings: [hi]\n", encoding="utf-8")

    with pytest.raises(ValueError) as exc_info:
        generator.generate("plugin_ok", [base_file], all=True)

    assert "Cannot use 'all' with a multi-file config" in str(exc_info.value)


def test_generate_invalid_config_type(generator: Generator):
    with pytest.raises(ValueError) as exc_info:
        generator.generate("plugin_ok", 12345)  # type: ignore[arg-type]

    assert "Invalid config type: int. Must be Path, str, dict, or Sequence." in str(
        exc_info.value
    )


# Addition 1: Pass-through templating options (template, context, env)
def test_generate_with_template_and_context(generator: Generator, tmp_path: Path):
    file_path = tmp_path / "templated_config.yml"
    file_path.write_text(
        "name: {{ user_name }}\ngreetings:\n  - {{ custom_greeting }}\n",
        encoding="utf-8",
    )

    files = generator.generate(
        "plugin_ok",
        file_path,
        template=True,
        context={"user_name": "templated_user", "custom_greeting": "hola"},
    )

    assert len(files) == 1
    assert isinstance(files[0].content, str)
    assert "Hola, templated_user!" in files[0].content


def test_generate_with_env_injection(
    generator: Generator, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("TEST_USER_NAME", "env_injected_user")
    file_path = tmp_path / "env_config.yml"
    file_path.write_text(
        "name: {{ TEST_USER_NAME }}\ngreetings:\n  - welcome\n",
        encoding="utf-8",
    )

    files = generator.generate(
        "plugin_ok",
        file_path,
        template=True,
        env=True,
    )

    assert len(files) == 1
    assert isinstance(files[0].content, str)
    assert "Welcome, env_injected_user!" in files[0].content


def test_generate_raw_string_with_template(generator: Generator):
    raw_template = "name: {{ name }}\ngreetings:\n  - {{ greet }}\n"
    files = generator.generate(
        "plugin_ok",
        raw_template,
        format="yaml",
        template=True,
        context={"name": "str_user", "greet": "salutations"},
    )

    assert len(files) == 1
    assert isinstance(files[0].content, str)
    assert "Salutations, str_user!" in files[0].content


def test_generate_multi_file_with_template(generator: Generator, tmp_path: Path):
    base_file = tmp_path / "base.yml"
    base_file.write_text("name: {{ base_name }}\ngreetings: [hi]\n", encoding="utf-8")

    overlay_file = tmp_path / "overlay.json"
    overlay_file.write_text(
        json.dumps({"greetings": ["{{ overlay_greet }}"]}), encoding="utf-8"
    )

    files = generator.generate(
        "plugin_ok",
        [base_file, overlay_file],
        template=True,
        context={"base_name": "multi_user", "overlay_greet": "bonjour"},
    )

    assert len(files) == 1
    assert isinstance(files[0].content, str)
    assert "Bonjour, multi_user!" in files[0].content


# Addition 2: Multi-doc handling with single-item generators
def test_generate_all_with_single_item_generator(generator: Generator, tmp_path: Path):
    multi_file = tmp_path / "multi_boards.yml"
    multi_file.write_text(
        """
name: doc_one
greetings:
  - hello
---
name: doc_two
greetings:
  - greetings
""",
        encoding="utf-8",
    )

    # plugin_ok's generator is designed for a single PluginOkSchema
    files = generator.generate("plugin_ok", multi_file, all=True)

    assert len(files) == 2
    assert isinstance(files[0].content, str)
    assert isinstance(files[1].content, str)
    assert "Hello, doc_one!" in files[0].content
    assert "Greetings, doc_two!" in files[1].content


def test_generate_all_string_with_single_item_generator(generator: Generator):
    raw_multi = """
name: str_doc_one
greetings:
  - hey
---
name: str_doc_two
greetings:
  - howdy
"""
    files = generator.generate("plugin_ok", raw_multi, format="yaml", all=True)

    assert len(files) == 2
    assert isinstance(files[0].content, str)
    assert isinstance(files[1].content, str)
    assert "Hey, str_doc_one!" in files[0].content
    assert "Howdy, str_doc_two!" in files[1].content


def test_generate_all_flag_with_batch_generator(generator: Generator, tmp_path: Path):
    generator.plugins["multi_plugin"] = Plugin.model_validate(
        {
            "id": "multi_plugin",
            "version": "1.0.0",
            "description": "Multi-doc test plugin",
            "contact": {"author": "Tester", "email": "test@example.com"},
        },
        context={
            "generator_class": MultiDocGenerator,
            "schema_class": MultiDocSchema,
        },
    )

    multi_file = tmp_path / "multi.yml"
    multi_file.write_text("title: First\n---\ntitle: Second\n", encoding="utf-8")

    files = generator.generate("multi_plugin", multi_file, all=True)
    # MultiDocGenerator generates 1 file for each document when iterated
    assert len(files) == 2
    assert isinstance(files[0].content, str)
    assert isinstance(files[1].content, str)
    assert "Titles: First" in files[0].content
    assert "Titles: Second" in files[1].content


# Addition 3: Convenience method run()
def test_run_generates_and_writes_files(generator: Generator, tmp_path: Path):
    config_path = PLUGINS_DIR / "plugin_ok" / "schema.yml"
    files = generator.run("plugin_ok", config_path)

    assert len(files) == 1
    output_file = tmp_path / "output.txt"
    assert output_file.exists()
    assert isinstance(files[0].content, str)
    assert output_file.read_text(encoding="utf-8") == files[0].content


def test_run_with_template_and_context(generator: Generator, tmp_path: Path):
    file_path = tmp_path / "run_templated.yml"
    file_path.write_text(
        "name: {{ run_user }}\ngreetings:\n  - {{ run_greeting }}\n",
        encoding="utf-8",
    )

    files = generator.run(
        "plugin_ok",
        file_path,
        template=True,
        context={"run_user": "runner", "run_greeting": "ciao"},
    )

    assert len(files) == 1
    output_file = tmp_path / "output.txt"
    assert output_file.exists()
    assert "Ciao, runner!" in output_file.read_text(encoding="utf-8")


def test_write_text_and_binary_files(generator: Generator, tmp_path: Path):
    files = [
        GeneratedFile(
            path=Path("sub/dir/code.c"), content="int main() { return 0; }\n"
        ),
        GeneratedFile(path=Path("bin/firmware.bin"), content=b"\xde\xad\xbe\xef"),
    ]

    generator.write(files)

    written_text = tmp_path / "sub/dir/code.c"
    written_bin = tmp_path / "bin/firmware.bin"

    assert written_text.exists()
    assert written_text.read_text(encoding="utf-8") == "int main() { return 0; }\n"

    assert written_bin.exists()
    assert written_bin.read_bytes() == b"\xde\xad\xbe\xef"
