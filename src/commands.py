"""Small reusable helpers for shell options and cat output."""

from collections.abc import Callable


def parse_options(
    arguments: list[str], allowed: set[str],
) -> tuple[set[str], list[str]]:
    """Parse short flags and --; reject unsupported command options."""
    flags: set[str] = set()
    paths: list[str] = []
    options_enabled = True
    for argument in arguments:
        if options_enabled and argument == "--":
            options_enabled = False
        elif options_enabled and argument.startswith("-") and argument != "-":
            for flag in argument[1:]:
                if flag not in allowed:
                    raise ValueError(f"unsupported option: -{flag}")
                flags.add(flag)
        else:
            paths.append(argument)
    return flags, paths


class CatWriter:
    """Optionally number lines continuously across multiple files."""

    def __init__(self, writer: Callable[[str], object], numbered: bool):
        """Initialize a shared output state for one cat invocation."""
        self.writer = writer
        self.numbered = numbered
        self.line_number = 1
        self.line_start = True

    def write(self, text: str) -> None:
        """Preserve content and avoid adding a final newline."""
        if not self.numbered:
            self.writer(text)
            return
        for part in text.splitlines(keepends=True):
            if self.line_start:
                self.writer(f"{self.line_number:6}\t")
                self.line_number += 1
            self.writer(part)
            self.line_start = part.endswith("\n")
