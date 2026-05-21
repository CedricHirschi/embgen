"""Expand register maps through vendored regtool for physical layout."""

from __future__ import annotations

import io
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

from jinja2 import Environment, Template

from ...models import Enum as EmbgenEnum
from .models import Access, BitField, HjsonEntry, LogicalGroup, LogicalInstance, Register

if TYPE_CHECKING:
    from .models import RegistersConfig

_REGTOOL_PATH = Path(__file__).parent / "regtool"


def _ensure_regtool_importable() -> None:
    path = str(_REGTOOL_PATH)
    if path not in sys.path:
        sys.path.insert(0, path)


def _swaccess_to_access(key: str) -> Access:
    mapping = {
        "ro": Access.RO,
        "rw": Access.RW,
        "wo": Access.WO,
        "w1c": Access.RWC,
        "wosc": Access.WOS,
        "w0c": Access.WOS,
        "w1s": Access.RW,
        "r0w1c": Access.RWC,
        "rc": Access.RO,
        "none": Access.RW,
    }
    try:
        return mapping[key]
    except KeyError as exc:
        raise ValueError(f"Unsupported regtool swaccess value: {key!r}") from exc


def _convert_field(reggen_field: Any) -> BitField:
    reset = 0 if reggen_field.resval is None else reggen_field.resval
    enums: Optional[list[EmbgenEnum]] = None
    if reggen_field.enum is not None:
        enums = [
            EmbgenEnum(name=e.name, value=e.value, description=e.desc or "")
            for e in reggen_field.enum
        ]
    return BitField(
        name=reggen_field.name,
        description=reggen_field.desc,
        reset=reset,
        width=reggen_field.bits.width(),
        offset=reggen_field.bits.lsb,
        enums=enums,
    )


def _convert_register(reggen_reg: Any) -> Register:
    return Register(
        name=reggen_reg.name,
        description=reggen_reg.desc,
        address=reggen_reg.offset,
        access=_swaccess_to_access(reggen_reg.swaccess.key),
        bitfields=[_convert_field(f) for f in reggen_reg.fields],
    )


def _multireg_slots(entry: HjsonEntry, regwidth: int) -> int:
    if entry.kind != "multireg" or entry.group is None:
        return 1
    group = entry.group
    compact = (
        group.compact
        if group.compact is not None
        else len(group.bitfields) == 1
    )
    if compact and len(group.bitfields) == 1:
        field_width = group.bitfields[0].width
        regs_per_creg = regwidth // field_width
        return (group.count + regs_per_creg - 1) // regs_per_creg
    return group.count


def build_hjson_render_entries(config: RegistersConfig) -> list[dict[str, Any]]:
    """Build hjson template entries, inserting skipto for address gaps."""
    addrsep = config.width // 8
    entries: list[dict[str, Any]] = []
    next_slot = 0

    for entry in config.hjson_entries:
        slot = (
            entry.reg.address
            if entry.kind == "register" and entry.reg is not None
            else entry.group.base_address
            if entry.kind == "multireg" and entry.group is not None
            else 0
        )
        if slot > next_slot:
            entries.append({"kind": "skipto", "offset": slot * addrsep})
        elif slot < next_slot:
            raise ValueError(
                f"Register slot {slot} overlaps previous entries ending at slot {next_slot - 1}"
            )

        entries.append({"kind": entry.kind, "entry": entry})
        next_slot = slot + _multireg_slots(entry, config.width)

    return entries


def render_hjson(config: RegistersConfig, env: Environment) -> str:
    """Render hjson with skipto entries to honour YAML register slot addresses."""
    template = env.get_template("template.hjson.j2")
    return template.render(
        name=config.name,
        width=config.width,
        hjson_entries=build_hjson_render_entries(config),
        access_separate=config.access_separate,
    )


def _load_ip_block(hjson_text: str) -> Any:
    _ensure_regtool_importable()
    from reggen.ip_block import IpBlock

    return IpBlock.from_text(hjson_text, [], "embgen generated hjson")


def render_markdown(block: Any) -> str:
    _ensure_regtool_importable()
    from reggen.gen_md import gen_md

    out = io.StringIO()
    gen_md(block, out)
    return out.getvalue()


@dataclass
class RegtoolLayout:
    block: Any
    physical_registers: list[Register] = field(default_factory=list)
    logical_groups: list[LogicalGroup] = field(default_factory=list)
    markdown: str = ""


def _build_logical_groups(
    block: Any,
    yaml_groups: list[Any],
    regwidth: int,
) -> list[LogicalGroup]:
    _ensure_regtool_importable()
    from reggen.gen_md import multireg_is_compact
    from reggen.multi_register import MultiRegister

    yaml_by_name = {g.name: g for g in yaml_groups}
    logical_groups: list[LogicalGroup] = []

    reg_block = block.reg_blocks[None]
    for entry in reg_block.entries:
        if not isinstance(entry, MultiRegister):
            continue
        yaml_group = yaml_by_name.get(entry.reg.name)
        if yaml_group is None:
            continue

        instances: list[LogicalInstance] = []

        if multireg_is_compact(entry, regwidth):
            base_field = entry.reg.fields[0].name
            for reg in entry.regs:
                for bf in reg.fields:
                    suffix = bf.name.rsplit("_", 1)
                    if (
                        len(suffix) == 2
                        and suffix[0] == base_field
                        and suffix[1].isdigit()
                    ):
                        idx = int(suffix[1])
                    elif bf.name == base_field and len(reg.fields) == 1:
                        idx = 0
                    else:
                        continue
                    instances.append(
                        LogicalInstance(
                            index=idx,
                            address=reg.offset,
                            bitfields=[_convert_field(bf)],
                        )
                    )
        else:
            for reg_idx, reg in enumerate(entry.regs):
                instances.append(
                    LogicalInstance(
                        index=reg_idx,
                        address=reg.offset,
                        bitfields=[_convert_field(f) for f in reg.fields],
                    )
                )

        instances.sort(key=lambda inst: inst.index)
        logical_groups.append(
            LogicalGroup(
                name=yaml_group.name,
                description=yaml_group.description,
                access=yaml_group.access,
                count=yaml_group.count,
                template_bitfields=yaml_group.bitfields,
                instances=instances,
            )
        )

    return logical_groups


def build_layout(
    config: RegistersConfig,
    env: Environment,
) -> RegtoolLayout:
    hjson_text = render_hjson(config, env)
    block = _load_ip_block(hjson_text)
    reg_block = block.reg_blocks[None]

    physical_registers = [_convert_register(reg) for reg in reg_block.flat_regs]
    logical_groups = _build_logical_groups(
        block, config.register_groups, config.width
    )

    return RegtoolLayout(
        block=block,
        physical_registers=sorted(physical_registers, key=lambda r: r.address),
        logical_groups=logical_groups,
        markdown=render_markdown(block),
    )
