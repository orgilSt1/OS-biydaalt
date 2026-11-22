"""
Memory layout зургийн тест. tkinter, дэлгэц ХЭРЭГГҮЙ: хуурамч canvas нь зурах дуудлагуудыг л тэмдэглэнэ.
Ажиллуулах (repo-ийн үндсэн фолдероос):
    python -m unittest discover tests        (Windows)
    python3 -m unittest discover tests       (Linux)
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from allocator import Allocator
import gui_canvas
from gui_canvas import draw_memory, color_for, reset_colors, MIN_BLOCK_PX, PROCESS_COLORS


class FakeCanvas:
    """tkinter.Canvas-ийн зурах дуудлагуудыг тэмдэглэдэг хуурамч хувилбар."""

    def __init__(self, width=800):
        self.width = width
        self.rects = []      # (x1, y1, x2, y2, fill)
        self.texts = []      # текст
        self.height = None

    def delete(self, *args):
        self.rects = []
        self.texts = []

    def winfo_width(self):
        return self.width

    def create_rectangle(self, x1, y1, x2, y2, **kw):
        self.rects.append((x1, y1, x2, y2, kw.get("fill")))

    def create_text(self, x, y, **kw):
        self.texts.append(kw.get("text", ""))

    def create_line(self, *args, **kw):
        pass

    def config(self, **kw):
        if "height" in kw:
            self.height = kw["height"]


def bar_rects(canvas):
    """Санах ойн мөрийн (BAR_TOP-ээс эхэлсэн) тэгш өнцөгтүүд."""
    return [r for r in canvas.rects if r[1] == gui_canvas.BAR_TOP]


class TestTinyBlocks(unittest.TestCase):
    """R-4: 1-2 byte-ийн блок өмнө нь <1 px байж зурагт харагддаггүй байсан (БД1 known issue)."""

    def setUp(self):
        reset_colors()

    def make(self):
        a = Allocator(1000)
        for name, size in (("X", 600), ("A", 1), ("B", 150), ("C", 2), ("E", 1), ("F", 100)):
            a.request(name, size, "F")
        a.release("X")
        a.release("B")
        return a

    def test_every_process_has_a_visible_rectangle(self):
        a = self.make()
        canvas = FakeCanvas()
        draw_memory(canvas, a.get_blocks(), a.max_size)
        for name in ("A", "C", "E"):
            fill = color_for(name)
            widths = [r[2] - r[0] for r in bar_rects(canvas) if r[4] == fill]
            self.assertTrue(widths, name + " огт зурагдаагүй")
            self.assertGreaterEqual(max(widths), MIN_BLOCK_PX, name + " харагдахааргүй нарийхан")

    def test_narrow_markers_do_not_overlap(self):
        a = self.make()
        canvas = FakeCanvas()
        draw_memory(canvas, a.get_blocks(), a.max_size)
        markers = []
        for name in ("A", "C", "E"):
            fill = color_for(name)
            markers.extend([r for r in bar_rects(canvas) if r[4] == fill and abs((r[2] - r[0]) - MIN_BLOCK_PX) < 0.01])
        self.assertEqual(len(markers), 3)            # A, C, E тус бүр нэг маркертай
        markers.sort()
        for left, right in zip(markers, markers[1:]):
            self.assertLessEqual(left[2], right[0] + 0.01, "жижиг блокууд бие биеэ халхлаж байна")

    def test_legend_shows_exact_size_and_address(self):
        a = self.make()
        canvas = FakeCanvas()
        draw_memory(canvas, a.get_blocks(), a.max_size)
        joined = "\n".join(canvas.texts)
        self.assertIn("A  [600:600]  1 byte", joined)
        self.assertIn("C  [751:752]  2 byte", joined)

    def test_no_note_when_all_blocks_wide(self):
        a = Allocator(1000)
        a.request("P1", 500, "F")
        canvas = FakeCanvas()
        draw_memory(canvas, a.get_blocks(), a.max_size)
        self.assertFalse(any("Тайлбар" in t for t in canvas.texts))

    def test_tiny_hole_is_visible_too(self):
        a = Allocator(1000)
        a.request("A", 500, "F")
        a.request("B", 1, "F")
        a.request("C", 499, "F")
        a.release("B")                               # 1 byte-ийн hole
        canvas = FakeCanvas()
        draw_memory(canvas, a.get_blocks(), a.max_size)
        hole_marks = [r for r in bar_rects(canvas) if r[4] == gui_canvas.HOLE_COLOR and r[2] - r[0] >= MIN_BLOCK_PX]
        self.assertTrue(hole_marks)

    def test_block_at_memory_edges_stays_inside_bar(self):
        a = Allocator(1000)
        a.request("A", 1, "F")                       # хамгийн зүүн
        a.request("M", 998, "F")
        a.request("Z", 1, "F")                       # хамгийн баруун
        canvas = FakeCanvas()
        draw_memory(canvas, a.get_blocks(), a.max_size)
        for r in bar_rects(canvas):
            self.assertGreaterEqual(r[0], gui_canvas.MARGIN - 0.01)
            self.assertLessEqual(r[2], 800 - gui_canvas.MARGIN + 0.01)


class TestColors(unittest.TestCase):
    """R-5: 12-оос олон нэр дараалан ашиглагдахад амьд процессуудын өнгө давхцдаг байсан."""

    def setUp(self):
        reset_colors()

    def test_live_processes_have_distinct_colors_after_many_names(self):
        """Өнгөний давхцал нь 'зэрэг амьд байх' мөчид гардаг тул АЛХАМ БҮРД шалгана."""
        a = Allocator(100000)
        canvas = FakeCanvas()
        a.request("keep1", 100, "F")
        a.request("keep2", 100, "F")
        draw_memory(canvas, a.get_blocks(), a.max_size)
        for i in range(30):                          # 30 түр процесс орж гарна (палитр 12 өнгөтэй)
            name = "T" + str(i)
            a.request(name, 100, "F")
            draw_memory(canvas, a.get_blocks(), a.max_size)
            live = [b.owner for b in a.get_blocks() if not b.is_hole()]
            colors = [color_for(n) for n in live]
            self.assertEqual(len(set(colors)), len(colors), "алхам " + str(i) + ": " + str(colors))
            a.release(name)
            draw_memory(canvas, a.get_blocks(), a.max_size)

    def test_color_is_stable_while_process_lives(self):
        a = Allocator(1000)
        canvas = FakeCanvas()
        a.request("A", 100, "F")
        a.request("B", 100, "F")
        draw_memory(canvas, a.get_blocks(), a.max_size)
        color_b = color_for("B")
        a.release("A")                               # өөр процесс чөлөөлөгдөхөд B-ийн өнгө солигдохгүй
        draw_memory(canvas, a.get_blocks(), a.max_size)
        self.assertEqual(color_for("B"), color_b)

    def test_palette_has_twelve_unique_colors(self):
        self.assertEqual(len(set(PROCESS_COLORS)), 12)


class TestCanvasConsistency(unittest.TestCase):
    """R-8: gui_canvas нь fragmentation-ийн томьёог allocator-оос тусад нь (зориуд) бодно.
    Хоёр томьёо зөрөхгүйг санамсаргүй төлвүүд дээр шалгана."""

    def test_canvas_fragmentation_equals_allocator_stats(self):
        import random
        rng = random.Random(3)
        a = Allocator(5000)
        live = []
        for i in range(400):
            if rng.random() < 0.6 or not live:
                name = "P" + str(i)
                if a.request(name, rng.randint(1, 400), rng.choice("FBW"))[0]:
                    live.append(name)
            else:
                a.release(live.pop(rng.randrange(len(live))))
            hole_count, free, largest, percent = gui_canvas._fragmentation_info(a.get_blocks())
            stats = a.get_stats()
            self.assertEqual(hole_count, stats["hole_count"])
            self.assertEqual(free, stats["free"])
            self.assertEqual(largest, stats["largest_hole"])
            self.assertAlmostEqual(percent, stats["external_fragmentation"])


class TestLegendLayout(unittest.TestCase):

    def setUp(self):
        reset_colors()

    def test_height_grows_with_many_processes(self):
        a = Allocator(10000)
        for i in range(12):
            a.request("P" + str(i), 10, "F")
        canvas = FakeCanvas()
        draw_memory(canvas, a.get_blocks(), a.max_size)
        self.assertGreater(canvas.height, 170)

    def test_unwindowed_canvas_uses_default_width(self):
        canvas = FakeCanvas(width=1)                 # цонх хараахан зурагдаагүй
        a = Allocator(1000)
        a.request("P1", 100, "F")
        draw_memory(canvas, a.get_blocks(), a.max_size)
        self.assertTrue(bar_rects(canvas))


if __name__ == "__main__":
    unittest.main()
