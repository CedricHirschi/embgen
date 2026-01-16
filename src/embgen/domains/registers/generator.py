"""Register map domain generator."""

from datetime import datetime
from pathlib import Path
from typing import Any, cast
import subprocess
import sys

from jinja2 import Template

from .. import DomainGenerator, BaseConfig
from .models import RegistersConfig, RegisterGroup


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
        config = RegistersConfig.model_validate(data)
        expanded_registers = []
        register_groups = []

        for register in config.regmap:
            if register.numbers:
                # Create a RegisterGroup for this numbered register
                group = RegisterGroup(
                    name=register.name,
                    description=register.description,
                    base_address=register.address,
                    access=register.access,
                    bitfields=register.bitfields,
                    numbers=register.numbers,
                )
                register_groups.append(group)

                # Also expand individual registers for backward compatibility
                base_address = register.address
                for i, number in enumerate(register.numbers):
                    new_register = register.model_copy()
                    new_register.name = f"{register.name}{number}"
                    new_register.address = base_address + i
                    new_register.numbers = None  # Clear numbers on expanded register
                    expanded_registers.append(new_register)
            else:
                expanded_registers.append(register)

        # Clear the original regmap and extend it with the new registers
        config.regmap.clear()
        config.regmap.extend(expanded_registers)
        config.register_groups = register_groups

        return cast(BaseConfig, config)

    def render(self, config: Any, template: Template) -> str:
        cfg: RegistersConfig = config  # type: narrow
        # Sort registers by address
        registers = sorted(cfg.regmap, key=lambda r: r.address)

        # Sort bitfields within each register
        for reg in registers:
            reg.bitfields = sorted(reg.bitfields, key=lambda bf: bf.offset)

        # Sort bitfields in register groups too
        for group in cfg.register_groups:
            group.bitfields = sorted(group.bitfields, key=lambda bf: bf.offset)

        # Collect all bitfields for templates that need flat access
        bitfields = [bf for reg in registers for bf in reg.bitfields]

        return template.render(
            name=cfg.name,
            width=cfg.width,
            regmap=registers,
            register_groups=cfg.register_groups,
            bitfields=bitfields,
            access_separate=cfg.access_separate,
            generated_on=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

    def post_generate(
        self, config: BaseConfig, output: Path, generated_extensions: set[str]
    ) -> list[str]:
        # Only copy reg_common.h/.c when C header output is generated
        if "hjson" in generated_extensions:
            hjson_file = output / (config.file or config.name.lower() + ".hjson")
            subprocess.run(
                [
                    sys.executable,
                    "regtool.py",
                    "-r",
                    "-t",
                    output.as_posix(),
                    hjson_file.as_posix(),
                ],
                cwd=Path(__file__).parent / "regtool",
            )
            return [
                (config.file or config.name.lower() + "_reg_pkg.hjson"),
                (config.file or config.name.lower() + "_reg_top.hjson"),
            ]

        elif "h" not in generated_extensions:
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
