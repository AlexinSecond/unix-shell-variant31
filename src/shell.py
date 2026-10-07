"""Interactive loop, whitespace parser, scripts, and VFS commands."""

import getpass
import socket
import sys
from collections.abc import Callable
from pathlib import Path

from .config import Config
from .commands import CatWriter, parse_options
from .vfs import VirtualFileSystem

MULTI_PATH_MIN = 2
MIN_HISTORY_COUNT = 0


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
        self.previous_cwd = "/"
        self.history: list[str] = []

    @property
    def prompt(self) -> str:
        """Return a UNIX-like prompt based on real OS information."""
        location = "~" if self.cwd == "/" else self.cwd
        return f"{self.username}@{self.hostname}:{location}$ "

    def emit(self, message: str) -> None:
        """Write a complete output line."""
        self.write(message + "\n")

    def commands(self) -> dict[str, Callable[[list[str]], None]]:
        """Return the commands supported at this implementation stage."""
        return {
            "ls": self._ls, "cd": self._cd, "exit": self._exit,
            "conf-dump": self._conf_dump,
            "vfs-init": self._vfs_init,
            "cat": self._cat, "history": self._history,
            "touch": self._touch,
        }

    def execute(self, line: str) -> None:
        """Split on whitespace, dispatch, and report command errors."""
        tokens = line.split()
        if not tokens:
            return
        self.history.append(line.strip())
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
        """List files or directories, with optional hidden entries."""
        flags, paths = parse_options(arguments, {"a"})
        paths = paths or ["."]
        for path in paths:
            if len(paths) >= MULTI_PATH_MIN:
                self.emit(f"{path}:")
            try:
                self._list_path(path, "a" in flags)
            except ValueError as error:
                self.emit(f"ls: {error}")

    def _list_path(self, path: str, show_all: bool) -> None:
        """Display sorted child names or the requested file path."""
        _, node = self.vfs.resolve(path, self.cwd)
        if node.kind == "file":
            self.emit(path)
            return
        names = list(node.children)
        if show_all:
            names.extend([".", ".."])
        else:
            names = [name for name in names if not name.startswith(".")]
        for name in sorted(names):
            self.emit(name)

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
        self.previous_cwd = "/"
        self.emit("VFS reset: empty root directory")

    def _cd(self, arguments: list[str]) -> None:
        """Change the virtual directory; no argument means virtual home."""
        arguments = arguments[1:] if arguments[:1] == ["--"] else arguments
        if arguments[1:]:
            raise ValueError("usage: cd [DIRECTORY]")
        requested = arguments[0] if arguments else "~"
        path = self.previous_cwd if requested == "-" else requested
        absolute, node = self.vfs.resolve(path, self.cwd)
        if node.kind != "dir":
            raise ValueError(f"{requested}: Not a directory")
        self.previous_cwd, self.cwd = self.cwd, absolute
        if requested == "-":
            self.emit(self.cwd)

    def _cat(self, arguments: list[str]) -> None:
        """Print file contents, optionally with continuous numbering."""
        flags, paths = parse_options(arguments, {"n"})
        if not paths:
            raise ValueError("usage: cat [-n] [--] FILE...")
        output = CatWriter(self.write, "n" in flags)
        for path in paths:
            try:
                _, node = self.vfs.resolve(path, self.cwd)
                if node.kind != "file":
                    raise ValueError(f"{path}: Is a directory")
                output.write(node.content.decode("utf-8", errors="replace"))
            except ValueError as error:
                self.emit(f"cat: {error}")

    def _history(self, arguments: list[str]) -> None:
        """Show all commands, the last N commands, or clear the history."""
        if arguments == ["-c"]:
            self.history.clear()
            return
        if arguments[1:]:
            raise ValueError("usage: history [N | -c]")
        count = len(self.history)
        if arguments:
            try:
                count = int(arguments[0])
            except ValueError as error:
                raise ValueError("history count must be an integer") from error
            if count < MIN_HISTORY_COUNT:
                raise ValueError("history count cannot be negative")
        start = max(len(self.history) - count, MIN_HISTORY_COUNT)
        for index in range(start, len(self.history)):
            self.emit(f"{index + 1:5}  {self.history[index]}")

    def _touch(self, arguments: list[str]) -> None:
        """Create files or refresh timestamps; -c suppresses creation."""
        flags, paths = parse_options(arguments, {"c"})
        if not paths:
            raise ValueError("usage: touch [-c] [--] FILE...")
        for path in paths:
            try:
                self.vfs.touch(path, self.cwd, create="c" not in flags)
            except ValueError as error:
                self.emit(f"touch: {error}")

    def _exit(self, arguments: list[str]) -> None:
        """Stop the loop; reject arguments in this emulator."""
        if arguments:
            raise ValueError("usage: exit")
        self.running = False
