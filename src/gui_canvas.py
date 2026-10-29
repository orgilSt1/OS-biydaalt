"""
gui_canvas.py - Memory layout-ийг ЗУРАХ хэсэг
 
Энэ файл зөвхөн ЗУРАХ ажил хийнэ. Товчлуур, оролтын талбар энд байхгүй (gui.py).
 
gui.py энэ функцийг ингэж дуудна:
    draw_memory(canvas, allocator.get_blocks(), allocator.max_size)
 
Зураг:
  - Дээд талд гарчиг: нийт хэмжээ (byte), hole-ын тоо, гадаад fragmentation
  - Дунд нь санах ойн мөр: процесс бүр өөр өнгөтэй, hole саарал
  - Доор нь эхлэх хаягууд (оролцуулсан хаяг)
  - Хамгийн доор legend (өнгөний тайлбар)
Хэрэв hole нэгээс олон (fragmentation) бол hole-уудын хүрээ улаан зураасаар зурагдана.
"""
 
HOLE_COLOR = "#e0e0e0"          # hole-ын өнгө (цайвар саарал)
HOLE_OUTLINE = "#555555"        # hole-ын хүрээ
FRAGMENT_OUTLINE = "#c0392b"    # hole нэгээс олон үед (fragmentation) хүрээ
PROCESS_COLORS = ["#e6194b", "#3cb44b", "#4363d8", "#f58231", "#911eb4",
                  "#42d4f4", "#f032e6", "#bfef45", "#fabed4", "#469990",
                  "#dcbeff", "#9a6324"]
MARGIN = 20                     # зургийн захын зай
BAR_TOP = 40                    # санах ойн мөрийн дээд ирмэг
BAR_BOTTOM = 100                # санах ойн мөрийн доод ирмэг
LEGEND_ITEM_WIDTH = 175         # legend-ийн нэг зүйлийн өргөн
LEGEND_ROW_HEIGHT = 22
 
# Процесс бүрт өнгийг ЭХЛЭЭД харагдсан дарааллаар нь өгч, хадгална.
# Ингэснээр өөр процесс чөлөөлөгдөхөд бусдын өнгө солигдохгүй.
_color_of = {}
 
 
def reset_colors():
    """Өнгөний бүртгэлийг цэвэрлэнэ (Reset хийхэд дуудаж болно)."""
    _color_of.clear()
 
 
def color_for(name):
    """Процессын нэрэнд тогтвортой өнгө өгнө. 12-оос олон процесст өнгө давтагдана."""
    if name not in _color_of:
        _color_of[name] = PROCESS_COLORS[len(_color_of) % len(PROCESS_COLORS)]
    return _color_of[name]
 
 
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
 
 
def draw_legend(canvas, items, x0, y0, width):
    """Өнгөний тайлбарыг зурна. items = [(өнгө, текст, хүрээний өнгө), ...]
    Мөр дүүрвэл дараагийн мөр рүү шилжинэ. Ашигласан өндрийг буцаана."""
    per_row = max(1, int(width // LEGEND_ITEM_WIDTH))
    for i in range(len(items)):
        color, text, outline = items[i]
        row = i // per_row
        col = i % per_row
        x = x0 + col * LEGEND_ITEM_WIDTH
        y = y0 + row * LEGEND_ROW_HEIGHT
        canvas.create_rectangle(x, y, x + 14, y + 14, fill=color, outline=outline)
        canvas.create_text(x + 20, y + 7, text=text, anchor="w")
    rows = (len(items) + per_row - 1) // per_row
    return rows * LEGEND_ROW_HEIGHT
 
 
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
 
    # --- Гарчиг ---
    title = ("Memory layout   Нийт: " + str(max_size) + " byte   Hole: " + str(hole_count)
             + "   Гадаад fragmentation: " + format(percent, ".1f") + "%")
    canvas.create_text(MARGIN, 15, text=title, anchor="w", font=("Helvetica", 10, "bold"))
 
    # --- Санах ойн мөр ---
    label_end_x = -1000                       # сүүлийн хаягийн бичгийн баруун захын x
    process_names = []
    for block in blocks:
        x1 = MARGIN + block.start * usable / max_size
        x2 = MARGIN + (block.start + block.size) * usable / max_size
        if x2 < x1 + 1:
            x2 = x1 + 1                       # хэт жижиг блок ч харагдана
 
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
            if block.owner not in process_names:
                process_names.append(block.owner)
 
        # Блок доторх бичиг: өргөнөөс хамаарч
        block_width = x2 - x1
        middle_y = (BAR_TOP + BAR_BOTTOM) / 2
        if block_width >= 60:
            canvas.create_text((x1 + x2) / 2, middle_y, text=label + "\n" + str(block.size))
        elif block_width >= 28:
            canvas.create_text((x1 + x2) / 2, middle_y, text=label)
 
        # Эхлэх хаяг: өмнөх бичигтэй давхцахгүй бол
        if x1 - 4 >= label_end_x:
            text = str(block.start)
            canvas.create_text(x1, BAR_BOTTOM + 6, text=text, anchor="nw")
            label_end_x = x1 + 7 * len(text) + 8
 
    # Хамгийн сүүлийн хаяг (оролцуулсан) баруун талд
    last_text = str(max_size - 1)
    last_x = MARGIN + usable
    if last_x - 7 * len(last_text) >= label_end_x:
        canvas.create_text(last_x, BAR_BOTTOM + 6, text=last_text, anchor="ne")
 
    # --- Legend ---
    items = []
    if fragmented:
        items.append((HOLE_COLOR, "hole (хуваагдсан)", FRAGMENT_OUTLINE))
    else:
        items.append((HOLE_COLOR, "hole (чөлөөт)", HOLE_OUTLINE))
    for name in process_names:
        items.append((color_for(name), name, "black"))
    legend_y = BAR_BOTTOM + 32
    used = draw_legend(canvas, items, MARGIN, legend_y, usable)
 
    # Legend олон мөр болбол зургийн өндрийг өсгөнө
    needed = legend_y + used + 10
    if needed < 150:
        needed = 150
    canvas.config(height=needed)
 
 

# """
# gui_canvas.py - Memory layout-ийг ЗУРАХ хэсэг (Гишүүн 3-ын ажил)

# Энэ файл зөвхөн ЗУРАХ ажил хийнэ. Товчлуур, оролтын талбар энд байхгүй
# (тэдгээр нь gui.py буюу Гишүүн 4-ийн ажил).

# Гишүүн 4 энэ файлын draw_memory() функцийг ингэж дуудна:
#     draw_memory(canvas, allocator.get_blocks(), allocator.max_size)
# Тиймээс функцийн НЭР, АРГУМЕНТЫГ ӨӨРЧЛӨХГҮЙ байх. Дотор нь хүссэнээрээ сайжруулна.

# Одоо байгаа нь хамгийн энгийн ажилладаг хувилбар. Үүнийг сайжруулна (доорх TODO).
# """

# HOLE_COLOR = "#d9d9d9"          # hole-ын өнгө (саарал)
# PROCESS_COLORS = ["#e6194b", "#3cb44b", "#4363d8", "#f58231", "#911eb4",
#                   "#42d4f4", "#f032e6", "#bfef45", "#fabed4", "#469990"]
# MARGIN = 20                      # зургийн захын зай


# def color_for(name):
#     """Процессын нэрээр өнгө сонгоно."""
#     total = 0
#     for ch in name:
#         total = total + ord(ch)
#     return PROCESS_COLORS[total % len(PROCESS_COLORS)]


# def draw_memory(canvas, blocks, max_size):
#     """Санах ойг тэгш өнцөгт мөр хэлбэрээр зурна.
#     canvas   : tkinter Canvas
#     blocks   : allocator.get_blocks()-ийн үр дүн (Block-уудын жагсаалт)
#     max_size : нийт санах ойн хэмжээ
#     """
#     canvas.delete("all")                      # өмнөх зургийг арилгана
#     width = canvas.winfo_width()
#     if width < 100:
#         width = 800                           # цонх хараахан зурагдаагүй үед
#     usable = width - 2 * MARGIN
#     top = 40
#     bottom = 110

#     for block in blocks:
#         x1 = MARGIN + block.start * usable / max_size
#         x2 = MARGIN + (block.start + block.size) * usable / max_size
#         if block.is_hole():
#             color = HOLE_COLOR
#             label = "hole"
#         else:
#             color = color_for(block.owner)
#             label = block.owner
#         canvas.create_rectangle(x1, top, x2, bottom, fill=color, outline="black")
#         if x2 - x1 > 40:                      # хангалттай өргөн бол нэр бичнэ
#             canvas.create_text((x1 + x2) / 2, (top + bottom) / 2,
#                                text=label + "\n" + str(block.size))

#     # TODO 1: блок бүрийн эхлэх хаягийг доор нь бичих (0, 200, 500 ...)
#     # TODO 2: draw_legend() функц бичиж дуудах (өнгөний тайлбар: процесс, hole)
#     # TODO 3: нарийхан блокийн нэр дээр багтахгүй бол жижиг бичих эсвэл алгасах
#     # TODO 4: өнгө давхцахгүйгээр өөр өөр процесст өөр өнгө өгөх (color_for-г сайжруулах)
#     # TODO 5: fragmentation-ийг харуулах (жишээ нь hole-уудыг хээтэй/хүрээтэй зурах)
#     # TODO 6: нэгжийг (byte, KB гэх мэт) зургийн гарчигт бичих
