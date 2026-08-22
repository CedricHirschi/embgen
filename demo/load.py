"""Demo showing configuration loading and multi-file merging using AnyconfigLoader."""

import tempfile
from pathlib import Path

from embgen.common import setup_logging
from embgen.load import Loader
from embgen.plugin import Schema

log = setup_logging("DEBUG")


class BoardConfig(Schema):
    name: str
    version: str
    frequency_hz: int = 16_000_000
    features: list[str] = []


loader = Loader(BoardConfig)

with tempfile.TemporaryDirectory() as tmp_dir:
    tmp_path = Path(tmp_dir)

    # 1. Basic Single File Loading (YAML)
    base_file = tmp_path / "base.yml"
    base_file.write_text(
        """
name: stm32_core
version: 1.0.0
frequency_hz: 16000000
features:
  - uart
  - spi
""",
        encoding="utf-8",
    )

    config1 = loader.load(base_file)
    log.info(f"1. Loaded single YAML file: {config1}")

    # 2. Multi-File Overlay Merging (Base YAML + Board Overlay JSON)
    overlay_file = tmp_path / "board_overlay.json"
    overlay_file.write_text(
        """{
  "version": "2.0.0",
  "frequency_hz": 80000000,
  "features": ["i2c", "can"]
}""",
        encoding="utf-8",
    )

    merged_config = loader.load_multi([base_file, overlay_file])
    log.info(f"2. Merged YAML base + JSON overlay: {merged_config}")

    # 3. Jinja2 Templated Config Loading
    template_file = tmp_path / "templated.json"
    template_file.write_text(
        """{
  "name": "{{ device_name }}",
  "version": "{{ major }}.{{ minor }}.0",
  "frequency_hz": {{ freq }}
}""",
        encoding="utf-8",
    )

    templated_config = loader.load(
        template_file,
        template=True,
        context={
            "device_name": "samd21",
            "major": 3,
            "minor": 1,
            "freq": 48_000_000,
        },
    )
    log.info(f"3. Loaded Jinja2 templated config: {templated_config}")

    # 4. In-Memory String Loading
    raw_yaml = """
name: esp32
version: 1.2.3
frequency_hz: 240000000
features:
  - wifi
  - bluetooth
"""
    string_config = loader.load_string(raw_yaml, format="yaml")
    log.info(f"4. Loaded from raw string: {string_config}")
