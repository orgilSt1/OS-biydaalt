"""
CLI-ийн тест. Ажиллуулах (repo-ийн үндсэн фолдероос):
    python -m unittest discover tests        (Windows)
    python3 -m unittest discover tests       (Linux)
"""
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(__file__)
SRC = os.path.join(HERE, "..", "src")
EXAMPLES = os.path.join(HERE, "..", "examples")
sys.path.insert(0, SRC)
from allocator import Allocator
from cli import handle_command, format_status


def run_cli(args, input_text=""):
    """cli.py-г тусдаа процесс болгон ажиллуулж, гаралтыг нь буцаана."""
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    result = subprocess.run([sys.executable, os.path.join(SRC, "cli.py")] + args,
                            input=input_text, capture_output=True, text=True,
                            encoding="utf-8", env=env)
    return result.stdout.replace("\r\n", "\n")


class TestHandleCommand(unittest.TestCase):

    def test_exit_command(self):
        a = Allocator(1000)
        text, should_exit = handle_command(a, "X")
        self.assertTrue(should_exit)

    def test_request_command(self):
        a = Allocator(1000)
        text, should_exit = handle_command(a, "RQ P1 200 F")
        self.assertFalse(should_exit)
        self.assertIn("P1", text)
        self.assertIn("[0:199]", text)

    def test_unknown_command(self):
        a = Allocator(1000)
        text, should_exit = handle_command(a, "HELLO")
        self.assertIn("Алдаа", text)
        self.assertFalse(should_exit)

    def test_empty_line(self):
        a = Allocator(1000)
        self.assertEqual(handle_command(a, ""), ("", False))
        self.assertEqual(handle_command(a, "   "), ("", False))

    def test_lowercase_command_accepted(self):
        a = Allocator(1000)
        text, should_exit = handle_command(a, "rq P1 100 f")
        self.assertIn("олгов", text)

    def test_request_size_not_a_number(self):
        a = Allocator(1000)
        text, _ = handle_command(a, "RQ P1 abc F")
        self.assertIn("Алдаа", text)

    def test_request_missing_arguments(self):
        a = Allocator(1000)
        text, _ = handle_command(a, "RQ P1")
        self.assertIn("Хэрэглээ", text)

    def test_request_bad_strategy(self):
        a = Allocator(1000)
        text, _ = handle_command(a, "RQ P1 100 Z")
        self.assertIn("Алдаа", text)

    def test_release_unknown_process(self):
        a = Allocator(1000)
        text, _ = handle_command(a, "RL NOPE")
        self.assertIn("Алдаа", text)

    def test_release_and_compact(self):
        a = Allocator(1000)
        handle_command(a, "RQ A 100 F")
        handle_command(a, "RQ B 100 F")
        text, _ = handle_command(a, "RL A")
        self.assertIn("чөлөөллөө", text)
        text, _ = handle_command(a, "C")
        self.assertIn("Compaction", text)
        self.assertEqual(a.get_stats()["hole_count"], 1)

    def test_extra_arguments_rejected(self):
        a = Allocator(1000)
        text, should_exit = handle_command(a, "X now")
        self.assertIn("Хэрэглээ", text)
        self.assertFalse(should_exit)


class TestStatFormat(unittest.TestCase):
    """Номын STAT-ын формат: Addresses [эхлэх:төгсөх] Process <нэр> / Unused"""

    def test_stat_initial(self):
        a = Allocator(1000)
        self.assertEqual(format_status(a), "Addresses [0:999] Unused")

    def test_stat_after_request(self):
        a = Allocator(1000)
        handle_command(a, "RQ P1 200 F")
        text, _ = handle_command(a, "STAT")
        lines = text.split("\n")
        self.assertEqual(lines[0], "Addresses [0:199] Process P1")
        self.assertEqual(lines[1], "Addresses [200:999] Unused")
        self.assertEqual(len(lines), 2)


class TestProgram(unittest.TestCase):
    """cli.py-г бүтнээр нь (процесс болгон) ажиллуулах тест."""

    def test_no_argument(self):
        out = run_cli([])
        self.assertIn("Хэрэглээ", out)

    def test_bad_memory_size(self):
        for bad in ("abc", "0", "-10"):
            out = run_cli([bad])
            self.assertIn("Алдаа", out, "хэмжээ: " + bad)

    def test_examples_match_expected_output(self):
        """examples/*.txt бүрийг ажиллуулж, *.expected.txt-тэй харьцуулна."""
        names = ["example1", "example2_fits", "example3_compaction", "example4_errors"]
        for name in names:
            with open(os.path.join(EXAMPLES, name + ".txt"), encoding="utf-8") as f:
                commands = f.read()
            with open(os.path.join(EXAMPLES, name + ".expected.txt"), encoding="utf-8") as f:
                expected = f.read().replace("\r\n", "\n")
            actual = run_cli(["1000"], commands)
            self.assertEqual(actual, expected, name + " гаралт зөрлөө")


if __name__ == "__main__":
    unittest.main()
