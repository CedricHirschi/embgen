"""Demo showing configuration loading across all formats and features."""

import os
from pathlib import Path

from embgen.common import setup_logging
from embgen.load import Loader
from embgen.plugin import Schema

log = setup_logging("DEBUG")

CONFIGS_DIR = Path(__file__).parent / "configs"


class BoardConfig(Schema):
    name: str
    version: str
    frequency_hz: int = 16_000_000
    features: list[str] = []


loader = Loader(BoardConfig)

# 1. Single File Loading (YAML)
config_yaml = loader.load(CONFIGS_DIR / "base.yml")
log.info(f"1. Loaded single YAML: {config_yaml}")

# 2. HJSON Loading (with comments & unquoted keys)
config_hjson = loader.load(CONFIGS_DIR / "comments.hjson")
log.info(f"2. Loaded HJSON with comments: {config_hjson}")

# 3. In-File Include Directive (!include)
config_include = loader.load(CONFIGS_DIR / "with_include.yml")
log.info(f"3. Loaded YAML with !include: {config_include}")

# 4. Multi-File Overlay Merging (YAML base + TOML overlay)
merged_config = loader.load_multi(
    [CONFIGS_DIR / "base.yml", CONFIGS_DIR / "overlay.toml"]
)
log.info(f"4. Merged YAML base + TOML overlay: {merged_config}")

# 5. Jinja2 Templated Config Loading (with environment injection)
os.environ["ENV_FEATURE"] = "ethernet_gigabit"
templated_config = loader.load(
    CONFIGS_DIR / "templated.json",
    template=True,
    context={"device_name": "samd21", "major": 3, "minor": 1, "freq": 48_000_000},
)
log.info(f"5. Loaded Jinja2 templated config with env: {templated_config}")

# 6. Multi-Document YAML Loading (load_all)
all_docs = loader.load_all(CONFIGS_DIR / "multi_doc.yml")
log.info(f"6. Loaded multi-document YAML ({len(all_docs)} documents): {all_docs}")

# 7. In-Memory String Loading (TOML)
raw_toml = """
name = "esp32_s3"
version = "1.0.0"
frequency_hz = 240000000
features = ["wifi", "bluetooth_le"]
"""
string_config = loader.load_string(raw_toml, format="toml")
log.info(f"7. Loaded from in-memory TOML string: {string_config}")
