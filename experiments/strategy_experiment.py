"""
strategy_experiment.py - First/Best/Worst-fit стратегийг ИЖИЛ ажлын ачаалал дээр жинхэнэ allocator.py-аар
харьцуулж, гүйцэтгэлийг хэмжинэ. Үр дүн нь программаар гарсан тоо (гараар бичсэн биш) бөгөөд ижил seed-ээр
давтахад ижил гарна (хугацааны хэмжилтээс бусад нь).

Ажиллуулах (repo-ийн үндсэн фолдероос):
    python experiments/strategy_experiment.py              (Windows)
    python3 experiments/strategy_experiment.py             (Linux)
Үр дүнг experiments/results.csv ба experiments/results.md файлд бичнэ.
"""
import csv
import os
import random
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))
from allocator import Allocator

MEMORY = 100000          # санах ойн хэмжээ (byte)
STEPS = 2000             # нэг туршилтын хүсэлтийн тоо (алхам бүрт нэг хүсэлт)
SEEDS = 50               # давтан ажиллуулах seed-ийн тоо
MIN_SIZE, MAX_SIZE = 50, 2500      # хүсэлтийн хэмжээний муж (byte)
MIN_LIFE, MAX_LIFE = 10, 100       # процесс хэдэн алхмын дараа чөлөөлөгдөх вэ (алхмын тоо)


def make_trace(seed):
    """Стратегиас хамаарахгүй, бүх стратегид ИЖИЛ үйлдлийн дараалал үүсгэнэ.
    Алхам бүрт нэг процесс хүснэ; процесс бүр MIN_LIFE..MAX_LIFE алхмын дараа чөлөөлөгдөнө
    (ингэснээр санах ойн ачаалал тогтворжино, ойролцоогоор 55 процесс зэрэг амьд байна)."""
    rng = random.Random(seed)
    releases = {}                                 # алхам -> тэр алхамд чөлөөлөх нэрс
    trace = []
    for i in range(STEPS):
        for name in releases.pop(i, []):
            trace.append(("RL", name, 0))
        name = "P" + str(i)
        trace.append(("RQ", name, rng.randint(MIN_SIZE, MAX_SIZE)))
        releases.setdefault(i + rng.randint(MIN_LIFE, MAX_LIFE), []).append(name)
    return trace


def moved_bytes(before, after):
    """Compaction-д хаяг нь өөрчлөгдсөн (шилжсэн) процессуудын нийт хэмжээ."""
    old = {b[2]: b[0] for b in before[1] if b[2] is not None}
    total = 0
    for start, size, owner in after[1]:
        if owner is not None and old[owner] != start:
            total = total + size
    return total


def run_trace(trace, strategy, compact_on_failure):
    a = Allocator(MEMORY)
    live = set()
    result = {"requests": 0, "ok": 0, "frag_fail": 0, "nomem_fail": 0,
              "compactions": 0, "moved": 0, "frag_sum": 0.0, "holes_sum": 0, "util_sum": 0.0, "samples": 0}
    for kind, name, size in trace:
        if kind == "RQ":
            result["requests"] += 1
            before_free = a.get_stats()["free"]
            ok, _ = a.request(name, size, strategy)
            if not ok:
                if before_free >= size:
                    result["frag_fail"] += 1            # чөлөөт зай хангалттай ч нэг hole-д багтаагүй
                    if compact_on_failure:
                        snap = a.snapshot()
                        a.compact()
                        result["compactions"] += 1
                        result["moved"] += moved_bytes(snap, a.snapshot())
                        ok, _ = a.request(name, size, strategy)
                else:
                    result["nomem_fail"] += 1           # чөлөөт зай нь өөрөө хүрэлцээгүй
            if ok:
                result["ok"] += 1
                live.add(name)
        else:
            if name in live:
                a.release(name)
                live.discard(name)
        stats = a.get_stats()
        result["frag_sum"] += stats["external_fragmentation"]
        result["holes_sum"] += stats["hole_count"]
        result["util_sum"] += stats["used"] * 100.0 / stats["total"]
        result["samples"] += 1
    return result


def mean(values):
    return sum(values) / len(values)


def experiment():
    rows = []
    for strategy, title in (("F", "First-fit"), ("B", "Best-fit"), ("W", "Worst-fit")):
        for compact in (False, True):
            runs = [run_trace(make_trace(seed), strategy, compact) for seed in range(SEEDS)]
            req = mean([r["requests"] for r in runs])
            rows.append({
                "strategy": title,
                "compaction": "тийм" if compact else "үгүй",
                "requests": round(req, 1),
                # эцэст нь олгогдоогүй хүсэлт (compaction-тай бол шахаад дахин оролдсоны дараа)
                "final_fail_pct": round(mean([(r["requests"] - r["ok"]) * 100.0 / r["requests"] for r in runs]), 2),
                # анхны оролдлогод fragmentation-ээс болж татгалзсан (чөлөөт зай хангалттай ч нэг hole-д багтаагүй)
                "first_try_fragmentation_fail_pct": round(mean([r["frag_fail"] * 100.0 / r["requests"] for r in runs]), 2),
                "first_try_no_memory_fail_pct": round(mean([r["nomem_fail"] * 100.0 / r["requests"] for r in runs]), 2),
                "avg_external_frag_pct": round(mean([r["frag_sum"] / r["samples"] for r in runs]), 2),
                "avg_hole_count": round(mean([r["holes_sum"] / r["samples"] for r in runs]), 2),
                "avg_utilization_pct": round(mean([r["util_sum"] / r["samples"] for r in runs]), 2),
                "compactions_per_run": round(mean([r["compactions"] for r in runs]), 1),
                "moved_kb_per_compaction": round(mean([(r["moved"] / r["compactions"] / 1024.0) if r["compactions"] else 0.0 for r in runs]), 2),
            })
    return rows


def benchmark(blocks=1500, repeats=1000):
    """Ойролцоогоор `blocks` ширхэг блок (hole, процесс сөөлжлөн) байхад нэг request() дундажаар хэдэн мкс вэ."""
    out = []
    for strategy in "FBW":
        a = Allocator(blocks * 20 + 10 ** 6)
        for i in range(blocks):
            a.request("L" + str(i), 10, "F")
            a.request("S" + str(i), 10, "F")
        for i in range(blocks):
            a.release("S" + str(i))                # hole, процесс сөөлжлөн: ~blocks hole
        n_blocks = len(a.get_blocks())
        # хамгийн дор тохиолдол: ямар ч hole-д багтахгүй хүсэлт нь бүх жагсаалтыг уншина
        t0 = time.perf_counter()
        for _ in range(repeats):
            a.request("Z", 10 ** 9, strategy)
        elapsed = time.perf_counter() - t0
        out.append((strategy, n_blocks, elapsed * 1e6 / repeats))
    return out


def main():
    rows = experiment()
    path_csv = os.path.join(HERE, "results.csv")
    with open(path_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    lines = []
    lines.append("# Стратегийн туршилтын үр дүн (программаар гарсан)\n")
    lines.append("Орчин: Python " + sys.version.split()[0] + ". Тохиргоо: санах ой " + str(MEMORY) + " byte, "
                 + str(STEPS) + " хүсэлт, " + str(SEEDS) + " seed (0.." + str(SEEDS - 1) + "), хүсэлтийн хэмжээ "
                 + str(MIN_SIZE) + ".." + str(MAX_SIZE) + " byte, процессын настай " + str(MIN_LIFE) + ".." + str(MAX_LIFE) + " алхам.\n")
    lines.append("| Стратеги | Compaction | Эцсийн амжилтгүй хүсэлт % | Анхны татгалзал (fragmentation) % | Анхны татгалзал (санах ой дутсан) % | Дундаж fragmentation % | Дундаж hole | Ашиглалт % | Compaction/ажиллуулалт | Шилжсэн KB/compaction |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        lines.append("| " + " | ".join(str(r[k]) for k in ("strategy", "compaction", "final_fail_pct", "first_try_fragmentation_fail_pct",
                                                           "first_try_no_memory_fail_pct", "avg_external_frag_pct", "avg_hole_count",
                                                           "avg_utilization_pct", "compactions_per_run", "moved_kb_per_compaction")) + " |")
    lines.append("")
    lines.append("## Хурд: request() нэг дуудлагын дундаж хугацаа (хамгийн дор тохиолдол, бүх hole-ыг уншина)\n")
    lines.append("| Стратеги | Блокийн тоо | мкс / request |")
    lines.append("|---|---|---|")
    for strategy, n_blocks, micro in benchmark():
        lines.append("| " + strategy + " | " + str(n_blocks) + " | " + format(micro, ".1f") + " |")
    lines.append("\nХурдны тоо нь компьютерээс хамаарна; зөвхөн харьцаа ба O(n) өсөлтийг харуулна.\n")
    text = "\n".join(lines)
    with open(os.path.join(HERE, "results.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print(text)


if __name__ == "__main__":
    main()
