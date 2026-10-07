"""Start the console emulator with python -m src."""

from .shell import Shell


def main() -> int:
    """Run the interactive command loop."""
    Shell().run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
