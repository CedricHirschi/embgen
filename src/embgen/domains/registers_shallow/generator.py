"""Register map (shallow) domain generator."""

from datetime import datetime
from pathlib import Path
from typing import Any, cast
import subprocess
import sys

from jinja2 import Environment, Template

from .. import DomainGenerator, BaseConfig
from .models import HjsonEntry, RegistersConfig, RegisterGroup
from .regtool_layout import build_hjson_render_entries, build_layout


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
            else:
                hjson_entries.append(HjsonEntry(kind="register", reg=register))

        config.register_groups = register_groups
        config.hjson_entries = hjson_entries

        return cast(BaseConfig, config)

    def _prepare_template_context(
        self, cfg: RegistersConfig, env: Environment
    ) -> dict[str, Any]:
        layout = build_layout(cfg, env)

        registers = layout.physical_registers
        logical_groups = layout.logical_groups
        logical_group_names = {group.name for group in logical_groups}
        yaml_standalone_addresses = {
            reg.name: reg.address for reg in cfg.regmap_shallow if not reg.count
        }

        standalone_registers = sorted(
            [
                reg.model_copy(
                    update={
                        "address": yaml_standalone_addresses.get(
                            reg.name, reg.address
                        )
                    }
                )
                for reg in registers
                if not (
                    reg.name in logical_group_names
                    or any(
                        reg.name.startswith(f"{group_name}_")
                        for group_name in logical_group_names
                    )
                )
            ],
            key=lambda reg: reg.address,
        )

        for reg in registers:
            reg.bitfields = sorted(reg.bitfields, key=lambda bf: bf.offset)
        for group in logical_groups:
            group.template_bitfields = sorted(
                group.template_bitfields, key=lambda bf: bf.offset
            )
            for inst in group.instances:
                inst.bitfields = sorted(inst.bitfields, key=lambda bf: bf.offset)

        for entry in cfg.hjson_entries:
            if entry.kind == "register" and entry.reg is not None:
                entry.reg.bitfields = sorted(
                    entry.reg.bitfields, key=lambda bf: bf.offset
                )
            elif entry.kind == "multireg" and entry.group is not None:
                entry.group.bitfields = sorted(
                    entry.group.bitfields, key=lambda bf: bf.offset
                )

        bitfields = [bf for reg in registers for bf in reg.bitfields]

        return {
            "name": cfg.name,
            "file": cfg.file,
            "support_file": cfg.support_output_filename,
            "width": cfg.width,
            "regmap": registers,
            "standalone_registers": standalone_registers,
            "logical_groups": logical_groups,
            "register_groups": logical_groups,
            "hjson_entries": build_hjson_render_entries(cfg),
            "bitfields": bitfields,
            "access_separate": cfg.access_separate,
            "generated_on": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "_layout": layout,
        }

    def render(self, config: Any, template: Template) -> str:
        cfg: RegistersConfig = config  # type: narrow
        env = template.environment
        context = self._prepare_template_context(cfg, env)

        if template.name.endswith("template.md.j2"):
            return context["_layout"].markdown

        return template.render(**{k: v for k, v in context.items() if k != "_layout"})

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
                base_template = self.templates_path / "registers_base.py"
                if base_template.exists():
                    dst = output / f"{config.support_output_filename}.py"
                    dst.write_text(base_template.read_text())
                    result.append(f"{config.support_output_filename}.py")

        return result
