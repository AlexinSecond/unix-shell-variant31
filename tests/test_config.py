"""Check argument parsing, script execution, and startup failures."""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from src.__main__ import main
from src.config import Config, parse_config
from src.shell import Shell


class ConfigTests(unittest.TestCase):
    """Use temporary physical files without changing fixture data."""

    def test_parse_paths_with_spaces(self):
        """CLI paths may contain spaces even though shell parsing is simple."""
        config = parse_config([
            "--vfs", "a folder/fs.json", "--script", "a folder/start.txt",
        ])
        self.assertEqual(config.vfs_path, Path("a folder/fs.json").resolve())
        self.assertEqual(
            config.script_path, Path("a folder/start.txt").resolve()
        )

    def test_defaults_and_dump(self):
        """Both keys are present even without a startup script."""
        config = parse_config([])
        self.assertIsNone(config.script_path)
        self.assertEqual(
            config.dump(), f"vfs_path={config.vfs_path}\nscript_path="
        )

    def test_invalid_cli_option(self):
        """argparse rejects unknown options with process status 2."""
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as caught:
                parse_config(["--unknown"])
        self.assertEqual(caught.exception.code, 2)

    def test_script_comments_echo_and_exit(self):
        """Blank/comments are skipped, commands echoed, exit stops script."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "startup.txt"
            path.write_text(
                "# skip\n\nls one # comment\nexit\nls ignored\n",
                encoding="utf-8",
            )
            output = io.StringIO()
            shell = Shell(writer=output.write)
            shell.run_script(path)
        result = output.getvalue()
        self.assertIn("$ ls one # comment", result)
        self.assertIn("ls: ['one']", result)
        self.assertNotIn("ignored", result)
        self.assertNotIn("# skip", result)

    def test_conf_dump_and_error(self):
        """The service command prints configuration and checks arity."""
        output = io.StringIO()
        shell = Shell(Config(Path("fs.json")), output.write)
        shell.execute("conf-dump")
        shell.execute("conf-dump extra")
        self.assertIn("vfs_path=fs.json\nscript_path=", output.getvalue())
        self.assertIn("usage: conf-dump", output.getvalue())

    def test_missing_script_is_a_startup_error(self):
        """A nonexistent startup script returns status 1 without a REPL."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing.txt"
            with contextlib.redirect_stdout(io.StringIO()):
                with contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(main(["--script", str(path)]), 1)


if __name__ == "__main__":
    unittest.main()
