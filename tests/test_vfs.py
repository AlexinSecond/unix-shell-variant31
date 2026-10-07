"""Check JSON validation, paths, byte preservation, and service reset."""

import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.config import Config
from src.shell import Shell
from src.vfs import VirtualFileSystem, decode_node


class VfsTests(unittest.TestCase):
    """Exercise real fixture files and isolated writable JSON copies."""

    def setUp(self):
        """Load the filesystem with at least three directory levels."""
        self.vfs = VirtualFileSystem.load(Path("examples/vfs/deep.json"))

    def test_fixture_variants_and_binary_data(self):
        """Minimal, multi-file, and deep trees all load correctly."""
        minimal = VirtualFileSystem.load(Path("examples/vfs/minimal.json"))
        files = VirtualFileSystem.load(Path("examples/vfs/files.json"))
        self.assertEqual(minimal.root.children, {})
        self.assertGreater(len(files.root.children), 1)
        self.assertEqual(self.vfs.resolve("/binary.bin")[1].content,
                         b"\x00\x01\x02\xff")
        node = self.vfs.resolve("/home/student/projects/readme.txt")[1]
        self.assertIn(b"Project at", node.content)

    def test_paths_relative_absolute_parent_and_home(self):
        """The path resolver works independently of Windows path rules."""
        self.assertEqual(
            self.vfs.resolve("./projects/../projects", "/home/student")[0],
            "/home/student/projects",
        )
        self.assertEqual(self.vfs.resolve("../../..", "/home")[0], "/")
        self.assertEqual(self.vfs.resolve("~")[0], "/")
        self.assertEqual(self.vfs.resolve("~/var//log/")[0], "/var/log")

    def test_missing_or_non_directory_components(self):
        """Normalization must not bypass missing nodes or file parents."""
        for path in ["/missing/../home", "/hello.txt/..", "/hello.txt/"]:
            with self.subTest(path=path):
                with self.assertRaises(ValueError):
                    self.vfs.resolve(path)

    def test_invalid_schema(self):
        """Bad node types, content, names, encoding, and base64 fail."""
        invalid = [
            [], {"type": "bad"}, {"type": "dir", "children": []},
            {"type": "file", "content": 12},
            {"type": "file", "content": "?", "encoding": "base64"},
            {"type": "file", "content": "x", "encoding": "other"},
            {"type": "dir", "children": {"../x": {"type": "dir"}}},
        ]
        for data in invalid:
            with self.subTest(data=data):
                with self.assertRaises(ValueError):
                    decode_node(data)
        with self.assertRaises(ValueError):
            VirtualFileSystem(decode_node({"type": "file", "content": ""}))

    def test_load_does_not_modify_physical_source(self):
        """Loading performs no writes to the physical source."""
        path = Path("examples/vfs/deep.json")
        before = path.read_bytes()
        VirtualFileSystem.load(path)
        self.assertEqual(path.read_bytes(), before)

    def test_reset_clears_memory_physical_source_and_cwd(self):
        """Only the service command resets the JSON file on disk."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "vfs.json"
            path.write_bytes(Path("examples/vfs/deep.json").read_bytes())
            shell = Shell(Config(path), io.StringIO().write)
            shell.cwd = "/home/student"
            shell.execute("vfs-init")
            self.assertEqual(shell.cwd, "/")
            self.assertEqual(shell.vfs.root.children, {})
            self.assertEqual(
                json.loads(path.read_text(encoding="utf-8")),
                {"type": "dir", "children": {}},
            )

    def test_failed_reset_keeps_memory(self):
        """A physical write failure leaves the in-memory tree unchanged."""
        original = self.vfs.root
        with patch.object(Path, "write_text", side_effect=OSError("denied")):
            with self.assertRaises(OSError):
                self.vfs.reset(Path("unused.json"))
        self.assertIs(self.vfs.root, original)

    def test_bad_json_and_missing_file(self):
        """Invalid physical sources produce readable startup failures."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "vfs.json"
            with self.assertRaises(OSError):
                VirtualFileSystem.load(path)
            path.write_text("{ broken", encoding="utf-8")
            with self.assertRaises(ValueError):
                VirtualFileSystem.load(path)


if __name__ == "__main__":
    unittest.main()
