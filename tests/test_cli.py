"""
CLI-ийн тест (Гишүүн 5-ын ажил). Ажиллуулах: python -m unittest discover tests

АНХААР: cli.py бэлэн болоогүй байхад эдгээр тест унана. Энэ хэвийн.
Гишүүн 2 cli.py-г бичиж дуусахад ногоон болно.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from allocator import Allocator
from cli import handle_command


class TestCli(unittest.TestCase):

    def test_exit_command(self):
        a = Allocator(1000)
        text, should_exit = handle_command(a, "X")
        self.assertTrue(should_exit)

    def test_request_command(self):
        a = Allocator(1000)
        text, should_exit = handle_command(a, "RQ P1 200 F")
        self.assertFalse(should_exit)
        self.assertIn("P1", text)

    def test_unknown_command(self):
        a = Allocator(1000)
        text, should_exit = handle_command(a, "HELLO")
        self.assertIn("Алдаа", text)

    # TODO (Гишүүн 5): нэмэх тестүүд
    #  - STAT-ын гаралтад "Unused" болон "Process P1" байгаа эсэх
    #  - RQ-д хэмжээ нь тоо биш ("RQ P1 abc F") үед "Алдаа" гарах
    #  - RQ-д аргумент дутуу ("RQ P1") үед "Алдаа" гарах
    #  - RL байхгүй процесс дээр "Алдаа" гарах
    #  - жижиг үсгээр ("rq p1 100 f") ажиллах эсэх (шийд: зөвшөөрөх үү, үгүй юу?)


if __name__ == "__main__":
    unittest.main()
