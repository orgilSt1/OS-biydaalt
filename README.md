# V-1-14: Contiguous Memory Allocation

F.CSM302 Үйлдлийн систем, Бие даалт 1. Хуваарилалтын код: **V-1-14**.

## Зорилго

Operating System Concepts (10th ed., 2018), 9-р бүлгийн Programming Project болох **Contiguous Memory Allocation**-ийг хэрэгжүүлсэн.
MAX хэмжээтэй тасралтгүй санах ойн мужид (хаяг 0…MAX−1) процессуудад **First-fit (F)**, **Best-fit (B)**, **Worst-fit (W)** стратегиар хэсэг олгох,
чөлөөлөх, hole-уудыг шахах (compaction) болон байдлыг тайлагнах загварчлалын програм. Санах ой бодит биш, тоогоор бодогдоно.
Хоёр интерфейстэй: **CLI** (`allocator>` prompt) ба **GUI** (tkinter, **Memory layout** зурагтай). Хоёулаа нэг `allocator.py`-г ашиглана.

## Quick Start

Шаардлага: Python 3.10 эсвэл түүнээс дээш. Нэмэлт сан хэрэггүй (зөвхөн стандарт сан).
Windows-ийн Python суулгагч tkinter-ийг агуулдаг. Linux (Debian/Ubuntu) дээр GUI ажиллахгүй бол: `sudo apt install python3-tk`

```bash
git clone https://github.com/orgilSt1/OS-biydaalt.git
cd OS-biydaalt

# CLI (1000 нь санах ойн хэмжээ, byte)
python src/cli.py 1000                       # Linux: python3 src/cli.py 1000

# CLI, командыг файлаас уншуулах (Windows cmd)
python src\cli.py 1000 < examples\example1.txt
#   Linux: python3 src/cli.py 1000 < examples/example1.txt

# GUI
python src/gui.py                            # Linux: python3 src/gui.py

# Бүх автомат тест (төслийн үндсэн фолдероос)
python -m unittest discover tests            # Linux: python3 -m unittest discover tests
                                             # хүлээгдэх: Ran 39 tests ... OK
```

## Командууд

| Команд | Үүрэг |
|---|---|
| `RQ <нэр> <хэмжээ> <F\|B\|W>` | Санах ой хүсэх (нэрэнд зай байхгүй, хэмжээ 0-ээс их бүхэл тоо) |
| `RL <нэр>` | Санах ой чөлөөлөх, зэргэлдээ hole нэгдэнэ |
| `C` | Compaction: процессуудыг эхлэл рүү шахаж hole-уудыг нэг болгоно |
| `STAT` | Хуваарилагдсан ба чөлөөт мужийг харуулах |
| `X` | Гарах |

Хэмжээ, хаяг бүгд **byte**-аар. Хаяг оролцуулсан (inclusive): 200 byte-ийн блок 0-ээс эхэлбэл `[0:199]`.
Команд том/жижиг үсгээр ялгагдахгүй, процессын нэр ялгагдана.

Жишээ:

```
allocator> RQ P0 40000 W
P0-д [0:39999] олгов
allocator> STAT
Addresses [0:39999] Process P0
Addresses [40000:1048575] Unused
```

## Memory layout дүрслэл (GUI)

Блок бүрийн өргөн хэмжээтэй пропорциональ. Өнгөт блок = процесс (нэр, хэмжээ), саарал = hole.
Hole-уудын **улаан тасархай** хүрээ = нэгээс олон hole (гадаад fragmentation), **саарал тасархай** хүрээ = нэг тасралтгүй чөлөөт зай.
Блокийн доор эхлэх хаяг, гарчигт нийт хэмжээ, hole-ын тоо, fragmentation (%) гарна. Доор нь legend байна.

## Бүтэц

| Зам | Агуулга |
|---|---|
| `src/allocator.py` | Бүх логик: `Block`, `Allocator` (request, release, compact, get_stats). `print`/`input` байхгүй |
| `src/cli.py` | Командын мөрийн интерфейс |
| `src/gui.py`, `src/gui_canvas.py` | Цонх, товчлуур ба Memory layout зурах хэсэг |
| `tests/` | `test_allocator.py` (23), `test_cli.py` (16) |
| `examples/` | `example1…4.txt` ба `.expected.txt` хос; тайлбар `examples/README.md` |
| `docs/` | `V-1-14_Manual.pdf`, `V-1-14_BD1_Report.pdf` |

## Туршилт

- **Автомат тест:** 39 тест, бүгд давсан (Ubuntu 24.04, Python 3.12.3). Windows 11 + Python 3.11 дээр мэдэгдэхүйц алдаа гараагүй.
- **Жишээ файл:** гаралтыг `.expected.txt`-тэй харьцуулна: `python src\cli.py 1000 < examples\example1.txt > out.txt` ба `fc out.txt examples\example1.expected.txt` (Linux: `python3 src/cli.py ...` ба `diff`).
- **Номын жишээ:** 550 + 375 + 1900 + 4500 KB-ийн дөрвөн hole compaction-ий дараа нэг 7325 KB hole болдог (`test_book_compaction_example`).
- Дэлгэрэнгүй: `docs/V-1-14_BD1_Report.pdf`. Алхам алхмаар заавар: `docs/V-1-14_Manual.pdf`.

## Мэдэгдэж буй хязгаарлалт

- 1–2 byte-ийн хэт жижиг блок GUI-ийн зурагт харагддаггүй (тоон статистик ба STAT-д зөв).
- GUI-д командын түүх, undo байхгүй.
- Хүрэлцэхгүй хүсэлтийг хүлээлгийн дараалалд тавихгүй, татгалзана (номын шаардлагын дагуу).

## Баг

| № | Оюутны код | Нэр |
|---|---|---|
| 1 | B241910016 | Я.Мөнх-Оргил |
| 2 | B232290038 | Н.Гантогтох |
| 3 | B222270065 | Э.Эрдэнэбат |
| 4 | B241910045 | Б.Баасандорж |
| 5 | B242270080 | Э.Халиунаа |

## AI болон бэлэн материалын ашиглалт

- Суурь код, тестийн араг ясыг (src/, tests/) болон Report, Manual, README-ийн эх бичвэрийг Claude (Anthropic)-ийн тусламжтай бэлтгэж, гишүүд ажиллуулж, шалгаж, шаардлагатай хэсгийг засварласан
- Гадны сан ашиглаагүй (зөвхөн Python стандарт сан).

## Release

Хувилбар v1.0: https://github.com/orgilSt1/OS-biydaalt/releases/tag/v1.0
