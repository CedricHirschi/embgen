from pathlib import Path

from embgen.common import setup_logging
from embgen.generator import Generator
from embgen.plugins.discover import BUILTIN_PLUGINS_DIR

OUTPUT_DIR = Path(__file__).parent / "output"
PLUGINS_DIR = BUILTIN_PLUGINS_DIR

log = setup_logging("DEBUG")

gen = Generator(OUTPUT_DIR, [PLUGINS_DIR])
files = gen.generate("plugin_ok", PLUGINS_DIR / "plugin_ok" / "schema.yml")

log.info(f"Generated {len(files)} files")
for file in files:
    log.info(f"Generated file: {file.path.as_posix()}")
    log.info(f"Content:\n{file.content}")

gen.write(files)
