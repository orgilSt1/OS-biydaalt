"""
gui_canvas.py - Memory layout-ийг ЗУРАХ хэсэг

Энэ файл зөвхөн ЗУРАХ ажил хийнэ. Товчлуур, оролтын талбар энд байхгүй (gui.py).

gui.py энэ функцийг ингэж дуудна:
    draw_memory(canvas, allocator.get_blocks(), allocator.max_size)

Зураг:
  - Дээд талд гарчиг: нийт хэмжээ (byte), hole-ын тоо, гадаад fragmentation
  - Дунд нь санах ойн мөр: процесс бүр өөр өнгөтэй, hole саарал. Өргөн нь хэмжээтэй пропорциональ
  - Хэт нарийхан (MIN_BLOCK_PX-ээс бага) блокийг тодруулж, дээр нь нэрийг нь бичнэ (БД2-т нэмсэн)
  - Доор нь эхлэх хаягууд (оролцуулсан хаяг)
  - Хамгийн доор legend: процесс бүрийн нэр, [эхлэх:төгсгөл] хаяг, хэмжээ
Хэрэв hole нэгээс олон (fragmentation) бол hole-уудын хүрээ улаан зураасаар зурагдана.
"""

HOLE_COLOR = "#e0e0e0"          # hole-ын өнгө (цайвар саарал)
HOLE_OUTLINE = "#555555"        # hole-ын хүрээ
FRAGMENT_OUTLINE = "#c0392b"    # hole нэгээс олон үед (fragmentation) хүрээ
PROCESS_COLORS = ["#e6194b", "#3cb44b", "#4363d8", "#f58231", "#911eb4",
                  "#42d4f4", "#f032e6", "#bfef45", "#fabed4", "#469990",
                  "#dcbeff", "#9a6324"]
MARGIN = 20                     # зургийн захын зай
CALLOUT_ROW_1 = 50              # нарийхан блокийн нэрийн эхний мөр (y)
CALLOUT_ROW_2 = 38              # хоёр дахь мөр (эхнийхтэй давхцвал)
BAR_TOP = 60                    # санах ойн мөрийн дээд ирмэг
BAR_BOTTOM = 120                # санах ойн мөрийн доод ирмэг
MIN_BLOCK_PX = 8                # үүнээс нарийхан блокийг тодруулж зурна
CHAR_PX = 7                     # нэг тэмдэгтийн ойролцоо өргөн (бичгийн багтаамж тооцоход)
LEGEND_ITEM_WIDTH = 175         # legend-ийн нэг зүйлийн хамгийн бага өргөн
LEGEND_ROW_HEIGHT = 22

# Процесс бүрт өнгийг ЭХЛЭЭД харагдсан дарааллаар нь өгч, хадгална.
# Ингэснээр өөр процесс чөлөөлөгдөхөд бусдын өнгө солигдохгүй.
_color_of = {}


def reset_colors():
    """Өнгөний бүртгэлийг цэвэрлэнэ (Reset хийхэд дуудна)."""
    _color_of.clear()


def color_for(name):
    """Процессын нэрэнд тогтвортой өнгө өгнө.
    Шинэ нэрэнд одоо ашиглагдаагүй эхний өнгийг өгнө. 12-оос олон ХАМТ байгаа процесст өнгө давтагдана."""
    if name not in _color_of:
        used = set(_color_of.values())
        chosen = None
        for color in PROCESS_COLORS:
            if color not in used:
                chosen = color
                break
        if chosen is None:
            chosen = PROCESS_COLORS[len(_color_of) % len(PROCESS_COLORS)]
        _color_of[name] = chosen
    return _color_of[name]


def _sync_colors(live_names):
    """Чөлөөлөгдсөн процессын өнгийг чөлөөлнө. Ингэснээр 12-оос олон нэр ХУГАЦААНД
    ашиглагдсан ч нэгэн зэрэг байгаа процессууд өөр өнгөтэй хэвээр байна."""
    for name in list(_color_of.keys()):
        if name not in live_names:
            del _color_of[name]


def _fragmentation_info(blocks):
    """Гарчигт хэрэгтэй тоонуудыг блокуудаас бодно: (hole-ын тоо, чөлөөт, хамгийн том hole, fragmentation %)"""
    hole_count = 0
    free = 0
    largest = 0
    for block in blocks:
        if block.is_hole():
            hole_count = hole_count + 1
            free = free + block.size
            if block.size > largest:
                largest = block.size
    if free > 0:
        percent = (free - largest) * 100.0 / free
    else:
        percent = 0.0
    return hole_count, free, largest, percent


def draw_legend(canvas, items, x0, y0, width, item_width=None):
    """Өнгөний тайлбарыг зурна. items = [(өнгө, текст, хүрээний өнгө), ...]
    Мөр дүүрвэл дараагийн мөр рүү шилжинэ. Ашигласан өндрийг буцаана.
    item_width өгөөгүй бол текстийн урт дээр тулгуурлан бодно."""
    if item_width is None:
        longest = 0
        for item in items:
            if len(item[1]) > longest:
                longest = len(item[1])
        item_width = max(LEGEND_ITEM_WIDTH, longest * CHAR_PX + 34)
    per_row = max(1, int(width // item_width))
    for i in range(len(items)):
        color, text, outline = items[i]
        row = i // per_row
        col = i % per_row
        x = x0 + col * item_width
        y = y0 + row * LEGEND_ROW_HEIGHT
        canvas.create_rectangle(x, y, x + 14, y + 14, fill=color, outline=outline)
        canvas.create_text(x + 20, y + 7, text=text, anchor="w")
    rows = (len(items) + per_row - 1) // per_row
    return rows * LEGEND_ROW_HEIGHT


def _draw_narrow_marker(canvas, block, x1, x2, usable, color, state):
    """MIN_BLOCK_PX-ээс нарийхан блокийг харагдахуйц болгож дахин зурна, дээр нь нэрийг нь бичнэ.
    Блокийн төвд тавина; өмнөх тэмдэгтэй давхцвал баруун тийш зайлуулна (бие биеэ халхлахгүй).
    state = [эхний мөрийн сүүлийн x, хоёр дахь мөрийн сүүлийн x, өмнөх тэмдэгтийн баруун ирмэг]"""
    center = (x1 + x2) / 2.0
    left = center - MIN_BLOCK_PX / 2.0
    if left < state[2] + 1:
        left = state[2] + 1                   # өмнөх тэмдэгтийн дээр тавихгүй
    if left < MARGIN:
        left = MARGIN
    if left + MIN_BLOCK_PX > MARGIN + usable:
        left = MARGIN + usable - MIN_BLOCK_PX
    right = left + MIN_BLOCK_PX
    state[2] = right
    if block.is_hole():
        canvas.create_rectangle(left, BAR_TOP, right, BAR_BOTTOM, fill=HOLE_COLOR,
                                outline=FRAGMENT_OUTLINE, width=2)
        label = "hole"
    else:
        canvas.create_rectangle(left, BAR_TOP, right, BAR_BOTTOM, fill=color,
                                outline="black", width=1)
        label = block.owner
    mid = (left + right) / 2.0
    half = (CHAR_PX * len(label) + 4) / 2.0
    # нэрийг давхцахгүй мөрөнд тавина; аль нь ч багтахгүй бол зөвхөн тэмдэг үлдэнэ
    for row_index, row_y in ((0, CALLOUT_ROW_1), (1, CALLOUT_ROW_2)):
        if mid - half >= state[row_index]:
            canvas.create_line(mid, row_y + 7, mid, BAR_TOP, fill="black")
            canvas.create_text(mid, row_y, text=label, anchor="s", font=("Helvetica", 8, "bold"))
            state[row_index] = mid + half
            return True
    canvas.create_line(mid, BAR_TOP - 6, mid, BAR_TOP, fill="black")
    return False


def draw_memory(canvas, blocks, max_size):
    """Санах ойг тэгш өнцөгт мөр хэлбэрээр зурна.
    canvas   : tkinter Canvas
    blocks   : allocator.get_blocks()-ийн үр дүн (Block-уудын жагсаалт)
    max_size : нийт санах ойн хэмжээ (byte)
    """
    canvas.delete("all")                      # өмнөх зургийг арилгана
    width = canvas.winfo_width()
    if width < 100:
        width = 800                           # цонх хараахан зурагдаагүй үед
    usable = width - 2 * MARGIN

    hole_count, free, largest, percent = _fragmentation_info(blocks)
    fragmented = hole_count > 1

    # Чөлөөлөгдсөн процессын өнгийг чөлөөлж, харагдаж буй процессуудад өнгө өгнө
    live = []
    for block in blocks:
        if not block.is_hole():
            live.append(block.owner)
    _sync_colors(live)
    for name in live:
        color_for(name)

    # --- Гарчиг ---
    title = ("Memory layout   Нийт: " + str(max_size) + " byte   Hole: " + str(hole_count)
             + "   Гадаад fragmentation: " + format(percent, ".1f") + "%")
    canvas.create_text(MARGIN, 15, text=title, anchor="w", font=("Helvetica", 10, "bold"))

    # --- Санах ойн мөр ---
    label_end_x = -1000                       # сүүлийн хаягийн бичгийн баруун захын x
    narrow = []                               # нарийхан блокууд: сүүлд нь тодруулж зурна
    for block in blocks:
        x1 = MARGIN + block.start * usable / max_size
        x2 = MARGIN + (block.start + block.size) * usable / max_size

        if block.is_hole():
            color = HOLE_COLOR
            if fragmented:
                canvas.create_rectangle(x1, BAR_TOP, x2, BAR_BOTTOM, fill=color,
                                        outline=FRAGMENT_OUTLINE, width=2, dash=(4, 2))
            else:
                canvas.create_rectangle(x1, BAR_TOP, x2, BAR_BOTTOM, fill=color,
                                        outline=HOLE_OUTLINE, dash=(4, 2))
            label = "hole"
        else:
            color = color_for(block.owner)
            canvas.create_rectangle(x1, BAR_TOP, x2, BAR_BOTTOM, fill=color, outline="black")
            label = block.owner

        # Блок доторх бичиг: өргөнөөс хамаарч
        block_width = x2 - x1
        middle_y = (BAR_TOP + BAR_BOTTOM) / 2
        if block_width >= 60:
            canvas.create_text((x1 + x2) / 2, middle_y, text=label + "\n" + str(block.size))
        elif block_width >= 28:
            canvas.create_text((x1 + x2) / 2, middle_y, text=label)
        elif block_width < MIN_BLOCK_PX:
            narrow.append((block, x1, x2, color))

        # Эхлэх хаяг: өмнөх бичигтэй давхцахгүй бол
        if x1 - 4 >= label_end_x:
            text = str(block.start)
            canvas.create_text(x1, BAR_BOTTOM + 6, text=text, anchor="nw")
            label_end_x = x1 + CHAR_PX * len(text) + 8

    # Хамгийн сүүлийн хаяг (оролцуулсан) баруун талд
    last_text = str(max_size - 1)
    last_x = MARGIN + usable
    if last_x - CHAR_PX * len(last_text) >= label_end_x:
        canvas.create_text(last_x, BAR_BOTTOM + 6, text=last_text, anchor="ne")

    # Нарийхан блокуудыг бусдын ДЭЭР тодруулж зурна (зүүнээс баруун тийш)
    marker_state = [-1000, -1000, -1000]
    for block, x1, x2, color in narrow:
        _draw_narrow_marker(canvas, block, x1, x2, usable, color, marker_state)

    # --- Legend ---
    items = []
    if fragmented:
        items.append((HOLE_COLOR, "hole (хуваагдсан)", FRAGMENT_OUTLINE))
    else:
        items.append((HOLE_COLOR, "hole (чөлөөт)", HOLE_OUTLINE))
    for block in blocks:
        if not block.is_hole():
            text = (block.owner + "  [" + str(block.start) + ":" + str(block.end()) + "]  "
                    + str(block.size) + " byte")
            items.append((color_for(block.owner), text, "black"))
    legend_y = BAR_BOTTOM + 32
    used = draw_legend(canvas, items, MARGIN, legend_y, usable)

    # Нарийхан блок байвал тайлбар нэмнэ
    note_height = 0
    if len(narrow) > 0:
        canvas.create_text(MARGIN, legend_y + used + 4, anchor="nw", fill="#555555",
                           text="Тайлбар: " + str(MIN_BLOCK_PX) + " px-ээс нарийхан блокийг "
                                "тодруулж, нэрийг нь дээр бичив (бодит хэмжээг legend-ээс харна уу)")
        note_height = 20

    # Legend олон мөр болбол зургийн өндрийг өсгөнө
    needed = legend_y + used + note_height + 10
    if needed < 170:
        needed = 170
    canvas.config(height=needed)
