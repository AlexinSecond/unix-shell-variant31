"""Command-line parameters and key-value configuration output."""

import argparse
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Config:
    """Store physical paths; these are separate from virtual paths."""

    vfs_path: Path
    script_path: Path | None = None

    def dump(self) -> str:
        """Format all configurable values as key=value lines."""
        script = str(self.script_path) if self.script_path else ""
        return f"vfs_path={self.vfs_path}\nscript_path={script}"


def parse_config(arguments: list[str] | None = None) -> Config:
    """Parse --vfs and --script and normalize physical paths."""
    parser = argparse.ArgumentParser(
        description="UNIX shell emulator, variant 31"
    )
    parser.add_argument(
        "--vfs", type=Path, default=Path("examples/vfs/minimal.json"),
        help="physical path to the JSON virtual filesystem",
    )
    parser.add_argument(
        "--script", type=Path, help="physical path to a startup script"
    )
    options = parser.parse_args(arguments)
    script = options.script.resolve() if options.script is not None else None
    return Config(options.vfs.resolve(), script)
