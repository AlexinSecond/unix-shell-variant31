"""Check complete emulator processes and physical-path edge cases."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESS_TIMEOUT = 10


def run_emulator(arguments, stdin=""):
    """Start the real entry point with UTF-8 input and captured output."""
    environment = os.environ.copy()
    environment["PYTHONIOENCODING"] = "utf-8"
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, "-m", "src", *arguments], cwd=PROJECT_ROOT,
        input=stdin, encoding="utf-8", errors="replace",
        capture_output=True, timeout=PROCESS_TIMEOUT, env=environment,
    )


class IntegrationTests(unittest.TestCase):
    """Verify process output, statuses, script-to-REPL flow, and isolation."""

    def test_real_paths_with_spaces_and_cyrillic(self):
        """Both CLI paths support spaces and Unicode through the OS."""
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory) / "папка с пробелами"
            folder.mkdir()
            vfs = folder / "file system.json"
            script = folder / "start script.txt"
            original = (PROJECT_ROOT / "examples/vfs/deep.json").read_bytes()
            vfs.write_bytes(original)
            script.write_text(
                "# comment\ncat /hello.txt\ntouch /new.txt\nls /\n"
                "exit\nignored-command\n", encoding="utf-8",
            )
            result = run_emulator(["--vfs", str(vfs), "--script", str(script)])
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Hello, variant 31!", result.stdout)
            self.assertIn("new.txt", result.stdout)
            self.assertNotIn("ignored-command", result.stdout)
            self.assertEqual(vfs.read_bytes(), original)

    def test_missing_vfs_returns_startup_status(self):
        """A bad physical source produces status 1 without a traceback."""
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing.json"
            result = run_emulator(["--vfs", str(missing)])
        self.assertEqual(result.returncode, 1)
        self.assertIn("startup:", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_missing_cli_value_returns_parser_status(self):
        """Missing CLI option values produce argparse status 2."""
        result = run_emulator(["--vfs"])
        self.assertEqual(result.returncode, 2)
        self.assertIn("expected one argument", result.stderr)

    def test_script_without_exit_continues_in_repl(self):
        """After startup commands, interactive commands are still read."""
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / "start.txt"
            script.write_text("conf-dump\n", encoding="utf-8")
            result = run_emulator(
                ["--script", str(script)], "ls -a\nexit\n"
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("$ conf-dump", result.stdout)
        self.assertIn(".\n..\n", result.stdout)

    def test_utf8_bom_sources_and_cyrillic_content(self):
        """JSON/script BOMs are accepted; Cyrillic text prints correctly."""
        with tempfile.TemporaryDirectory() as directory:
            vfs = Path(directory) / "vfs.json"
            script = Path(directory) / "script.txt"
            data = {"type": "dir", "children": {
                "hello.txt": {"type": "file", "content": "Привет!\n"},
            }}
            vfs.write_text(
                json.dumps(data, ensure_ascii=False), encoding="utf-8-sig"
            )
            script.write_text("cat /hello.txt\nexit\n", encoding="utf-8-sig")
            result = run_emulator(["--vfs", str(vfs), "--script", str(script)])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Привет!", result.stdout)

    def test_host_commands_are_not_executed(self):
        """An unknown command cannot fall through to the real OS shell."""
        result = run_emulator([], "whoami\nexit\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("whoami: command not found", result.stdout)


if __name__ == "__main__":
    unittest.main()
