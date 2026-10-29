"""
cli.py - Командын мөрийн интерфейс
 
Ажиллуулах:
    python src/cli.py 1048576        (Windows)
    python3 src/cli.py 1048576       (Linux)
 
Дараа нь   allocator>   гэсэн prompt гарч, дараах командуудыг хүлээн авна:
    RQ P0 40000 W    санах ой хүсэх (F / B / W)
    RL P0            санах ой чөлөөлөх
    C                compaction
    STAT             байдлыг харуулах
    X                гарах
 
Командыг файлаас уншуулж болно:
    python src/cli.py 1000 < examples/example1.txt
"""
import sys
from allocator import Allocator
 
PROMPT = "allocator> "
COMMANDS_HELP = "Боломжит командууд: RQ <нэр> <хэмжээ> <F|B|W>, RL <нэр>, C, STAT, X"
 
 
def format_status(allocator):
    """STAT командын гаралтыг нэг текст болгож буцаана (print хийхгүй).
 
    Номын формат:
        Addresses [0:199] Process P1
        Addresses [200:999] Unused
    Хаяг нь ОРОЛЦУУЛСАН (inclusive): эхлэх хаяг ба сүүлийн хаяг.
    """
    lines = []
    for block in allocator.get_blocks():
        if block.is_hole():
            who = "Unused"
        else:
            who = "Process " + block.owner
        lines.append("Addresses [" + str(block.start) + ":" + str(block.end()) + "] " + who)
    return "\n".join(lines)
 
 
def handle_command(allocator, line):
    """Нэг мөр командыг боловсруулна.
    Буцаах утга:  (хэвлэх текст, гарах эсэх)
    """
    parts = line.split()
    if len(parts) == 0:
        return "", False                      # хоосон мөр: юу ч хийхгүй
 
    command = parts[0].upper()
 
    if command == "RQ":
        if len(parts) != 4:
            return "Хэрэглээ: RQ <нэр> <хэмжээ> <F|B|W>", False
        try:
            size = int(parts[2])
        except ValueError:
            return "Алдаа: хэмжээ бүхэл тоо байх ёстой (оруулсан: " + parts[2] + ")", False
        ok, message = allocator.request(parts[1], size, parts[3])
        return message, False
 
    if command == "RL":
        if len(parts) != 2:
            return "Хэрэглээ: RL <нэр>", False
        ok, message = allocator.release(parts[1])
        return message, False
 
    if command == "C":
        if len(parts) != 1:
            return "Хэрэглээ: C", False
        ok, message = allocator.compact()
        return message, False
 
    if command == "STAT":
        if len(parts) != 1:
            return "Хэрэглээ: STAT", False
        return format_status(allocator), False
 
    if command == "X":
        if len(parts) != 1:
            return "Хэрэглээ: X", False
        return "", True
 
    return "Алдаа: үл мэдэгдэх команд '" + parts[0] + "'. " + COMMANDS_HELP, False
 
 
def setup_utf8():
    """Монгол үсэг Windows дээр зөв хэвлэгдэхийн тулд UTF-8 болгоно."""
    for stream in (sys.stdout, sys.stdin):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
 
 
def main():
    """Программын эхлэл."""
    setup_utf8()
 
    # 1. Аргументыг шалгах
    if len(sys.argv) != 2:
        print("Хэрэглээ: python src/cli.py <санах ойн хэмжээ (byte)>")
        return
    try:
        max_size = int(sys.argv[1])
        allocator = Allocator(max_size)
    except ValueError:
        print("Алдаа: санах ойн хэмжээ 0-ээс их бүхэл тоо байх ёстой")
        return
 
    # 2. Командыг давтан уншина
    interactive = sys.stdin.isatty()
    while True:
        try:
            line = input(PROMPT)
        except EOFError:
            break          # файлаас уншиж дууссан үед
        if not interactive:
            print(line)    # файлаас уншиж байвал командыг давтаж харуулна (гаралт ойлгомжтой болно)
        text, should_exit = handle_command(allocator, line)
        if text != "":
            print(text)
        if should_exit:
            break
 
 
if __name__ == "__main__":
    main()
 

