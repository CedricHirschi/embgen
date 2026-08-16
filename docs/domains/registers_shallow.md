# Registers (shallow) Domain

`registers_shallow` is the OpenTitan-oriented register map domain. YAML uses `regmap_shallow` instead of `regmap`. Repeated registers stay as **multiregs** (`count`) instead of being expanded to `DATA0`, `DATA1`, … the way [Registers](registers.md) does with `numbers`.

Use this when you want hjson that `regtool.py` consumes as `multireg` blocks, including compact packing of several logical instances into one physical register.

## YAML Schema

```yaml
name: string              # Required
file: string              # Optional output filename (defaults to lowercase name)
width: integer            # Optional register width in bits (default: 32)
access_separate: bool     # If true, every register must set access_hw
regmap_shallow:           # Required
  - name: string
    address: integer      # Word address (hex or decimal)
    description: string
    access: string        # Software access (default: rw)
    access_hw: string     # Hardware access (required if access_separate)
    hwqe: bool            # OpenTitan hwqe
    hwext: bool           # OpenTitan hwext
    count: integer        # Optional: identical instances (OpenTitan multireg)
    cname: string         # Optional, passed through to hjson
    compact: bool         # Optional multireg packing
    regwen_multi: bool
    bitfields:
      - name: string
        width: integer
        offset: integer
        reset: integer | bool | enum name
        description: string
        enums:
          - { name: string, value: integer, description: string }
```

Detection key: `regmap_shallow`. `embgen auto` can distinguish this from `registers`.

## Access Types

Software (`access`) and hardware (`access_hw`) use the same names:

| Type | Meaning |
| --- | --- |
| `rw` | Read-write (default software access) |
| `ro` | Read-only |
| `wo` | Write-only |
| `rw1c` | Write-1-to-clear |
| `wosc` | Write-only, self-clearing |
| `rolh` | Read-only, latch high |
| `hro` / `hrw` / `hwo` | Hardware-side access |

## Example Configuration

```yaml
name: SimpleRegmap
file: simple

regmap_shallow:
  - name: CONTROL
    description: Control register
    address: 0
    bitfields:
      - name: ENABLE
        width: 1
        offset: 0
        reset: 0
      - name: MODE
        width: 3
        offset: 1
        reset: NORMAL
        enums:
          - { name: POWER_OFF, value: 0 }
          - { name: NORMAL, value: 1 }

  - name: DATA
    description: Data register bank
    address: 2
    count: 16
    bitfields:
      - name: VALUE
        width: 16
        offset: 0
        reset: 0xCAFE
```

`count: 16` stays a multireg in hjson. The C/Python/Markdown views use the physical layout from `regtool_layout.py` (packed vs spread instances).

## Generated Outputs

| Flag | Output |
| --- | --- |
| `--h` | `<file>.h` — addresses, attributes, accessors |
| `--py` | `<file>.py` plus `registers_base.py` (if `copy_support_files`) |
| `--md` | `<file>.md` — bit layouts from the computed layout |
| `--hjson` | `<file>.hjson`, then vendored `regtool.py -r` writes `<file>_reg_pkg.sv` and `<file>_reg_top.sv` |

```bash
embgen registers_shallow config.yml -o output/ --h --py --md --hjson
```

`--hjson` runs OpenTitan `regtool.py` from `src/embgen/domains/registers_shallow/regtool/` with `cwd` set to that folder. Failures there mean the `.hjson` exists but RTL may be missing.

## vs Registers

| | `registers` | `registers_shallow` |
| --- | --- | --- |
| YAML key | `regmap` | `regmap_shallow` |
| Repeated regs | `numbers: [0, 1, …]` expanded to `NAME0`, `NAME1`, consecutive addresses | `count: N` kept as OpenTitan `multireg` |
| Extra C | `--c-multi` (`_impl.h`, `_base.h`, `_base.c`) | no `c_multi` templates |
| Layout | Flat expanded `regmap` | `regtool_layout.py` physical + logical groups |

## Python API Usage

```python
from pathlib import Path
from embgen.discovery import discover_domains
from embgen.generator import CodeGenerator

domains = discover_domains()
code_gen = CodeGenerator(domains["registers_shallow"], Path("output"))
code_gen.generate_from_file(
    Path("map.yml"),
    {"h": "template.h.j2", "hjson": "template.hjson.j2"},
)
```
