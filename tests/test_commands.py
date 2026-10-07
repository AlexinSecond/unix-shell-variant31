"""Check real UNIX-like commands, paths, history, and read-only VFS use."""

import io
import unittest
from pathlib import Path

from src.commands import parse_options
from src.config import Config
from src.shell import Shell
from src.vfs import Node


class CommandTests(unittest.TestCase):
    """Test command output and state rather than handler internals."""

    def setUp(self):
        """Load a fresh in-memory copy for each test."""
        self.output = io.StringIO()
        self.source = Path("examples/vfs/deep.json")
        self.shell = Shell(Config(self.source), self.output.write)

    def execute(self, line):
        """Run a command and return only its output."""
        self.output.seek(0)
        self.output.truncate(0)
        self.shell.execute(line)
        return self.output.getvalue()

    def test_ls_hidden_files_and_file_operand(self):
        """ls hides dotfiles unless -a is present and supports file paths."""
        plain = self.execute("ls")
        self.assertNotIn(".hidden", plain)
        self.assertEqual(plain.splitlines(), sorted(plain.splitlines()))
        all_files = self.execute("ls -a")
        self.assertIn(".\n..\n.hidden\n", all_files)
        self.assertEqual(self.execute("ls /hello.txt"), "/hello.txt\n")

    def test_ls_multiple_paths_and_errors(self):
        """An invalid operand does not prevent listing later valid ones."""
        result = self.execute("ls /missing /home/student/projects")
        self.assertIn("No such file", result)
        self.assertIn("readme.txt", result)
        self.assertIn("unsupported option", self.execute("ls -z"))

    def test_cd_relative_parent_home_and_previous(self):
        """cd changes only the virtual cwd and updates the prompt."""
        self.execute("cd /home/student")
        self.execute("cd ./projects")
        self.assertEqual(self.shell.cwd, "/home/student/projects")
        self.assertIn(":/home/student/projects$", self.shell.prompt)
        self.execute("cd ..")
        self.assertEqual(self.execute("cd -"), "/home/student/projects\n")
        self.execute("cd ~")
        self.assertEqual(self.shell.cwd, "/")
        self.execute("cd -- /var/log")
        self.execute("cd")
        self.assertEqual(self.shell.cwd, "/")

    def test_cd_errors_preserve_directory(self):
        """Missing paths, files, and too many operands do not change cwd."""
        for command in ["cd /missing", "cd /hello.txt", "cd a b"]:
            with self.subTest(command=command):
                self.assertTrue(self.execute(command))
                self.assertEqual(self.shell.cwd, "/")

    def test_cat_contents_numbering_and_empty_file(self):
        """cat preserves text and numbers lines across all operands."""
        self.assertEqual(self.execute("cat /hello.txt"),
                         "Hello, variant 31!\nSecond line.\n")
        self.assertEqual(self.execute("cat /empty.txt"), "")
        result = self.execute(
            "cat -n /hello.txt /home/student/projects/readme.txt"
        )
        self.assertIn("     1\tHello", result)
        self.assertIn("     3\tProject", result)
        self.assertIn("\ufffd", self.execute("cat /binary.bin"))

    def test_cat_errors_and_later_valid_operand(self):
        """cat reports errors, then continues with valid files."""
        result = self.execute("cat /missing /hello.txt")
        self.assertIn("No such file", result)
        self.assertIn("Hello, variant 31!", result)
        self.assertIn("Is a directory", self.execute("cat /"))
        self.assertIn("usage: cat", self.execute("cat"))
        self.assertIn("unsupported option", self.execute("cat -z /hello.txt"))

    def test_cat_unterminated_lines_continue_between_files(self):
        """cat -n does not number a new line without a newline boundary."""
        self.shell.vfs.root.children["one"] = Node("file", content=b"abc")
        self.shell.vfs.root.children["two"] = Node("file", content=b"def\nx")
        self.assertEqual(
            self.execute("cat -n /one /two"), "     1\tabcdef\n     2\tx"
        )

    def test_history_records_errors_itself_and_preserves_spacing(self):
        """Nonempty commands, including unsuccessful ones, are numbered."""
        self.execute("  ls   /  ")
        self.execute("bad")
        self.execute(" ")
        result = self.execute("history 2")
        self.assertEqual(result, "    2  bad\n    3  history 2\n")
        self.assertEqual(self.shell.history[0], "ls   /")

    def test_history_zero_clear_and_bad_arguments(self):
        """Zero prints nothing; clear resets numbering; errors stay visible."""
        self.execute("ls")
        self.assertEqual(self.execute("history 0"), "")
        self.assertIn("negative", self.execute("history -1"))
        self.assertIn("integer", self.execute("history bad"))
        self.assertIn("usage", self.execute("history 1 2"))
        self.assertEqual(self.execute("history -c"), "")
        self.assertEqual(self.execute("history"), "    1  history\n")

    def test_read_commands_do_not_modify_source_or_host_cwd(self):
        """ls, cd, cat and history do not write JSON or change host cwd."""
        before = self.source.read_bytes()
        host_cwd = Path.cwd()
        for command in ["cd /home", "ls -a /", "cat /hello.txt", "history"]:
            self.execute(command)
        self.assertEqual(self.source.read_bytes(), before)
        self.assertEqual(Path.cwd(), host_cwd)

    def test_option_terminator_allows_names_starting_with_dash(self):
        """-- separates options from names that would look like flags."""
        self.shell.vfs.root.children["-a"] = Node("file", content=b"ok")
        self.assertEqual(self.execute("cat -- -a"), "ok")
        self.assertEqual(parse_options(["-a", "--", "-x"], {"a"}),
                         ({"a"}, ["-x"]))


if __name__ == "__main__":
    unittest.main()
