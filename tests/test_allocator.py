"""
Allocator-ийн тест. Ажиллуулах (repo-ийн үндсэн фолдероос):
    python -m unittest discover tests        (Windows)
    python3 -m unittest discover tests       (Linux)
"""
import os
import random
import sys
import unittest

# src фолдерыг Python-д танилцуулна
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from allocator import Allocator, parse_int


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

    def test_exact_size_request(self):
        """Hole-той яг тэнцүү хэмжээтэй хүсэлт: үлдэгдэл hole үүсэхгүй"""
        a = make_allocator()
        ok, msg = a.request("X", 200, "F")       # анхны hole яг 200
        self.assertTrue(ok)
        self.assertEqual(start_of(a, "X"), 0)
        self.assertEqual(a.get_stats()["hole_count"], 2)

    def test_fill_whole_memory_then_fail(self):
        a = Allocator(100)
        self.assertTrue(a.request("A", 100, "F")[0])
        self.assertFalse(a.request("B", 1, "F")[0])
        self.assertEqual(a.get_stats()["free"], 0)

    def test_release_merges_with_left_hole(self):
        a = Allocator(1000)
        a.request("A", 100, "F")
        a.request("B", 100, "F")
        a.request("C", 100, "F")
        a.release("A")
        a.release("B")                           # A-ийн hole-той нэгдэнэ
        blocks = a.get_blocks()
        self.assertEqual(len(blocks), 3)         # [hole 200] [C] [hole 700]
        self.assertEqual(blocks[0].size, 200)

    def test_release_merges_with_right_hole(self):
        a = Allocator(1000)
        a.request("A", 100, "F")
        a.request("B", 100, "F")
        a.request("C", 100, "F")
        a.release("C")                           # төгсгөлийн том hole-той нэгдэнэ
        blocks = a.get_blocks()
        self.assertEqual(len(blocks), 3)         # [A] [B] [hole 800]
        self.assertEqual(blocks[2].size, 800)

    def test_best_fit_tie_takes_first(self):
        """Тэнцүү хэмжээтэй hole олон байвал хаягаар хамгийн эхнийх"""
        a = Allocator(1000)
        a.request("A", 100, "F")
        a.request("P", 50, "F")
        a.request("B", 100, "F")
        a.request("Q", 50, "F")
        a.release("A")
        a.release("B")                           # hole 100 @0 ба hole 100 @150
        a.request("X", 100, "B")
        self.assertEqual(start_of(a, "X"), 0)

    def test_compact_keeps_process_order(self):
        a = Allocator(1000)
        for name in ("A", "B", "C", "D"):
            a.request(name, 100, "F")
        a.release("B")
        a.compact()
        self.assertEqual(start_of(a, "A"), 0)
        self.assertEqual(start_of(a, "C"), 100)
        self.assertEqual(start_of(a, "D"), 200)

    def test_compact_not_needed(self):
        a = Allocator(100)
        a.request("A", 100, "F")                 # hole байхгүй
        ok, msg = a.compact()
        self.assertTrue(ok)
        self.assertIn("хэрэггүй", msg)
        b = Allocator(100)
        b.request("A", 50, "F")                  # нэг hole төгсгөлд
        ok, msg = b.compact()
        self.assertIn("хэрэггүй", msg)

    def test_invalid_memory_size(self):
        for bad in (0, -5, "abc", 10.5):
            with self.assertRaises(ValueError):
                Allocator(bad)

    def test_empty_process_name(self):
        a = Allocator(100)
        self.assertFalse(a.request("", 10, "F")[0])
        self.assertFalse(a.request("   ", 10, "F")[0])

    def test_reset(self):
        a = make_allocator()
        a.reset()
        blocks = a.get_blocks()
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0].size, 1000)
        a.reset(2000)
        self.assertEqual(a.max_size, 2000)
        self.assertEqual(a.get_blocks()[0].size, 2000)

    def test_stats(self):
        a = make_allocator()                     # hole 200, 80, 620 / процесс P 50, Q 50
        stats = a.get_stats()
        self.assertEqual(stats["total"], 1000)
        self.assertEqual(stats["used"], 100)
        self.assertEqual(stats["free"], 900)
        self.assertEqual(stats["hole_count"], 3)
        self.assertEqual(stats["process_count"], 2)
        self.assertEqual(stats["largest_hole"], 620)
        self.assertAlmostEqual(stats["external_fragmentation"], 280 * 100.0 / 900)

    def test_get_blocks_returns_copy(self):
        a = Allocator(100)
        blocks = a.get_blocks()
        blocks[0].owner = "HACK"
        self.assertIsNone(a.get_blocks()[0].owner)


# ----------------------------------------------------------------------
# БД2-т нэмсэн тестүүд (self-review-ийн дагуу)
# ----------------------------------------------------------------------

class TestMessagesAndInput(unittest.TestCase):
    """R-1: бүх мессежийн нэгж 'byte' (өмнө нь 'нэгж' ба 'byte' холилдсон байсан)."""

    def test_messages_use_byte_unit(self):
        a = make_allocator()
        texts = []
        texts.append(a.release("P")[1])
        texts.append(a.request("BIG", 700, "F")[1])        # fragmentation алдаа
        texts.append(a.compact()[1])
        texts.append(Allocator(100).request("X", 500, "F")[1])   # хүрэлцэхгүй
        for text in texts:
            self.assertIn("byte", text, text)
            self.assertNotIn("нэгж", text, text)

    def test_parse_int_accepts_plain_integers(self):
        self.assertEqual(parse_int("1000"), 1000)
        self.assertEqual(parse_int("  42 "), 42)
        self.assertEqual(parse_int("+5"), 5)
        self.assertEqual(parse_int("-5"), -5)

    def test_parse_int_rejects_python_quirks(self):
        """R-2: int() нь '1_0', арабын цифр зэргийг хүлээн авдаг; бид татгалзана."""
        for bad in ("1_0", "\u0663", "1e3", "1.5", "", "abc", "0x10", "--5", "1 0"):
            with self.assertRaises(ValueError, msg=repr(bad)):
                parse_int(bad)

    def test_bool_is_not_a_valid_size(self):
        """True нь Python-д int тул size=1 гэж ойлгогдож байсан."""
        a = Allocator(100)
        self.assertFalse(a.request("A", True, "F")[0])
        with self.assertRaises(ValueError):
            Allocator(True)


class TestSnapshotAndPreview(unittest.TestCase):

    def test_snapshot_restore_roundtrip(self):
        a = make_allocator()
        snap = a.snapshot()
        before = [(b.start, b.size, b.owner) for b in a.get_blocks()]
        a.request("X", 70, "B")
        a.compact()
        self.assertNotEqual([(b.start, b.size, b.owner) for b in a.get_blocks()], before)
        a.restore(snap)
        self.assertEqual([(b.start, b.size, b.owner) for b in a.get_blocks()], before)

    def test_snapshot_is_independent_of_later_changes(self):
        a = Allocator(100)
        snap = a.snapshot()
        a.request("A", 50, "F")
        a.restore(snap)
        self.assertEqual(len(a.get_blocks()), 1)
        self.assertTrue(a.get_blocks()[0].is_hole())

    def test_preview_matches_real_request(self):
        """preview() төлвийг өөрчлөхгүй, бодит request()-тэй яг ижил хаяг өгнө."""
        a = make_allocator()                      # hole 200 @0, 80 @250, 620 @380
        before = a.snapshot()
        result = a.preview(70)
        self.assertEqual(a.snapshot(), before)    # өөрчлөгдөөгүй
        self.assertEqual(result["F"], (0, 200))
        self.assertEqual(result["B"], (250, 80))
        self.assertEqual(result["W"], (380, 620))
        for strategy in ("F", "B", "W"):
            b = make_allocator()
            b.request("X", 70, strategy)
            self.assertEqual(start_of(b, "X"), result[strategy][0])

    def test_preview_none_when_no_hole_fits(self):
        a = make_allocator()
        self.assertEqual(a.preview(700), {"F": None, "B": None, "W": None})
        self.assertEqual(a.preview(0), {"F": None, "B": None, "W": None})
        self.assertEqual(a.preview(-3), {"F": None, "B": None, "W": None})
        self.assertEqual(a.preview(True), {"F": None, "B": None, "W": None})


def check_invariants(test, a):
    """Allocator-ийн бүтцийн инвариантууд (БД1 тайлан 4.2)."""
    blocks = a.get_blocks()
    test.assertGreater(len(blocks), 0)
    position = 0
    names = []
    for i, block in enumerate(blocks):
        test.assertEqual(block.start, position, "завсар/давхцал")
        test.assertGreater(block.size, 0, "хоосон блок")
        position = position + block.size
        if i > 0:
            test.assertFalse(block.is_hole() and blocks[i - 1].is_hole(), "зэргэлдээ hole нэгдээгүй")
        if not block.is_hole():
            names.append(block.owner)
    test.assertEqual(position, a.max_size, "нийлбэр MAX-тай тэнцэхгүй")
    test.assertEqual(len(names), len(set(names)), "процессын нэр давхардсан")
    stats = a.get_stats()
    test.assertEqual(stats["used"] + stats["free"], stats["total"])


def expected_start(blocks, size, strategy):
    """Стратегийн хүлээгдэх хаягийг ӨӨР, энгийн аргаар (hole-уудыг шүүж) бодно."""
    holes = [(b.start, b.size) for b in blocks if b.is_hole() and b.size >= size]
    if not holes:
        return None
    if strategy == "F":
        return holes[0][0]
    if strategy == "B":
        return min(holes, key=lambda h: (h[1], h[0]))[0]
    return max(holes, key=lambda h: (h[1], -h[0]))[0]


class TestRandomizedInvariants(unittest.TestCase):
    """R-3: санамсаргүй (seed-тэй, давтагдах) дарааллын дараа инвариант хадгалагдаж,
    стратеги бүр бие даасан тооцоотой таарна."""

    def run_random(self, seed, memory, steps):
        rng = random.Random(seed)
        a = Allocator(memory)
        live = []
        counter = 0
        for _ in range(steps):
            roll = rng.random()
            if roll < 0.55 or not live:
                counter = counter + 1
                name = "P" + str(counter)
                size = rng.randint(1, max(1, memory // 8))
                strategy = rng.choice("FBW")
                want = expected_start(a.get_blocks(), size, strategy)
                ok, msg = a.request(name, size, strategy)
                self.assertEqual(ok, want is not None, msg)
                if ok:
                    self.assertEqual(start_of(a, name), want)
                    live.append(name)
            elif roll < 0.92:
                name = live.pop(rng.randrange(len(live)))
                self.assertTrue(a.release(name)[0])
            else:
                order = [b.owner for b in a.get_blocks() if not b.is_hole()]
                a.compact()
                self.assertEqual([b.owner for b in a.get_blocks() if not b.is_hole()], order)
                self.assertLessEqual(a.get_stats()["hole_count"], 1)
            check_invariants(self, a)

    def test_random_small_memory(self):
        for seed in range(20):
            self.run_random(seed, 200, 300)

    def test_random_large_memory(self):
        for seed in range(5):
            self.run_random(100 + seed, 1048576, 500)

    def test_release_everything_gives_single_hole(self):
        rng = random.Random(7)
        a = Allocator(5000)
        names = []
        for i in range(60):
            if a.request("Q" + str(i), rng.randint(1, 200), rng.choice("FBW"))[0]:
                names.append("Q" + str(i))
        rng.shuffle(names)
        for name in names:
            a.release(name)
        blocks = a.get_blocks()
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0].size, 5000)


if __name__ == "__main__":
    unittest.main()
