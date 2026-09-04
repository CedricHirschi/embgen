import io
import os
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path


from embgen.cli import BUILTIN_PLUGINS_DIR, INTERNAL_PLUGINS_DIR, main

from .common import PLUGINS_DIR


def run_cli(*args: str) -> tuple[int, str, str]:
    """Run CLI in-process and capture output.

    Returns:
        tuple of (exit_code, stdout, stderr)
    """
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()

    exit_code = 0
    with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
        try:
            main(list(args))
        except SystemExit as e:
            exit_code = e.code if isinstance(e.code, int) else 1

    return exit_code, stdout_capture.getvalue(), stderr_capture.getvalue()


class TestCLIPluginsDir:
    def test_builtin_plugins_constants(self):
        assert BUILTIN_PLUGINS_DIR.exists()
        assert BUILTIN_PLUGINS_DIR.is_dir()
        assert INTERNAL_PLUGINS_DIR == BUILTIN_PLUGINS_DIR

    def test_cli_list_from_directory_without_plugins(self, tmp_path: Path):
        orig_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            # Ensure no local plugins directory exists in cwd
            assert not (tmp_path / "plugins").exists()

            exit_code, stdout, stderr = run_cli("list")
            assert exit_code == 0
            assert "registers" in stdout
            assert "plugin_ok" in stdout
        finally:
            os.chdir(orig_cwd)

    def test_cli_no_internal_plugins_without_dirs_fails(self):
        exit_code, stdout, stderr = run_cli("--no-internal-plugins", "list")
        assert exit_code == 2
        assert "No plugin directories specified" in stderr

    def test_cli_no_builtin_plugins_without_dirs_fails(self):
        exit_code, stdout, stderr = run_cli("--no-builtin-plugins", "list")
        assert exit_code == 2
        assert "No plugin directories specified" in stderr

    def test_cli_custom_plugins_dir(self, tmp_path: Path):
        custom_dir = tmp_path / "custom_plugin"
        custom_dir.mkdir()
        (custom_dir / "embgen.yml").write_text(
            "id: custom_plugin\nversion: 1.0.0\ndescription: Custom plugin\ncontact:\n  author: Tester\n  email: test@example.com\n"
        )
        (custom_dir / "generator.py").write_text(
            "from embgen.plugin import Generator\nclass CustomGen(Generator):\n    def generate(self, input): return []\n"
        )
        (custom_dir / "schema.py").write_text(
            "from embgen.plugin import Schema\nclass CustomSchema(Schema):\n    name: str\n"
        )

        exit_code, stdout, stderr = run_cli("--plugins-dir", str(tmp_path), "list")
        assert exit_code == 0
        assert "registers" in stdout
        assert "custom_plugin" in stdout

    def test_cli_custom_plugins_dir_with_no_internal(self):
        exit_code, stdout, stderr = run_cli(
            "--no-internal-plugins",
            "--plugins-dir",
            str(PLUGINS_DIR),
            "list",
        )
        assert exit_code == 0
        assert "plugin_ok" in stdout

    def test_cli_info_builtin_plugin(self):
        exit_code, stdout, stderr = run_cli("info", "registers")
        assert exit_code == 0
        assert "Plugin: registers" in stdout
        assert "Register Map Generation" in stdout
