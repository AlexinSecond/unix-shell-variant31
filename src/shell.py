"""Interactive loop, whitespace parser, and prototype commands."""

import getpass
import socket
import sys
from collections.abc import Callable
from pathlib import Path

from .config import Config
from .vfs import VirtualFileSystem


class Shell:
    """Parse commands and dispatch them without using the host shell."""

    def __init__(
        self, config: Config | None = None,
        writer: Callable[[str], object] | None = None,
        vfs: VirtualFileSystem | None = None,
    ):
        """Read real user/host names and initialize the output writer."""
        self.write = writer if writer is not None else sys.stdout.write
        self.username = getpass.getuser()
        self.hostname = socket.gethostname()
        self.running = True
        self.config = config or Config(Path("examples/vfs/minimal.json"))
        self.vfs = vfs if vfs is not None else VirtualFileSystem.load(
            self.config.vfs_path
        )
        self.cwd = "/"

    @property
    def prompt(self) -> str:
        """Return a UNIX-like prompt based on real OS information."""
        return f"{self.username}@{self.hostname}:~$ "

    def emit(self, message: str) -> None:
        """Write a complete output line."""
        self.write(message + "\n")

    def commands(self) -> dict[str, Callable[[list[str]], None]]:
        """Return the commands supported at this implementation stage."""
        return {
            "ls": self._ls, "cd": self._cd, "exit": self._exit,
            "conf-dump": self._conf_dump,
            "vfs-init": self._vfs_init,
        }

    def execute(self, line: str) -> None:
        """Split on whitespace, dispatch, and report command errors."""
        tokens = line.split()
        if not tokens:
            return
        command, *arguments = tokens
        handler = self.commands().get(command)
        if handler is None:
            self.emit(f"{command}: command not found")
            return
        try:
            handler(arguments)
        except (ValueError, OSError) as error:
            self.emit(f"{command}: {error}")

    def run(self) -> None:
        """Read commands until exit or EOF; Ctrl+C cancels the input."""
        while self.running:
            try:
                line = input(self.prompt)
            except EOFError:
                self.emit("")
                break
            except KeyboardInterrupt:
                self.emit("")
                continue
            self.execute(line)

    def _ls(self, arguments: list[str]) -> None:
        """Print the name and arguments of the ls stub."""
        self.emit(f"ls: {arguments!r}")

    def run_script(self, path: Path) -> None:
        """Echo and execute script commands; support Python # comments."""
        for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
            command = raw_line.partition("#")[0].strip()
            if not command:
                continue
            self.emit(self.prompt + raw_line.strip())
            self.execute(command)
            if not self.running:
                break

    def _conf_dump(self, arguments: list[str]) -> None:
        """Print the current configuration as key-value pairs."""
        if arguments:
            raise ValueError("usage: conf-dump")
        self.emit(self.config.dump())

    def _vfs_init(self, arguments: list[str]) -> None:
        """Reset both VFS representations and the current directory."""
        if arguments:
            raise ValueError("usage: vfs-init")
        self.vfs.reset(self.config.vfs_path)
        self.cwd = "/"
        self.emit("VFS reset: empty root directory")

    def _cd(self, arguments: list[str]) -> None:
        """Print the name and arguments of the cd stub."""
        self.emit(f"cd: {arguments!r}")

    def _exit(self, arguments: list[str]) -> None:
        """Stop the loop; reject arguments in this emulator."""
        if arguments:
            raise ValueError("usage: exit")
        self.running = False
