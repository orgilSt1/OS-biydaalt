"""
allocator.py - Санах ой хуваарилагчийн СУУРЬ (цөм)

Энэ файл бол төслийн хамгийн чухал хэсэг. Санах ой хуваарилах бүх логик
(request, release, compact) зөвхөн ЭНД байна.

АНХААР: энэ файлд print() эсвэл input() БАЙХГҮЙ. Зөвхөн тооцоолоод үр дүнг
буцаана. Хэвлэх, зурах ажлыг cli.py болон gui.py хийнэ.

Санах ойг БЛОКУУДЫН ЖАГСААЛТААР төлөөлнө. Блок бүр нь:
  - start : эхлэх хаяг
  - size  : хэмжээ
  - owner : процессын нэр (жишээ "P1"). Хоосон хэсэг (hole) бол None

Жишээ (1000 нэгж санах ой):
  [Block(0, 200, "P1"), Block(200, 300, None), Block(500, 500, "P2")]
   => 0-199 нь P1, 200-499 хоосон, 500-999 нь P2
"""

# Зөвшөөрөгдсөн стратегиуд: F = First-fit, B = Best-fit, W = Worst-fit
STRATEGIES = ("F", "B", "W")


class Block:
    """Санах ойн нэг хэсэг (процесс эсвэл хоосон hole)."""

    def __init__(self, start, size, owner=None):
        self.start = start    # эхлэх хаяг
        self.size = size      # хэмжээ
        self.owner = owner    # процессын нэр, hole бол None

    def end(self):
        """Сүүлийн хаяг (оролцуулсан). Жишээ: start=0, size=200 -> 199"""
        return self.start + self.size - 1

    def is_hole(self):
        """Хоосон хэсэг мөн эсэх."""
        return self.owner is None

    def copy(self):
        """Хуулбар үүсгэнэ (гаднаас блокийг эвдэхээс сэргийлнэ)."""
        return Block(self.start, self.size, self.owner)


class Allocator:
    """Санах ой хуваарилагч."""

    def __init__(self, max_size):
        """max_size хэмжээтэй санах ой үүсгэнэ. Эхэндээ бүтэн нэг hole."""
        if not isinstance(max_size, int) or max_size <= 0:
            raise ValueError("Санах ойн хэмжээ 0-ээс их бүхэл тоо байх ёстой")
        self.max_size = max_size
        self.blocks = [Block(0, max_size, None)]

    # ------------------------------------------------------------
    # ГАДНААС ДУУДАХ ҮНДСЭН ФУНКЦҮҮД
    # Бүгд (амжилттай эсэх, мессеж) буцаана. Жишээ: (True, "...")
    # ------------------------------------------------------------

    def request(self, name, size, strategy):
        """name процесст size хэмжээтэй санах ой олгоно.
        strategy: "F" (first), "B" (best), "W" (worst)"""
        # 1. Оролтыг шалгах
        if name is None or str(name).strip() == "":
            return False, "Алдаа: процессын нэр хоосон байна"
        if any(ch.isspace() for ch in str(name)):
            return False, "Алдаа: процессын нэрэнд зай байж болохгүй"
        if not isinstance(size, int) or size <= 0:
            return False, "Алдаа: хэмжээ 0-ээс их бүхэл тоо байх ёстой"
        strategy = str(strategy).upper()
        if strategy not in STRATEGIES:
            return False, "Алдаа: стратеги F, B, W-ийн аль нэг байх ёстой"
        if self.find_process(name) is not None:
            return False, "Алдаа: " + str(name) + " процесс аль хэдийн санах ой эзэлсэн байна"

        # 2. Тохирох hole сонгох
        index = self._choose_hole(size, strategy)
        if index == -1:
            free = self.total_free()
            if free >= size:
                return False, ("Алдаа: нийт чөлөөт зай " + str(free) + " байгаа ч нэг hole дотор "
                               "багтахгүй байна (fragmentation). Compaction (C) хийж үзнэ үү")
            return False, "Алдаа: санах ой хүрэлцэхгүй (чөлөөт " + str(free) + ", хүссэн " + str(size) + ")"

        # 3. Hole-ыг хуваана
        hole = self.blocks[index]
        if hole.size == size:
            # яг тэнцүү: hole бүхлээрээ процессынх болно
            hole.owner = name
        else:
            # үлдэх хэсэг нь шинэ hole болно
            rest = Block(hole.start + size, hole.size - size, None)
            hole.size = size
            hole.owner = name
            self.blocks.insert(index + 1, rest)
        return True, name + "-д [" + str(hole.start) + ":" + str(hole.end()) + "] олгов"

    def release(self, name):
        """name процессын санах ойг чөлөөлнө, зэргэлдээ hole-уудыг нэгтгэнэ."""
        index = self.find_process(name)
        if index is None:
            return False, "Алдаа: " + str(name) + " нэртэй процесс олдсонгүй"
        block = self.blocks[index]
        freed = block.size
        block.owner = None
        self._merge_holes()
        return True, str(name) + "-ийн санах ойг чөлөөллөө (" + str(freed) + " нэгж)"

    def compact(self):
        """Бүх процессыг эхлэл рүү шахаж, hole-уудыг төгсгөлд нэг болгоно."""
        hole_count = self.get_stats()["hole_count"]
        if hole_count == 0:
            return True, "Compaction хэрэггүй: чөлөөт hole алга"
        if hole_count == 1 and self.blocks[-1].is_hole():
            return True, "Compaction хэрэггүй: чөлөөт зай аль хэдийн нэг хэсэг байна"

        # процессуудыг дарааллаар нь авч, эхлэх хаягийг шинэчилнэ
        processes = []
        for block in self.blocks:
            if not block.is_hole():
                processes.append(block)
        position = 0
        for block in processes:
            block.start = position
            position = position + block.size

        # үлдсэн бүх зай нь нэг hole
        if position < self.max_size:
            processes.append(Block(position, self.max_size - position, None))
        self.blocks = processes
        return True, ("Compaction хийгдлээ: " + str(hole_count) + " hole нэг болов, "
                      "чөлөөт зай " + str(self.max_size - position))

    def reset(self, max_size=None):
        """Санах ойг эхний байдалд оруулна (GUI-ийн Reset товчинд).
        max_size өгвөл шинэ хэмжээтэй болгоно."""
        if max_size is None:
            max_size = self.max_size
        if not isinstance(max_size, int) or max_size <= 0:
            raise ValueError("Санах ойн хэмжээ 0-ээс их бүхэл тоо байх ёстой")
        self.max_size = max_size
        self.blocks = [Block(0, max_size, None)]

    # ------------------------------------------------------------
    # МЭДЭЭЛЭЛ АВАХ ФУНКЦҮҮД (cli.py, gui.py эдгээрийг ашиглана)
    # ------------------------------------------------------------

    def get_blocks(self):
        """Бүх блокийн ХУУЛБАРЫГ хаягаар нь эрэмбэлж буцаана."""
        result = []
        for block in self.blocks:
            result.append(block.copy())
        return result

    def get_stats(self):
        """Статистикийг dictionary-ээр буцаана:
        total, used, free, hole_count, process_count, largest_hole,
        external_fragmentation (хувь, 0-100)"""
        free = 0
        hole_count = 0
        largest = 0
        process_count = 0
        for block in self.blocks:
            if block.is_hole():
                free = free + block.size
                hole_count = hole_count + 1
                if block.size > largest:
                    largest = block.size
            else:
                process_count = process_count + 1
        # Гадаад fragmentation: чөлөөт зайн хэдэн хувь нь хамгийн том hole-д ороогүй вэ
        if free > 0:
            fragmentation = (free - largest) * 100.0 / free
        else:
            fragmentation = 0.0
        return {
            "total": self.max_size,
            "used": self.max_size - free,
            "free": free,
            "hole_count": hole_count,
            "process_count": process_count,
            "largest_hole": largest,
            "external_fragmentation": fragmentation,
        }

    def total_free(self):
        """Нийт чөлөөт зай."""
        return self.get_stats()["free"]

    def find_process(self, name):
        """name процессын блокийн индексийг буцаана. Олдохгүй бол None."""
        for i in range(len(self.blocks)):
            if self.blocks[i].owner == name:
                return i
        return None

    # ------------------------------------------------------------
    # ДОТООД ТУСЛАХ ФУНКЦҮҮД (гаднаас дуудахгүй)
    # ------------------------------------------------------------

    def _choose_hole(self, size, strategy):
        """Стратегийн дагуу тохирох hole-ын индексийг буцаана. Байхгүй бол -1."""
        chosen = -1
        for i in range(len(self.blocks)):
            block = self.blocks[i]
            # hole биш эсвэл жижиг бол алгасна
            if (not block.is_hole()) or block.size < size:
                continue
            if strategy == "F":
                return i                      # First-fit: анхных нь болно
            if chosen == -1:
                chosen = i                    # B, W: эхний тохирохыг санана
            elif strategy == "B" and block.size < self.blocks[chosen].size:
                chosen = i                    # Best-fit: хамгийн жижиг нь
            elif strategy == "W" and block.size > self.blocks[chosen].size:
                chosen = i                    # Worst-fit: хамгийн том нь
        return chosen

    def _merge_holes(self):
        """Зэргэлдээ орших hole-уудыг нэг болгоно."""
        i = 0
        while i < len(self.blocks) - 1:
            current = self.blocks[i]
            following = self.blocks[i + 1]
            if current.is_hole() and following.is_hole():
                current.size = current.size + following.size
                del self.blocks[i + 1]        # i-г нэмэхгүй, дахин шалгана
            else:
                i = i + 1
