"""Check in-memory creation, timestamp updates, and JSON isolation."""

import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.config import Config
from src.shell import Shell
from src.vfs import VirtualFileSystem


class TouchTests(unittest.TestCase):
    """Operate on a temporary JSON copy to verify disk invariants."""

    def setUp(self):
        """Prepare the source, shell, and captured command output."""
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "vfs.json"
        self.path.write_bytes(Path("examples/vfs/deep.json").read_bytes())
        self.before = self.path.read_bytes()
        self.output = io.StringIO()
        self.shell = Shell(Config(self.path), self.output.write)

    def test_create_relative_absolute_and_multiple_files(self):
        """touch creates empty files in existing virtual directories."""
        self.shell.execute("cd /home/student/projects")
        self.shell.execute("touch one.txt two.txt /absolute.txt ../parent.txt")
        paths = [
            "/home/student/projects/one.txt",
            "/home/student/projects/two.txt",
            "/absolute.txt", "/home/student/parent.txt",
        ]
        for path in paths:
            with self.subTest(path=path):
                node = self.shell.vfs.resolve(path)[1]
                self.assertEqual(node.kind, "file")
                self.assertEqual(node.content, b"")
                self.assertGreater(node.mtime_ns, 0)
        self.assertEqual(self.output.getvalue(), "")

    def test_existing_file_preserves_contents_and_updates_time(self):
        """touch does not truncate an existing file."""
        node = self.shell.vfs.resolve("/hello.txt")[1]
        original = node.content
        with patch("src.vfs.time.time_ns", return_value=123456789):
            self.shell.execute("touch /hello.txt")
        self.assertEqual(node.content, original)
        self.assertEqual(node.mtime_ns, 123456789)

    def test_directory_timestamp_can_be_updated(self):
        """Existing directories accept touch without changing their type."""
        node = self.shell.vfs.resolve("/home")[1]
        with patch("src.vfs.time.time_ns", return_value=123):
            self.shell.execute("touch /home")
        self.assertEqual(node.kind, "dir")
        self.assertEqual(node.mtime_ns, 123)

    def test_no_create_option(self):
        """-c skips missing files but still updates existing timestamps."""
        self.shell.execute("touch -c /absent.txt /hello.txt")
        self.assertNotIn("absent.txt", self.shell.vfs.root.children)
        self.assertGreater(self.shell.vfs.resolve("/hello.txt")[1].mtime_ns, 0)
        self.assertEqual(self.output.getvalue(), "")

    def test_errors_and_later_valid_operand(self):
        """Invalid parents and options are reported without stopping."""
        commands = [
            "touch /missing/file.txt good.txt",
            "touch /hello.txt/file.txt", "touch absent/",
            "touch", "touch -z invalid.txt",
        ]
        for command in commands:
            self.shell.execute(command)
        result = self.output.getvalue()
        self.assertIn("No such file", result)
        self.assertIn("Not a directory", result)
        self.assertIn("usage: touch", result)
        self.assertIn("unsupported option", result)
        self.assertIn("good.txt", self.shell.vfs.root.children)
        self.assertNotIn("invalid.txt", self.shell.vfs.root.children)

    def test_option_terminator(self):
        """touch -- supports virtual names starting with a dash."""
        self.shell.execute("touch -- -dash.txt")
        self.assertIn("-dash.txt", self.shell.vfs.root.children)

    def test_changes_disappear_when_reloading(self):
        """The JSON bytes and host directory contents stay unchanged."""
        files_before = list(Path(self.directory.name).iterdir())
        self.shell.execute("touch /new.txt /hello.txt")
        self.assertEqual(self.path.read_bytes(), self.before)
        self.assertEqual(
            list(Path(self.directory.name).iterdir()), files_before
        )
        reloaded = VirtualFileSystem.load(self.path)
        self.assertNotIn("new.txt", reloaded.root.children)
        self.assertEqual(reloaded.resolve("/hello.txt")[1].mtime_ns, 0)

    def test_reset_removes_created_files_and_resets_previous_cwd(self):
        """Service reset clears memory/disk while history remains available."""
        self.shell.execute("touch /created.txt")
        self.shell.execute("cd /home")
        self.shell.execute("vfs-init")
        self.assertEqual(self.shell.cwd, "/")
        self.assertEqual(self.shell.previous_cwd, "/")
        self.assertEqual(self.shell.vfs.root.children, {})
        self.assertEqual(VirtualFileSystem.load(self.path).root.children, {})
        self.assertIn("touch /created.txt", self.shell.history)


if __name__ == "__main__":
    unittest.main()
