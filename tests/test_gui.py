"""
GUI-ийн тест: жинхэнэ tkinter цонхыг үүсгэж, товчнуудын үйлдлийг дуудна.
Дэлгэц (display) эсвэл tkinter байхгүй орчинд (жишээ нь серверийн терминал) тест өөрөө алгасагдана (skipped).
Linux дээр дэлгэцгүй ажиллуулах бол:  xvfb-run -a python3 -m unittest discover tests
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

try:
    import tkinter as tk
    _probe = tk.Tk()
    _probe.destroy()
    HAS_DISPLAY = True
except Exception:                                   # tkinter суугаагүй эсвэл дэлгэц байхгүй
    HAS_DISPLAY = False


@unittest.skipUnless(HAS_DISPLAY, "tkinter эсвэл дэлгэц байхгүй")
class TestGuiApp(unittest.TestCase):

    def setUp(self):
        from gui import App
        self.root = tk.Tk()
        self.app = App(self.root)

    def tearDown(self):
        self.root.destroy()

    def request(self, name, size, strategy="F"):
        self.app.rq_name_entry.delete(0, tk.END)
        self.app.rq_name_entry.insert(0, name)
        self.app.rq_size_entry.delete(0, tk.END)
        self.app.rq_size_entry.insert(0, str(size))
        self.app.strategy_var.set(strategy)
        self.app.on_request()

    def blocks(self):
        return [(b.start, b.size, b.owner) for b in self.app.allocator.get_blocks()]

    def test_starts_with_default_memory(self):
        """Анхдагч 1000 byte-аар шууд эхэлнэ (өмнө нь 'Эхлүүлэх' дарах хэрэгтэй байсан)."""
        self.assertIsNotNone(self.app.allocator)
        self.assertEqual(self.app.allocator.max_size, 1000)
        self.assertEqual(self.app.history.size(), 1)

    def test_request_updates_allocator_and_history(self):
        self.request("P1", 200, "F")
        self.assertEqual(self.blocks()[0], (0, 200, "P1"))
        self.assertIn("RQ P1 200 F", self.app.history.get(tk.END))

    def test_invalid_size_does_not_change_state(self):
        before = self.blocks()
        for bad in ("abc", "1_0", "0", "-4", ""):
            self.request("P1", bad)
        self.assertEqual(self.blocks(), before)

    def test_undo_restores_previous_state(self):
        self.request("P1", 200)
        self.request("P2", 300)
        self.app.on_undo()
        self.assertEqual([b[2] for b in self.blocks() if b[2]], ["P1"])
        self.app.on_undo()
        self.assertEqual(len(self.blocks()), 1)
        self.assertEqual(str(self.app.undo_button.cget("state")), "disabled")

    def test_failed_request_is_not_undoable(self):
        self.request("P1", 200)
        self.request("BIG", 5000)                    # алдаа
        self.assertEqual(len(self.app.undo_stack), 1)

    def test_noop_compaction_is_not_undoable(self):
        self.app.on_compact()                        # hole нэг л байна: өөрчлөлт байхгүй
        self.assertEqual(len(self.app.undo_stack), 0)

    def test_demo_loads_fragmented_state(self):
        self.app.on_demo()
        self.assertEqual(self.blocks(), [(0, 200, "P1"), (200, 300, None),
                                         (500, 100, "P3"), (600, 400, None)])
        self.assertEqual(len(self.app.undo_stack), 4)

    def test_reset_clears_history_and_undo(self):
        self.app.on_demo()
        self.app.size_entry.delete(0, tk.END)
        self.app.size_entry.insert(0, "2000")
        self.app.on_start()
        self.assertEqual(self.app.allocator.max_size, 2000)
        self.assertEqual(len(self.app.undo_stack), 0)
        self.assertEqual(self.app.history.size(), 1)

    def test_preview_text_shows_all_strategies(self):
        self.app.on_demo()
        self.app.rq_size_entry.delete(0, tk.END)
        self.app.rq_size_entry.insert(0, "250")
        self.app.update_preview()
        text = self.app.preview_var.get()
        self.assertIn("F: [200:449]", text)
        self.assertIn("B: [200:449]", text)
        self.assertIn("W: [600:849]", text)

    def test_preview_handles_bad_input(self):
        for bad in ("abc", "-3", "0", "1_0"):
            self.app.rq_size_entry.delete(0, tk.END)
            self.app.rq_size_entry.insert(0, bad)
            self.app.update_preview()
            self.assertIn("Урьдчилан харах", self.app.preview_var.get(), bad)


if __name__ == "__main__":
    unittest.main()
