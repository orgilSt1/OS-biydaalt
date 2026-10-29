import tkinter as tk
from tkinter import messagebox

from allocator import Allocator
from gui_canvas import draw_memory

COLOR_OK = "#0b6b0b"       # амжилттай мессеж (ногоон)
COLOR_ERROR = "red"        # алдааны мессеж (улаан)
COLOR_INFO = "blue"        # мэдээллийн мессеж (цэнхэр)


class App:
    def __init__(self, root):
        self.root = root
        root.title("Contiguous Memory Allocation")
        self.allocator = None            # "Эхлүүлэх" дарсны дараа үүснэ
        self.build_widgets()

    def build_widgets(self):
        """Цонхны бүх хэсгийг үүсгэнэ."""
        # --- 1. Санах ойн хэмжээ оруулах мөр ---
        top = tk.Frame(self.root)
        top.pack(fill="x", padx=10, pady=5)
        tk.Label(top, text="Санах ойн хэмжээ (byte):").pack(side="left")
        self.size_entry = tk.Entry(top, width=12)
        self.size_entry.insert(0, "1000")
        self.size_entry.pack(side="left", padx=5)
        self.size_entry.bind("<Return>", lambda event: self.on_start())
        tk.Button(top, text="Эхлүүлэх / Reset", command=self.on_start).pack(side="left")

        # --- 2. Зураг ---
        self.canvas = tk.Canvas(self.root, width=800, height=150, bg="white")
        self.canvas.pack(padx=10, pady=5)

        # --- 3. Мессеж харуулах мөр ---
        self.message_var = tk.StringVar()
        self.message_label = tk.Label(self.root, textvariable=self.message_var,
                                      fg=COLOR_INFO, wraplength=780)
        self.message_label.pack(pady=2)

        # --- 4. Хүсэлтийн мөр (RQ) ---
        request_frame = tk.LabelFrame(self.root, text="Санах ой хүсэх (RQ)")
        request_frame.pack(fill="x", padx=10, pady=5)

        tk.Label(request_frame, text="Процессын нэр:").pack(side="left", padx=(5, 0))
        self.rq_name_entry = tk.Entry(request_frame, width=10)
        self.rq_name_entry.pack(side="left", padx=5)

        tk.Label(request_frame, text="Хэмжээ (byte):").pack(side="left")
        self.rq_size_entry = tk.Entry(request_frame, width=10)
        self.rq_size_entry.pack(side="left", padx=5)

        tk.Label(request_frame, text="Стратеги:").pack(side="left")
        self.strategy_var = tk.StringVar(value="F")
        for code, title in (("F", "F (First)"), ("B", "B (Best)"), ("W", "W (Worst)")):
            tk.Radiobutton(request_frame, text=title, variable=self.strategy_var,
                           value=code).pack(side="left")

        tk.Button(request_frame, text="RQ", width=6,
                  command=self.on_request).pack(side="left", padx=10, pady=3)

        # Enter дарахад RQ ажиллана
        self.rq_name_entry.bind("<Return>", lambda event: self.on_request())
        self.rq_size_entry.bind("<Return>", lambda event: self.on_request())

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

    # ------------------------------------------------------------
    # Туслах функцүүд
    # ------------------------------------------------------------

    def show_message(self, message, ok=True):
        """Мессежийг харуулна: амжилттай бол ногоон, алдаа бол улаан."""
        self.message_label.config(fg=COLOR_OK if ok else COLOR_ERROR)
        self.message_var.set(message)

    def check_started(self):
        """Allocator эхэлсэн эсэхийг шалгана. Эхлээгүй бол алдаа үзүүлж False буцаана."""
        if self.allocator is None:
            messagebox.showerror("Алдаа", "Эхлээд санах ойн хэмжээг оруулж 'Эхлүүлэх / Reset' дарна уу")
            return False
        return True

    # ------------------------------------------------------------
    # Товчнуудын үйлдэл
    # ------------------------------------------------------------

    def on_start(self):
        """Санах ойг эхлүүлэх эсвэл reset хийх."""
        try:
            size = int(self.size_entry.get())
            self.allocator = Allocator(size)
        except ValueError:
            messagebox.showerror("Алдаа", "Санах ойн хэмжээ 0-ээс их бүхэл тоо байх ёстой")
            return
        self.show_message("Санах ой " + str(size) + " byte-аар эхэллээ", True)
        self.refresh()

    def on_request(self):
        """RQ товч дарахад: оролтыг уншиж, allocator.request() дуудаад зургийг шинэчилнэ."""
        if not self.check_started():
            return
        name = self.rq_name_entry.get().strip()
        try:
            size = int(self.rq_size_entry.get())
        except ValueError:
            self.show_message("Алдаа: хэмжээ бүхэл тоо байх ёстой", False)
            return
        strategy = self.strategy_var.get()
        ok, message = self.allocator.request(name, size, strategy)
        self.show_message(message, ok)
        self.refresh()
        if ok:
            self.rq_name_entry.delete(0, tk.END)      # дараагийн хүсэлтэд бэлдэнэ
            self.rq_size_entry.delete(0, tk.END)
            self.rq_name_entry.focus_set()

    def on_release(self):
        """RL товч дарахад: allocator.release() дуудна."""
        if not self.check_started():
            return
        name = self.rl_name_entry.get().strip()
        if name == "":
            self.show_message("Алдаа: процессын нэр хоосон байна", False)
            return
        ok, message = self.allocator.release(name)
        self.show_message(message, ok)
        self.refresh()
        if ok:
            self.rl_name_entry.delete(0, tk.END)

    def on_compact(self):
        """C товч дарахад: allocator.compact() дуудна."""
        if not self.check_started():
            return
        ok, message = self.allocator.compact()
        self.show_message(message, ok)
        self.refresh()

    def refresh(self):
        """Зураг болон статистикийг шинэчилнэ. Allocator-ийн ямар ч өөрчлөлтийн дараа дуудна."""
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


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
