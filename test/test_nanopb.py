"""Tests for the NanoPB domain."""

import tempfile
from pathlib import Path
from typing import Any

from embgen.discovery import discover_domains
from embgen.generator import CodeGenerator
from embgen.templates import discover_templates


class TestNanoPBGeneration:
    """Test NanoPB generation from config-driven templates."""

    def test_generate_nanopb_outputs_from_config(self):
        """Test that NanoPB templates render from the input config."""
        config_path = Path(__file__).parent / "configs" / "nanopb" / "simple.yml"
        generator = discover_domains()["nanopb"]
        templates, _ = discover_templates(generator.templates_path)

        with tempfile.TemporaryDirectory() as tmpdir:
            code_gen = CodeGenerator(generator, Path(tmpdir))
            filenames = code_gen.generate_from_file(
                config_path,
                {ext: templates[ext][1] for ext in ("proto", "options", "py", "md")},
            )

            assert "telemetry.proto" in filenames
            assert "telemetry.options" in filenames
            assert "telemetry.py" in filenames
            assert "telemetry.md" in filenames

            proto_content = (Path(tmpdir) / "telemetry.proto").read_text()
            assert "package telemetry;" in proto_content
            assert "// Ping the device\nmessage ping_args {" in proto_content
            assert "enum OperatingMode {" in proto_content
            assert "message ping_args {" in proto_content
            assert "message ping_result {" in proto_content
            assert "enum PingStatus {" in proto_content
            assert "PingStatus status = 1; // Ping status" in proto_content
            assert (
                "OperatingMode mode = 1; // Requested operating mode" in proto_content
            )
            assert (
                "OK = 0; // The ping completed successfully\n  ERROR = 1; // The ping failed"
                in proto_content
            )
            assert "repeated response_data data = 2;" in proto_content

            options_content = (Path(tmpdir) / "telemetry.options").read_text()
            assert "telemetry.request.cmd max_count:40" in options_content
            assert "telemetry.response.status max_count:40" in options_content
            assert "telemetry.response.data max_count:40" in options_content

            py_path = Path(tmpdir) / "telemetry.py"
            py_content = py_path.read_text()
            assert (
                '"""Factory for the generated Telemetry NanoPB methods."""'
                in py_content
            )
            assert '"""Requested operating mode"""' in py_content
            assert "MAX_COMMANDS_PER_PACKET = 40" in py_content
            assert "    class OperatingMode(IntEnum):" in py_content
            assert "    class PingStatus(IntEnum):" in py_content
            assert "mode: OperatingMode = OperatingMode.AUTO" in py_content
            assert '"mode": TelemetryMethods.OperatingMode.AUTO' in py_content
            assert (
                "def writefpga(\n"
                "        self,\n"
                "        address: int,\n"
                "        value: int,\n"
                "    ) -> Method:"
            ) in py_content
            assert (
                "Args:\n"
                "            address: Address of the FPGA register to write\n"
                "            value: Value to write to the FPGA register"
            ) in py_content

            namespace: dict[str, Any] = {}
            exec(py_content, namespace)

            methods_class = namespace["TelemetryMethods"]
            methods_factory = methods_class()
            method = methods_factory.setmode()
            assert method.method == "setmode"
            assert method.params == {"mode": 0, "enabled": True}
            assert namespace["method_defaults"]("setmode") == {
                "mode": methods_class.OperatingMode.AUTO,
                "enabled": True,
            }

            md_content = (Path(tmpdir) / "telemetry.md").read_text()
            assert "# NanoPB Methods: Telemetry" in md_content
            assert "| Max Commands Per Packet | 40 |" in md_content
