from datetime import datetime
from pathlib import Path
from typing import Any, cast
from jinja2 import Template
from .. import DomainGenerator, BaseConfig
from .models import JSONRPCConfig


class JSONRPCGenerator(DomainGenerator):
    @property
    def name(self) -> str:
        return "jsonrpc"

    @property
    def description(self) -> str:
        return "Generate JSON-RPC methods"

    def detect(self, data: dict[str, Any]) -> bool:
        return "methods" in data

    def validate(self, data: dict[str, Any]) -> BaseConfig:
        return cast(BaseConfig, JSONRPCConfig.model_validate(data))

    def render(self, config: Any, template: Template) -> str:  # type: ignore
        config: JSONRPCConfig = config  # type: narrow
        return template.render(
            name=config.name,
            file=config.file,
            support_file=config.support_output_filename,
            methods=sorted(config.methods, key=lambda c: c.name),
            generated_on=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

    def post_generate(
        self, config: BaseConfig, output: Path, generated_extensions: set[str]
    ) -> list[str]:
        config = cast(JSONRPCConfig, config)
        result: list[str] = []

        return result
