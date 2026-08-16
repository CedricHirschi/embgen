# NanoPB Domain

The NanoPB domain generates protobuf definitions, NanoPB options, Python helpers, and Markdown from a method list. Typical use is a host/device RPC that compiles with [nanopb](https://jpa.kapsi.fi/nanopb/).

Use `embgen nanopb`, not `embgen auto`. Auto-detect also matches JSON-RPC on the same `methods` key.

## YAML Schema

```yaml
name: string              # Required: Name for the method set
file: string              # Optional: Output filename (defaults to lowercase name)
max_count: integer        # Optional: NanoPB max_count for repeated fields (default in templates: 40)
methods:                  # Required: List of methods
  - name: string          # Method name
    description: string   # Optional
    args:                 # Optional: arguments
      - name: string
        type: string      # Argument type (see below); omit when using enums
        description: string
        default: value    # Optional
        enum_name: string # Optional: explicit enum type name
        enums:            # Optional
          - name: string
            value: integer
            description: string
    returns:              # Optional: same shape as args
      - name: string
        type: string
        description: string
```

## Argument Types

Same `struct`-style codes as Commands and JSON-RPC:

| Type | Description | Python | Protobuf |
| ---- | ----------- | ------ | -------- |
| `B` / `H` / `I` | Unsigned 8/16/32-bit | `int` | `uint32` |
| `Q` | Unsigned 64-bit | `int` | `uint64` |
| `b` / `h` / `i` | Signed 8/16/32-bit | `int` | `int32` |
| `q` | Signed 64-bit | `int` | `int64` |
| `e` / `f` | 16/32-bit float | `float` | `float` |
| `d` | 64-bit float | `float` | `double` |
| `?` | Boolean | `bool` | `bool` |
| `s` | Byte string | `bytes` | `bytes` |

`enum_name` controls the generated enum identifier. Without it, names are derived from the method and field.

## Example Configuration

```yaml
name: Telemetry
file: telemetry
max_count: 40

methods:
  - name: ping
    description: "Ping the device"
    args:
      - name: probe_id
        type: B
        default: 1
        description: "Probe identifier"
    returns:
      - name: status
        enum_name: PingStatus
        enums:
          - { name: OK, value: 0, description: "The ping completed successfully" }
          - { name: ERROR, value: 1, description: "The ping failed" }
        description: "Ping status"

  - name: setmode
    description: "Switch the device operating mode"
    args:
      - name: mode
        enum_name: OperatingMode
        enums:
          - { name: AUTO, value: 0 }
          - { name: MANUAL, value: 1 }
        default: AUTO
        description: "Requested operating mode"
```

## Generated Outputs

### Protobuf (`--proto`)

```bash
embgen nanopb config.yml -o output/ --proto
```

Writes `<file>.proto`: `proto3` package, per-method `*_args` / `*_result` messages, a `cmd` oneof, batched `request` / `response`, and a `status` enum.

### NanoPB options (`--options`)

```bash
embgen nanopb config.yml -o output/ --options
```

Writes `<file>.options` with `max_count` on repeated request/response fields (40 if `max_count` is omitted).

### Python (`--py`) and Markdown (`--md`)

```bash
embgen nanopb config.yml -o output/ --py --md
```

Python helpers and Markdown docs for the same method list.

## CLI Usage

```bash
embgen nanopb config.yml -o output/ --proto --options --py --md
```

## Python API Usage

```python
from pathlib import Path
from embgen.discovery import discover_domains
from embgen.generator import CodeGenerator

domains = discover_domains()
code_gen = CodeGenerator(domains["nanopb"], Path("output"))

templates = {
    "proto": "template.proto.j2",
    "options": "template.options.j2",
    "py": "template.py.j2",
}
code_gen.generate_from_file(Path("telemetry.yml"), templates)
```
