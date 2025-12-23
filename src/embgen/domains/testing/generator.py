"""Generator for the testing domain."""

from pathlib import Path
from typing import Any, cast

from jinja2 import Template

from .. import BaseConfig, DomainGenerator
from .models import ConfigTesting


class TestingGenerator(DomainGenerator):
    """Generator for testing domain.

    This generator is designed to test all embgen features:
    - Domain detection
    - Config validation
    - Template rendering
    - Post-generate hooks
    - Single and multi-file output
    """

    @property
    def name(self) -> str:
        return "testing"

    @property
    def description(self) -> str:
        return "Testing domain for embgen test suite"

    @property
    def templates_path(self) -> Path:
        return Path(__file__).parent / "templates"

    def detect(self, data: dict[str, Any]) -> bool:
        """Detect testing domain by presence of 'items' key."""
        return "items" in data and "commands" not in data and "regmap" not in data

    def validate(self, data: dict[str, Any]) -> BaseConfig:
        """Validate and return TestingConfig."""
        return cast(BaseConfig, ConfigTesting.model_validate(data))

    def render(self, config: Any, template: Template) -> str:
        """Render a template with the testing config."""
        cfg: ConfigTesting = config
        return template.render(
            # Basic config
            name=cfg.name,
            file=cfg.file,
            output_filename=cfg.output_filename,
            version=cfg.version,
            description=cfg.description,
            # Items
            items=cfg.items,
            item_count=cfg.item_count,
            enabled_items=cfg.enabled_items,
            items_by_type=cfg.items_by_type,
            # Global data
            global_tags=cfg.global_tags,
            settings=cfg.settings,
            # Full config for advanced templates
            config=cfg,
        )

    def post_generate(
        self, config: BaseConfig, output: Path, generated_extensions: set[str]
    ) -> list[str]:
        """Post-generation hook - copy helper file when .txt is generated."""
        if "txt" not in generated_extensions:
            return []

        # Copy a helper file as post-generate test
        helper_src = self.templates_path / "testing_helper.txt"
        if helper_src.exists():
            helper_dst = output / "testing_helper.txt"
            helper_dst.write_text(helper_src.read_text())
            return ["testing_helper.txt"]
        return []
