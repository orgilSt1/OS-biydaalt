```python
"""
gui_canvas.py - Memory layout with addresses and process colors.
"""

HOLE_COLOR = "#e0e0e0"
HOLE_OUTLINE = "#555555"

PROCESS_COLORS = [
    "#e6194b", "#3cb44b", "#4363d8", "#f58231",
    "#911eb4", "#42d4f4", "#f032e6", "#469990",
    "#9a6324", "#fabed4", "#dcbeff", "#bfef45"
]

MARGIN = 20
BAR_TOP = 40
BAR_BOTTOM = 100

_color_of = {}


def reset_colors():
    """Clear the process color mapping."""
    _color_of.clear()


def color_for(name):
    """Assign a stable color to each process."""
    if name not in _color_of:
        _color_of[name] = PROCESS_COLORS[
            len(_color_of) % len(PROCESS_COLORS)
        ]
    return _color_of[name]


def draw_memory(canvas, blocks, max_size):
    """Draw memory blocks and their starting addresses."""
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

    last_label_end = -1000

    for block in blocks:
        x1 = MARGIN + block.start * usable / max_size
        x2 = MARGIN + (block.start + block.size) * usable / max_size
        x2 = max(x2, x1 + 1)

        if block.is_hole():
            color = HOLE_COLOR
            label = "HOLE"
            outline = HOLE_OUTLINE
        else:
            color = color_for(block.owner)
            label = block.owner
            outline = "black"

        canvas.create_rectangle(
            x1, BAR_TOP, x2, BAR_BOTTOM,
            fill=color,
            outline=outline
        )

        block_width = x2 - x1
        if block_width >= 55:
            canvas.create_text(
                (x1 + x2) / 2,
                (BAR_TOP + BAR_BOTTOM) / 2,
                text=f"{label}\n{block.size}"
            )
        elif block_width >= 30:
            canvas.create_text(
                (x1 + x2) / 2,
                (BAR_TOP + BAR_BOTTOM) / 2,
                text=label
            )

        address_text = str(block.start)
        if x1 - 4 >= last_label_end:
            canvas.create_text(
                x1, BAR_BOTTOM + 6,
                text=address_text,
                anchor="nw"
            )
            last_label_end = x1 + len(address_text) * 7 + 8

    # Display the final valid address.
    last_x = MARGIN + usable
    final_address = str(max_size - 1)

    if last_x - len(final_address) * 7 >= last_label_end:
        canvas.create_text(
            last_x, BAR_BOTTOM + 6,
            text=final_address,
            anchor="ne"
        )
```
