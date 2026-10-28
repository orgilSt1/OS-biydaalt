"""
Allocator-ийн тест. Ажиллуулах (repo-ийн үндсэн фолдероос):
    python -m unittest discover tests        (Windows)
    python3 -m unittest discover tests       (Linux)
"""
import os
import sys
import unittest

# src фолдерыг Python-д танилцуулна
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from allocator import Allocator


def start_of(allocator, name):
    """Процессын эхлэх хаягийг буцаана."""
    for block in allocator.get_blocks():
        if block.owner == name:
            return block.start
    return None


def make_allocator():
    """1000 нэгж санах ой. Дараах байдалтай болгоно:
       hole 200 @0 | P 50 @200 | hole 80 @250 | Q 50 @330 | hole 620 @380"""
    a = Allocator(1000)
    a.request("A", 200, "F")
    a.request("P", 50, "F")
    a.request("B", 80, "F")
    a.request("Q", 50, "F")
    a.release("A")
    a.release("B")
    return a


class TestAllocator(unittest.TestCase):

    def test_initial_state(self):
        a = Allocator(1000)
        blocks = a.get_blocks()
        self.assertEqual(len(blocks), 1)
        self.assertTrue(blocks[0].is_hole())
        self.assertEqual(blocks[0].size, 1000)

    def test_first_fit(self):
        a = make_allocator()
        ok, msg = a.request("X", 70, "F")
        self.assertTrue(ok)
        self.assertEqual(start_of(a, "X"), 0)      # анхны hole (200)

    def test_best_fit(self):
        a = make_allocator()
        ok, msg = a.request("X", 70, "B")
        self.assertTrue(ok)
        self.assertEqual(start_of(a, "X"), 250)    # хамгийн жижиг тохирох (80)

    def test_worst_fit(self):
        a = make_allocator()
        ok, msg = a.request("X", 70, "W")
        self.assertTrue(ok)
        self.assertEqual(start_of(a, "X"), 380)    # хамгийн том (620)

    def test_release_merges_holes(self):
        a = Allocator(1000)
        a.request("A", 100, "F")
        a.request("B", 100, "F")
        a.request("C", 100, "F")
        a.release("A")
        a.release("C")
        a.release("B")
        blocks = a.get_blocks()
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0].size, 1000)

    def test_compact(self):
        a = make_allocator()
        ok, msg = a.compact()
        self.assertTrue(ok)
        self.assertEqual(start_of(a, "P"), 0)
        self.assertEqual(start_of(a, "Q"), 50)
        stats = a.get_stats()
        self.assertEqual(stats["hole_count"], 1)
        self.assertEqual(stats["largest_hole"], 900)

    def test_bad_inputs(self):
        a = Allocator(1000)
        self.assertFalse(a.request("A", 0, "F")[0])       # хэмжээ 0
        self.assertFalse(a.request("A", -5, "F")[0])      # сөрөг хэмжээ
        self.assertFalse(a.request("A", 10, "Z")[0])      # буруу стратеги
        self.assertFalse(a.release("NOPE")[0])            # байхгүй процесс
        a.request("A", 10, "F")
        self.assertFalse(a.request("A", 10, "F")[0])      # давхар нэр

    def test_name_with_space_rejected(self):
        a = Allocator(1000)
        ok, msg = a.request("P 1", 10, "F")
        self.assertFalse(ok)

    def test_book_compaction_example(self):
        """Номын жишээ: 550, 375, 1900, 4500 KB-ийн дөрвөн hole -> 7325 KB нэг hole"""
        a = Allocator(7625)                    # 7325 (hole) + 3 x 100 (тусгаарлагч процесс) 
        a.request("H1", 550, "F")
        a.request("A", 100, "F")
        a.request("H2", 375, "F")
        a.request("B", 100, "F")
        a.request("H3", 1900, "F")
        a.request("C", 100, "F")
        a.request("H4", 4500, "F")
        for name in ("H1", "H2", "H3", "H4"):
            a.release(name)
        self.assertEqual(a.get_stats()["hole_count"], 4)
        a.compact()
        stats = a.get_stats()
        self.assertEqual(stats["hole_count"], 1)
        self.assertEqual(stats["largest_hole"], 7325)

    def test_not_enough_memory(self):
        a = Allocator(100)
        ok, msg = a.request("A", 101, "F")
        self.assertFalse(ok)

    def test_needs_compaction(self):
        a = make_allocator()
        ok, msg = a.request("BIG", 700, "F")     # чөлөөт 900, гэхдээ хамгийн том hole 620
        self.assertFalse(ok)
        a.compact()
        ok, msg = a.request("BIG", 700, "F")
        self.assertTrue(ok)

    # TODO (Гишүүн 5): энд өөрийн тестүүдийг нэмнэ (docs/TASKS.md-г үз)


if __name__ == "__main__":
    unittest.main()
