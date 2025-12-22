from datetime import datetime
from pathlib import Path
from typing import Any, cast
from jinja2 import Template
from .. import DomainGenerator, BaseConfig
from .models import CommandsConfig


class CommandsGenerator(DomainGenerator):
    @property
    def name(self) -> str:
        return "commands"

    @property
    def description(self) -> str:
        return "Generate code from command definitions"

    @property
    def templates_path(self) -> Path:
        """Path to this domain's templates."""
        return Path(__file__).parent / "templates"

    def detect(self, data: dict[str, Any]) -> bool:
        return "commands" in data

    def validate(self, data: dict[str, Any]) -> BaseConfig:
        return cast(BaseConfig, CommandsConfig.model_validate(data))

    def render(self, config: Any, template: Template) -> str:
        config: CommandsConfig = config  # type: narrow
        return template.render(
            name=config.name,
            endianness=config.endianness,
            commands=sorted(config.commands, key=lambda c: c.id),
            generated_on=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

    def post_generate(
        self, config: BaseConfig, output: Path, generated_extensions: set[str]
    ) -> list[str]:
        # Only copy commands_base.py when Python output is generated
        if "py" not in generated_extensions:
            return []

        src = self.templates_path / "commands_base.py"
        if src.exists():
            dst = output / (config.output_filename + "_base.py")
            dst.write_text(src.read_text())
            return [config.output_filename + "_base.py"]
        return []
