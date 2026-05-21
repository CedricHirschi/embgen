"""Register map (shallow) domain generator."""

from datetime import datetime
from pathlib import Path
from typing import Any, cast
import subprocess
import sys

from jinja2 import Template

from .. import DomainGenerator, BaseConfig
from .models import HjsonEntry, RegistersConfig, RegisterGroup


class RegistersGenerator(DomainGenerator):
    @property
    def name(self) -> str:
        return "registers_shallow"

    @property
    def description(self) -> str:
        return "Generate code from register map definitions (shallow)"

    def detect(self, data: dict[str, Any]) -> bool:
        return "regmap_shallow" in data

    def validate(self, data: dict[str, Any]) -> BaseConfig:
        config = RegistersConfig.model_validate(data)
        expanded_registers = []
        register_groups = []
        hjson_entries = []

        for register in config.regmap_shallow:
            if register.count:
                group = RegisterGroup(
                    name=register.name,
                    description=register.description,
                    base_address=register.address,
                    access=register.access,
                    access_hw=register.access_hw,
                    bitfields=register.bitfields,
                    hwqe=register.hwqe,
                    hwext=register.hwext,
                    count=register.count,
                    cname=register.cname,
                    compact=register.compact,
                    regwen_multi=register.regwen_multi,
                )
                register_groups.append(group)
                hjson_entries.append(HjsonEntry(kind="multireg", group=group))

                base_address = register.address
                for i in range(register.count):
                    new_register = register.model_copy()
                    new_register.name = f"{register.name}{i}"
                    new_register.address = base_address + i
                    new_register.count = None
                    new_register.cname = None
                    new_register.compact = None
                    new_register.regwen_multi = False
                    expanded_registers.append(new_register)
            else:
                hjson_entries.append(HjsonEntry(kind="register", reg=register))
                expanded_registers.append(register)

        config.regmap_shallow.clear()
        config.regmap_shallow.extend(expanded_registers)
        config.register_groups = register_groups
        config.hjson_entries = hjson_entries

        return cast(BaseConfig, config)

    def render(self, config: Any, template: Template) -> str:
        cfg: RegistersConfig = config  # type: narrow
        # Sort registers by address
        registers = sorted(cfg.regmap_shallow, key=lambda r: r.address)

        # Sort bitfields within each register
        for reg in registers:
            reg.bitfields = sorted(reg.bitfields, key=lambda bf: bf.offset)

        # Sort bitfields in register groups too
        for group in cfg.register_groups:
            group.bitfields = sorted(group.bitfields, key=lambda bf: bf.offset)

        for entry in cfg.hjson_entries:
            if entry.kind == "register" and entry.reg is not None:
                entry.reg.bitfields = sorted(
                    entry.reg.bitfields, key=lambda bf: bf.offset
                )
            elif entry.kind == "multireg" and entry.group is not None:
                entry.group.bitfields = sorted(
                    entry.group.bitfields, key=lambda bf: bf.offset
                )

        # Collect all bitfields for templates that need flat access
        bitfields = [bf for reg in registers for bf in reg.bitfields]

        return template.render(
            name=cfg.name,
            file=config.file,
            support_file=config.support_output_filename,
            width=cfg.width,
            regmap=registers,
            register_groups=cfg.register_groups,
            hjson_entries=cfg.hjson_entries,
            bitfields=bitfields,
            access_separate=cfg.access_separate,
            generated_on=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

    def post_generate(
        self, config: BaseConfig, output: Path, generated_extensions: set[str]
    ) -> list[str]:
        config = cast(RegistersConfig, config)
        result: list[str] = []

        if "hjson" in generated_extensions:
            hjson_file = output / (config.output_filename + ".hjson")
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
                check=True,
            )
            result.extend(
                [
                    (config.output_filename + "_reg_pkg.sv"),
                    (config.output_filename + "_reg_top.sv"),
                ]
            )

        if config.copy_support_files:
            if "h" in generated_extensions:
                header = self.templates_path / "reg_common.h"
                source = self.templates_path / "reg_common.c"

                files_copied = []
                if header.exists():
                    dst = output / f"{config.support_output_filename}.h"
                    dst.write_text(header.read_text())
                    files_copied.append(f"{config.support_output_filename}.h")
                if source.exists():
                    dst = output / f"{config.support_output_filename}.c"
                    dst.write_text(source.read_text())
                    files_copied.append(f"{config.support_output_filename}.c")

                result.extend(files_copied)

            if "py" in generated_extensions:
                # Copy the register base classes
                base_template = self.templates_path / "registers_base.py"
                if base_template.exists():
                    dst = output / f"{config.support_output_filename}.py"
                    dst.write_text(base_template.read_text())
                    result.append(f"{config.support_output_filename}.py")

        return result
