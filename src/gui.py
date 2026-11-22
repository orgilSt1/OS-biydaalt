import tkinter as tk
from tkinter import messagebox

from allocator import Allocator, parse_int
from gui_canvas import draw_memory, reset_colors

COLOR_OK = "#0b6b0b"       # амжилттай мессеж (ногоон)
COLOR_ERROR = "red"        # алдааны мессеж (улаан)
COLOR_INFO = "blue"        # мэдээллийн мессеж (цэнхэр)
DEFAULT_SIZE = "1000"      # анхдагч санах ойн хэмжээ (byte)

# "Жишээ ачаалах" товчийн анхдагч сценари (БД1 тайлан, Manual-ийн 1.7 Жишээ 2-той ижил эхлэл)
DEMO_STEPS = (
    ("RQ", ("P1", 200, "F")),
    ("RQ", ("P2", 300, "F")),
    ("RQ", ("P3", 100, "F")),
    ("RL", ("P2",)),
)


class App:
    def __init__(self, root):
        self.root = root
        root.title("Contiguous Memory Allocation")
        self.allocator = None            # on_start() дуудсаны дараа үүснэ
        self.undo_stack = []             # өөрчлөлт бүрийн өмнөх төлөв (Undo-д)
        self.step_number = 0             # командын түүхийн дугаар
        self.build_widgets()
        self.on_start()                  # анхдагч 1000 byte-аар шууд эхэлнэ

    def build_widgets(self):
        """Цонхны бүх хэсгийг үүсгэнэ."""
        # --- 1. Санах ойн хэмжээ оруулах мөр ---
        top = tk.Frame(self.root)
        top.pack(fill="x", padx=10, pady=5)
        tk.Label(top, text="Санах ойн хэмжээ (byte):").pack(side="left")
        self.size_entry = tk.Entry(top, width=12)
        self.size_entry.insert(0, DEFAULT_SIZE)
        self.size_entry.pack(side="left", padx=5)
        self.size_entry.bind("<Return>", lambda event: self.on_start())
        tk.Button(top, text="Эхлүүлэх / Reset", command=self.on_start).pack(side="left")
        tk.Button(top, text="Жишээ ачаалах", command=self.on_demo).pack(side="left", padx=(10, 0))
        self.undo_button = tk.Button(top, text="Undo (буцаах)", command=self.on_undo, state="disabled")
        self.undo_button.pack(side="left", padx=(10, 0))

        # --- 2. Зураг ---
        self.canvas = tk.Canvas(self.root, width=800, height=170, bg="white")
        self.canvas.pack(padx=10, pady=5)

        # --- 3. Мессеж харуулах мөр ---
        self.message_var = tk.StringVar()
        self.message_label = tk.Label(self.root, textvariable=self.message_var,
                                      fg=COLOR_INFO, wraplength=780)
        self.message_label.pack(pady=2)

        # --- 4. Хүсэлтийн мөр (RQ) ---
        request_frame = tk.LabelFrame(self.root, text="Санах ой хүсэх (RQ)")
        request_frame.pack(fill="x", padx=10, pady=5)
        request_row = tk.Frame(request_frame)
        request_row.pack(fill="x")

        tk.Label(request_row, text="Процессын нэр:").pack(side="left", padx=(5, 0))
        self.rq_name_entry = tk.Entry(request_row, width=10)
        self.rq_name_entry.pack(side="left", padx=5)

        tk.Label(request_row, text="Хэмжээ (byte):").pack(side="left")
        self.rq_size_entry = tk.Entry(request_row, width=10)
        self.rq_size_entry.pack(side="left", padx=5)

        tk.Label(request_row, text="Стратеги:").pack(side="left")
        self.strategy_var = tk.StringVar(value="F")
        for code, title in (("F", "F (First)"), ("B", "B (Best)"), ("W", "W (Worst)")):
            tk.Radiobutton(request_row, text=title, variable=self.strategy_var,
                           value=code).pack(side="left")

        tk.Button(request_row, text="RQ", width=6,
                  command=self.on_request).pack(side="left", padx=10, pady=3)

        # Хэмжээ бичих бүрт F/B/W хаана олгохыг (төлөв өөрчлөхгүй) харуулна
        self.preview_var = tk.StringVar()
        tk.Label(request_frame, textvariable=self.preview_var, anchor="w", fg="#333333",
                 font=("Helvetica", 9)).pack(fill="x", padx=5, pady=(0, 3))

        # Enter дарахад RQ ажиллана
        self.rq_name_entry.bind("<Return>", lambda event: self.on_request())
        self.rq_size_entry.bind("<Return>", lambda event: self.on_request())
        self.rq_size_entry.bind("<KeyRelease>", lambda event: self.update_preview())

        # --- 5. Чөлөөлөх мөр (RL) ---
        release_frame = tk.LabelFrame(self.root, text="Санах ой чөлөөлөх (RL)")
        release_frame.pack(fill="x", padx=10, pady=5)

        tk.Label(release_frame, text="Процессын нэр:").pack(side="left", padx=(5, 0))
        self.rl_name_entry = tk.Entry(release_frame, width=10)
        self.rl_name_entry.pack(side="left", padx=5)
        tk.Button(release_frame, text="RL", width=6,
                  command=self.on_release).pack(side="left", padx=10, pady=3)
        self.rl_name_entry.bind("<Return>", lambda event: self.on_release())

        # --- 6. Compaction товч ---
        tk.Button(self.root, text="C (Compaction)",
                  command=self.on_compact).pack(pady=5)

        # --- 7. Статистик ---
        stats_frame = tk.LabelFrame(self.root, text="Статистик")
        stats_frame.pack(fill="x", padx=10, pady=5)
        self.stats_var = tk.StringVar()
        tk.Label(stats_frame, textvariable=self.stats_var, justify="left",
                 anchor="w").pack(fill="x", padx=5, pady=3)
        self.stats_var.set("Санах ойг эхлүүлээгүй байна")

        # --- 8. Командын түүх ---
        history_frame = tk.LabelFrame(self.root, text="Командын түүх")
        history_frame.pack(fill="both", padx=10, pady=(5, 10))
        scrollbar = tk.Scrollbar(history_frame)
        scrollbar.pack(side="right", fill="y")
        self.history = tk.Listbox(history_frame, height=6, yscrollcommand=scrollbar.set,
                                  activestyle="none")
        self.history.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.history.yview)

    # ------------------------------------------------------------
    # Туслах функцүүд
    # ------------------------------------------------------------

    def show_message(self, message, ok=True):
        """Мессежийг харуулна: амжилттай бол ногоон, алдаа бол улаан."""
        self.message_label.config(fg=COLOR_OK if ok else COLOR_ERROR)
        self.message_var.set(message)

    def add_history(self, command, message, ok=True):
        """Командын түүхэнд нэг мөр нэмнэ (алдаа бол улаан)."""
        self.step_number = self.step_number + 1
        self.history.insert(tk.END, str(self.step_number) + ". " + command + "  ->  " + message)
        last = self.history.size() - 1
        if not ok:
            self.history.itemconfig(last, fg=COLOR_ERROR)
        self.history.see(tk.END)

    def check_started(self):
        """Allocator эхэлсэн эсэхийг шалгана. Эхлээгүй бол алдаа үзүүлж False буцаана."""
        if self.allocator is None:
            messagebox.showerror("Алдаа", "Эхлээд санах ойн хэмжээг оруулж 'Эхлүүлэх / Reset' дарна уу")
            return False
        return True

    def run(self, command, action):
        """Allocator-ийн үйлдлийг ажиллуулж, мессеж, түүх, Undo, зургийг нэг дор шинэчилнэ.
        action нь allocator-ийн (ok, message) буцаадаг функц."""
        before = self.allocator.snapshot()
        ok, message = action()
        if ok and self.allocator.snapshot() != before:
            self.undo_stack.append(before)        # төлөв үнэхээр өөрчлөгдсөн үед л Undo-д орно
        self.show_message(message, ok)
        self.add_history(command, message, ok)
        self.refresh()
        return ok

    def update_preview(self):
        """RQ-ийн хэмжээний талбарт бичсэн утгаар F/B/W хаана олгохыг урьдчилан харуулна."""
        text = self.rq_size_entry.get().strip()
        if self.allocator is None or text == "":
            self.preview_var.set("Хэмжээ бичвэл F / B / W стратеги хаана олгохыг энд урьдчилан харуулна")
            return
        try:
            size = parse_int(text)
        except ValueError:
            self.preview_var.set("Урьдчилан харах: хэмжээ бүхэл тоо байх ёстой")
            return
        if size <= 0:
            self.preview_var.set("Урьдчилан харах: хэмжээ 0-ээс их байх ёстой")
            return
        parts = []
        result = self.allocator.preview(size)
        for strategy in ("F", "B", "W"):
            found = result[strategy]
            if found is None:
                parts.append(strategy + ": багтах hole алга")
            else:
                start, hole_size = found
                parts.append(strategy + ": [" + str(start) + ":" + str(start + size - 1)
                             + "] (hole " + str(hole_size) + ")")
        self.preview_var.set(str(size) + " byte хүсвэл ->  " + "   |   ".join(parts))

    # ------------------------------------------------------------
    # Товчнуудын үйлдэл
    # ------------------------------------------------------------

    def on_start(self):
        """Санах ойг эхлүүлэх эсвэл reset хийх. Түүх болон Undo цэвэрлэгдэнэ."""
        try:
            size = parse_int(self.size_entry.get())
            allocator = Allocator(size)
        except ValueError:
            messagebox.showerror("Алдаа", "Санах ойн хэмжээ 0-ээс их бүхэл тоо байх ёстой")
            return
        self.allocator = allocator
        self.undo_stack = []
        self.step_number = 0
        self.history.delete(0, tk.END)
        reset_colors()
        self.show_message("Санах ой " + str(size) + " byte-аар эхэллээ", True)
        self.add_history("RESET " + str(size), "нэг hole [0:" + str(size - 1) + "]", True)
        self.refresh()

    def on_demo(self):
        """Анхдагч сценарийг (P1 200, P2 300, P3 100 хүсээд P2 чөлөөлөх) алхам алхмаар ачаална."""
        self.size_entry.delete(0, tk.END)
        self.size_entry.insert(0, DEFAULT_SIZE)
        self.on_start()
        for kind, args in DEMO_STEPS:
            if kind == "RQ":
                name, size, strategy = args
                self.run("RQ " + name + " " + str(size) + " " + strategy,
                         lambda a=args: self.allocator.request(a[0], a[1], a[2]))
            else:
                self.run("RL " + args[0], lambda a=args: self.allocator.release(a[0]))
        self.show_message("Жишээ ачаалав: hole [200:499] ба [600:999] (fragmentation). "
                          "Хэмжээний талбарт 250 бичвэл F/B/W хаана олгохыг харна", True)

    def on_request(self):
        """RQ товч дарахад: оролтыг уншиж, allocator.request() дуудаад зургийг шинэчилнэ."""
        if not self.check_started():
            return
        name = self.rq_name_entry.get().strip()
        try:
            size = parse_int(self.rq_size_entry.get())
        except ValueError:
            self.show_message("Алдаа: хэмжээ бүхэл тоо байх ёстой", False)
            return
        strategy = self.strategy_var.get()
        command = "RQ " + name + " " + str(size) + " " + strategy
        ok = self.run(command, lambda: self.allocator.request(name, size, strategy))
        if ok:
            self.rq_name_entry.delete(0, tk.END)      # дараагийн хүсэлтэд бэлдэнэ
            self.rq_size_entry.delete(0, tk.END)
            self.rq_name_entry.focus_set()
            self.update_preview()

    def on_release(self):
        """RL товч дарахад: allocator.release() дуудна."""
        if not self.check_started():
            return
        name = self.rl_name_entry.get().strip()
        if name == "":
            self.show_message("Алдаа: процессын нэр хоосон байна", False)
            return
        ok = self.run("RL " + name, lambda: self.allocator.release(name))
        if ok:
            self.rl_name_entry.delete(0, tk.END)

    def on_compact(self):
        """C товч дарахад: allocator.compact() дуудна."""
        if not self.check_started():
            return
        self.run("C", self.allocator.compact)

    def on_undo(self):
        """Сүүлийн өөрчлөлтийг буцаана."""
        if self.allocator is None or len(self.undo_stack) == 0:
            self.show_message("Буцаах үйлдэл алга", False)
            return
        self.allocator.restore(self.undo_stack.pop())
        message = "Сүүлийн өөрчлөлтийг буцаалаа"
        self.show_message(message, True)
        self.add_history("UNDO", message, True)
        self.refresh()

    def refresh(self):
        """Зураг, статистик, Undo товч, урьдчилан харалтыг шинэчилнэ. Allocator-ийн ямар ч өөрчлөлтийн дараа дуудна."""
        if self.allocator is None:
            return
        draw_memory(self.canvas, self.allocator.get_blocks(), self.allocator.max_size)
        stats = self.allocator.get_stats()
        self.stats_var.set(
            "Нийт: " + str(stats["total"]) + " byte"
            + "   Ашигласан: " + str(stats["used"]) + " byte"
            + "   Чөлөөт: " + str(stats["free"]) + " byte"
            + "   Процессын тоо: " + str(stats["process_count"]) + "\n"
            + "Hole-ын тоо: " + str(stats["hole_count"])
            + "   Хамгийн том hole: " + str(stats["largest_hole"]) + " byte"
            + "   Гадаад fragmentation: " + format(stats["external_fragmentation"], ".1f") + "%"
        )
        self.undo_button.config(state="normal" if len(self.undo_stack) > 0 else "disabled")
        self.update_preview()


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
