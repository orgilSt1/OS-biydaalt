```python
"""
gui_canvas.py - Basic memory layout visualization.
"""

HOLE_COLOR = "#e0e0e0"
PROCESS_COLORS = [
    "#e6194b", "#3cb44b", "#4363d8", "#f58231",
    "#911eb4", "#42d4f4", "#f032e6", "#469990"
]

MARGIN = 20
BAR_TOP = 40
BAR_BOTTOM = 100

_color_of = {}


def color_for(name):
    """Assign a consistent color to each process."""
    if name not in _color_of:
        _color_of[name] = PROCESS_COLORS[len(_color_of) % len(PROCESS_COLORS)]
    return _color_of[name]


def draw_memory(canvas, blocks, max_size):
    """Draw memory blocks on a Tkinter Canvas."""
    canvas.delete("all")

    width = canvas.winfo_width()
    if width < 100:
        width = 800

    usable = width - 2 * MARGIN

    canvas.create_text(
        MARGIN, 15,
        text=f"Memory Layout | Total: {max_size} bytes",
        anchor="w",
        font=("Helvetica", 10, "bold")
    )

    for block in blocks:
        x1 = MARGIN + block.start * usable / max_size
        x2 = MARGIN + (block.start + block.size) * usable / max_size

        if block.is_hole():
            color = HOLE_COLOR
            label = "HOLE"
        else:
            color = color_for(block.owner)
            label = block.owner

        canvas.create_rectangle(
            x1, BAR_TOP, max(x2, x1 + 1), BAR_BOTTOM,
            fill=color,
            outline="black"
        )

        if x2 - x1 >= 35:
            canvas.create_text(
                (x1 + x2) / 2,
                (BAR_TOP + BAR_BOTTOM) / 2,
                text=f"{label}\n{block.size}",
                font=("Arial", 9)
            )
```
