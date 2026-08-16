# Built-in Domains

embgen ships with these domains. Each one is a CLI subcommand (`embgen <domain> ...`).

## User-facing

| Domain | YAML key | What it generates |
| --- | --- | --- |
| [Commands](commands.md) | `commands` | Command protocol C header, Python, Markdown |
| [Registers](registers.md) | `regmap` | Register map C, Python, Markdown, Hjson (OpenTitan regtool) |
| [Registers (shallow)](registers_shallow.md) | `regmap_shallow` | Same idea, with OpenTitan-style `count` / packed multiregs |
| [JSON-RPC](jsonrpc.md) | `methods` | JSON-RPC client Python and Markdown |
| [NanoPB](nanopb.md) | `methods` | Protobuf + NanoPB options, Python, Markdown |

## Internal

`testing` (`items` key) exists for the test suite. It is not a product domain.

## Domain detection

`embgen auto` walks discovered generators and takes the **first** `detect()` that returns true.

| YAML key | Domain |
| --- | --- |
| `commands` | Commands |
| `regmap` | Registers |
| `regmap_shallow` | Registers (shallow) |
| `methods` | JSON-RPC **or** NanoPB (same key) |
| `items` (and no `commands`/`regmap`) | testing |

`jsonrpc` and `nanopb` both look for `methods`. Do not use `embgen auto` to choose between them; call `embgen jsonrpc` or `embgen nanopb`.

```yaml
# Commands
name: MyCommands
commands:
  - name: ping
    id: 0

# Registers
name: MyRegisters
regmap:
  - name: CONTROL
    address: 0x00
    bitfields: []

# Registers (shallow)
name: MyRegisters
regmap_shallow:
  - name: CONTROL
    address: 0x00
    bitfields: []

# JSON-RPC or NanoPB — pick the subcommand yourself
name: MyAPI
methods:
  - name: ping
```
