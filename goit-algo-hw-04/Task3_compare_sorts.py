from __future__ import annotations
import argparse
import random
import timeit
from dataclasses import dataclass
from typing import Callable, Iterable, List, Tuple, Dict
import csv
import sys

# ---------- Сортування ----------

def insertion_sort(a: List[int]) -> List[int]:
    """Стабільне in-place сортування вставками."""
    for i in range(1, len(a)):
        key = a[i]
        j = i - 1
        while j >= 0 and a[j] > key:
            a[j + 1] = a[j]
            j -= 1
        a[j + 1] = key
    return a

def merge_sort(a: List[int]) -> List[int]:
    """Стабільний ітеративний merge sort (без глибокої рекурсії)."""
    n = len(a)
    buf = [0] * n
    width = 1
    while width < n:
        for lo in range(0, n, 2 * width):
            mid = min(lo + width, n)
            hi = min(lo + 2 * width, n)
            i, j, k = lo, mid, lo
            while i < mid and j < hi:
                if a[i] <= a[j]:
                    buf[k] = a[i]; i += 1
                else:
                    buf[k] = a[j]; j += 1
                k += 1
            while i < mid:
                buf[k] = a[i]; i += 1; k += 1
            while j < hi:
                buf[k] = a[j]; j += 1; k += 1
            a[lo:hi] = buf[lo:hi]
        width *= 2
    return a

def timsort_sorted(a: List[int]) -> List[int]:
    """Timsort із стандартної бібліотеки (повертає новий список)."""
    return sorted(a)

# ---------- Генератори даних ----------

def gen_random(n: int, seed: int = 42) -> List[int]:
    rnd = random.Random(seed)
    return [rnd.randint(-10**9, 10**9) for _ in range(n)]

def gen_sorted(n: int) -> List[int]:
    return list(range(n))

def gen_reversed(n: int) -> List[int]:
    return list(range(n, 0, -1))

def gen_nearly_sorted(n: int, swaps_ratio: float = 0.02, seed: int = 42) -> List[int]:
    """Починаємо з відсортованого і робимо ~2% випадкових свопів."""
    rnd = random.Random(seed)
    a = list(range(n))
    swaps = max(1, int(n * swaps_ratio))
    for _ in range(swaps):
        i, j = rnd.randrange(n), rnd.randrange(n)
        a[i], a[j] = a[j], a[i]
    return a

def gen_many_duplicates(n: int, unique: int = 5, seed: int = 42) -> List[int]:
    """Лише кілька унікальних значень — сприятливий випадок для Timsort."""
    rnd = random.Random(seed)
    pool = [rnd.randint(-1000, 1000) for _ in range(unique)]
    return [rnd.choice(pool) for _ in range(n)]

# ---------- Бенчмарк ----------

@dataclass
class Result:
    algo: str
    dist: str
    n: int
    time_ms: float

def bench_one(func: Callable[[List[int]], List[int]],
              data: List[int],
              number: int,
              repeat: int) -> float:
    t = timeit.Timer(lambda: func(list(data)))
    best = min(t.repeat(repeat=repeat, number=number)) / number
    return best * 1000.0

def format_table(rows: List[Result]) -> str:
    dists = sorted({r.dist for r in rows})
    algos = ["Insertion", "Merge", "Timsort"]
    sizes = sorted({r.n for r in rows})

    lines = []
    for dist in dists:
        lines.append(f"\n### {dist}")
        header = "| n | " + " | ".join(algos) + " |"
        sep = "|---|" + "|".join(["---:"] * len(algos)) + "|"
        lines.append(header)
        lines.append(sep)
        for n in sizes:
            row = [r for r in rows if r.dist == dist and r.n == n]
            m = {r.algo: r.time_ms for r in row}
            lines.append("| {:>7} | {} |".format(
                n,
                " | ".join("{:>9.2f}".format(m.get(a, float('nan'))) for a in algos)
            ))
    return "\n".join(lines)

def main() -> int:
    ap = argparse.ArgumentParser(description="Порівняння Insertion/Merge/Timsort через timeit")
    ap.add_argument("--sizes", type=int, nargs="+", default=[1_000, 5_000, 10_000],
                    help="розміри масивів")
    ap.add_argument("--repeat", type=int, default=5, help="кількість повторів вимірювання")
    ap.add_argument("--number", type=int, default=1, help="кількість виконань у одному вимірі")
    ap.add_argument("--max-n2-size", type=int, default=6000,
                    help="максимальний n для запуску квадратичних алгоритмів (Insertion)")
    args = ap.parse_args()

    datasets: Dict[str, Callable[[int], List[int]]] = {
        "random": gen_random,
        "sorted": gen_sorted,
        "reversed": gen_reversed,
        "nearly_sorted(2%)": lambda n: gen_nearly_sorted(n, 0.02),
        "many_duplicates(5)": lambda n: gen_many_duplicates(n, 5),
    }

    algos: List[Tuple[str, Callable[[List[int]], List[int]]]] = [
        ("Insertion", insertion_sort),
        ("Merge",     merge_sort),
        ("Timsort",   timsort_sorted),
    ]

    results: List[Result] = []
    print(f"Python {sys.version.split()[0]}, repeat={args.repeat}, number={args.number}")
    print(f"Розміри: {args.sizes}; обмеження для Insertion: n ≤ {args.max_n2_size}\n")

    for dist_name, gen in datasets.items():
        print(f"→ Генерація: {dist_name}")
        caches: Dict[int, List[int]] = {}
        for n in args.sizes:
            base = gen(n)
            caches[n] = base

            for algo_name, func in algos:
                if algo_name == "Insertion" and n > args.max_n2_size:
                    continue
                ms = bench_one(func, base, number=args.number, repeat=args.repeat)
                results.append(Result(algo_name, dist_name, n, ms))
                print(f"  {algo_name:9s} n={n:>7} → {ms:8.2f} ms")
        print()

    # Вивід таблиць у консоль (Markdown-формат — зручно вставити в README)
    print("\n=== РЕЗУЛЬТАТИ (час у мс, менше — краще) ===")
    table_md = format_table(results)
    print(table_md)

    # Збереження у CSV
    with open("sort_bench.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["algo", "distribution", "n", "time_ms"])
        for r in results:
            w.writerow([r.algo, r.dist, r.n, f"{r.time_ms:.6f}"])
    print("\nЗбережено CSV: sort_bench.csv")

    # Короткі висновки (на основі типових результатів)
    print("""
Висновки (типово):
- Timsort (вбудований) стабільно найшвидший, особливо на nearly_sorted і з багатьма дублікатами
  завдяки виявленню вже відсортованих «runs», стабільності та вставкам на малих підмасивах.
- Merge має гарантоване O(n log n) і показує передбачуваний час, але витрачає додаткову пам'ять.
- Insertion — чудовий на майже відсортованих і малих масивах, але різко програє на великих n (O(n^2)).
""")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
