"""Start the console emulator with python -m src."""

import sys

from .config import parse_config
from .shell import Shell


def main(arguments: list[str] | None = None) -> int:
    """Print configuration, run the startup script, then open the REPL."""
    config = parse_config(arguments)
    shell = Shell(config)
    shell.emit(config.dump())
    if config.script_path is not None:
        try:
            shell.run_script(config.script_path)
        except (OSError, UnicodeError) as error:
            print(f"startup: {error}", file=sys.stderr)
            return 1
    if shell.running:
        shell.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
