"""Register map domain generator."""

from datetime import datetime
from pathlib import Path
from typing import Any, cast
from jinja2 import Template

from .. import DomainGenerator, BaseConfig
from .models import RegistersConfig


class RegistersGenerator(DomainGenerator):
    @property
    def name(self) -> str:
        return "registers"

    @property
    def description(self) -> str:
        return "Generate code from register map definitions"

    def detect(self, data: dict[str, Any]) -> bool:
        return "regmap" in data

    def validate(self, data: dict[str, Any]) -> BaseConfig:
        return cast(BaseConfig, RegistersConfig.model_validate(data))

    def render(self, config: Any, template: Template) -> str:
        config: RegistersConfig = config  # type: narrow
        # Sort registers by address
        registers = sorted(config.regmap, key=lambda r: r.address)

        # Sort bitfields within each register
        for reg in registers:
            reg.bitfields = sorted(reg.bitfields, key=lambda bf: bf.offset)

        # Collect all bitfields for templates that need flat access
        bitfields = [bf for reg in registers for bf in reg.bitfields]

        return template.render(
            name=config.name,
            regmap=registers,
            bitfields=bitfields,
            generated_on=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

    def post_generate(
        self, config: BaseConfig, output: Path, generated_extensions: set[str]
    ) -> list[str]:
        # Only copy reg_common.h/.c when C header output is generated
        if "h" not in generated_extensions:
            return []

        header = self.templates_path / "reg_common.h"
        source = self.templates_path / "reg_common.c"

        files_copied = []
        if header.exists():
            dst = output / "reg_common.h"
            dst.write_text(header.read_text())
            files_copied.append("reg_common.h")
        if source.exists():
            dst = output / "reg_common.c"
            dst.write_text(source.read_text())
            files_copied.append("reg_common.c")

        return files_copied
