"""Check the REPL, whitespace parser, prompt, and error handling."""

import io
import unittest
from unittest.mock import patch

from src.shell import Shell


class ShellTests(unittest.TestCase):
    """Exercise the public command-dispatch interface."""

    def setUp(self):
        """Capture output independently of the real terminal."""
        self.output = io.StringIO()
        self.shell = Shell(writer=self.output.write)

    def test_prompt_uses_real_os_data(self):
        """The prompt uses getpass and socket rather than fixed names."""
        with patch("src.shell.getpass.getuser", return_value="student"):
            with patch("src.shell.socket.gethostname", return_value="pc"):
                shell = Shell(writer=self.output.write)
        self.assertEqual(shell.prompt, "student@pc:~$ ")

    def test_whitespace_parser_and_arguments(self):
        """Repeated spaces separate arguments and empty input is ignored."""
        received = []
        handlers = {"ls": received.append, "cd": received.append}
        with patch.object(self.shell, "commands", return_value=handlers):
            self.shell.execute("   ls   -a /home  ")
            self.shell.execute("cd /tmp")
            self.shell.execute("  ")
        self.assertEqual(received, [["-a", "/home"], ["/tmp"]])

    def test_unknown_command(self):
        """An unknown command produces an error without stopping."""
        self.shell.execute("unknown")
        self.assertIn("command not found", self.output.getvalue())
        self.assertTrue(self.shell.running)

    def test_exit_rejects_arguments(self):
        """A malformed exit leaves the loop active."""
        self.shell.execute("exit now")
        self.assertTrue(self.shell.running)
        self.assertIn("usage: exit", self.output.getvalue())
        self.shell.execute("exit")
        self.assertFalse(self.shell.running)

    def test_repl_runs_until_exit(self):
        """The real loop consumes commands and stops on exit."""
        with patch("builtins.input", side_effect=["ls", "bad", "exit"]):
            self.shell.run()
        self.assertFalse(self.shell.running)
        self.assertIn("bad: command not found", self.output.getvalue())

    def test_repl_handles_interrupt_and_eof(self):
        """Ctrl+C does not terminate the process; EOF ends the loop."""
        with patch("builtins.input", side_effect=[KeyboardInterrupt, EOFError]):
            self.shell.run()
        self.assertEqual(self.output.getvalue(), "\n\n")


if __name__ == "__main__":
    unittest.main()
