# Built-in Domains

embgen includes two built-in domains for common embedded systems code generation tasks:

## [Commands](commands.md)

Generate code from command protocol definitions. Perfect for:

- Embedded communication protocols
- Serial command interfaces  
- RPC-style APIs between host and device
- Test automation interfaces

**Output Formats:**

- **C Header** — Command IDs, argument structures, enumerations
- **Python** — Dataclasses with serialization/deserialization
- **Markdown** — Human-readable documentation

## [Registers](registers.md)

Generate code from hardware register map definitions. Perfect for:

- MCU peripheral drivers
- FPGA register interfaces
- Hardware abstraction layers
- Register documentation

**Output Formats:**

- **C Header** — Addresses, bitfield macros, accessor functions
- **Python** — Register classes with bit manipulation
- **Markdown** — Documentation with bit-level layouts

## Domain Detection

When using `embgen auto`, the domain is detected by examining the YAML structure:

| YAML Key   | Detected Domain |
| ---------- | --------------- |
| `commands` | Commands        |
| `regmap`   | Registers       |

```yaml
# Detected as Commands domain
name: MyCommands
commands:
  - name: ping
    id: 0

# Detected as Registers domain  
name: MyRegisters
regmap:
  - name: CONTROL
    address: 0x00
```
