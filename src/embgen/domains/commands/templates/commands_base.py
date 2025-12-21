"""
Command base classes for building and sequencing commands.

This file is auto-copied by embgen. Do not edit manually.
"""

from dataclasses import dataclass, field, fields
import struct
from typing import Optional
from enum import Enum


@dataclass
class Command:
    """Base class for all commands."""

    _id: int = field(default=-1, init=False)
    _format: str = field(default="", init=False)

    @property
    def id(self) -> int:
        return self._id

    def build(self, endianness: str = "=") -> bytes:
        """Build the command into a byte sequence."""
        build_fields = [f.name for f in fields(self)]
        build_fields = filter(lambda f: not f.startswith("_"), build_fields)
        build_fields = [getattr(self, f) for f in build_fields]
        build_fields = [f.value if isinstance(f, Enum) else f for f in build_fields]

        format = endianness
        for i, char in enumerate(self._format):
            if char == "s":
                build_fields[i] = bytes(build_fields[i])
                format += str(len(build_fields[i])) + "s"
            else:
                format += char

        body = struct.pack(format, *build_fields)
        header = struct.pack(endianness + "BH", self._id, len(body))

        return header + body


class CommandSequence:
    """A sequence of commands that can be built together."""

    def __init__(self, other: Optional["Command | CommandSequence"] = None):
        self.commands: list[Command] = []
        if isinstance(other, Command):
            self.commands.append(other)
        elif isinstance(other, CommandSequence):
            self.commands.extend(other.commands)

    def add(self, command: Command) -> "CommandSequence":
        """Add a command to the sequence."""
        self.commands.append(command)
        return self

    def __iadd__(self, other: "Command | CommandSequence") -> "CommandSequence":
        if isinstance(other, Command):
            self.commands.append(other)
        elif isinstance(other, CommandSequence):
            self.commands.extend(other.commands)
        else:
            raise TypeError("Unsupported type for addition")
        return self

    def __add__(self, other: "Command | CommandSequence") -> "CommandSequence":
        self += other
        return self

    def build(self, endianness: str = "=", max_size: int = 1000) -> list[bytes]:
        """Build the command sequence into chunks of byte sequences."""
        max_payload = max_size - 2  # Reserve space for header

        def chunk_commands():
            current_chunk = []
            current_size = 0

            for cmd in self.commands:
                cmd_bytes = cmd.build(endianness)
                num_bytes = len(cmd_bytes)
                if num_bytes > max_payload:
                    raise ValueError(
                        f"Command {cmd.__class__.__name__} is too large ({num_bytes} bytes) "
                        f"for maximum payload size ({max_payload} bytes)"
                    )

                if current_size + num_bytes > max_payload and current_chunk:
                    yield current_chunk
                    current_chunk = [cmd_bytes]
                    current_size = num_bytes
                else:
                    current_chunk.append(cmd_bytes)
                    current_size += num_bytes

            if current_chunk:
                yield current_chunk

        return [
            struct.pack(endianness + "H", len(chunk)) + b"".join(chunk)
            for chunk in chunk_commands()
        ]

    def clear(self) -> None:
        """Clear all commands from the sequence."""
        self.commands.clear()
