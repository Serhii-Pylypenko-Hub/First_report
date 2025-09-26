from __future__ import annotations
import sys
import math
import time
from typing import List, Tuple

import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection



# ---------- Рекурсивне побудова фрактального дерева ----------
def build_segments(
    x: float, y: float,
    length: float,
    angle: float,
    level: int,
    segments: List[Tuple[Tuple[float, float], Tuple[float, float]]],
    decay: float,
    delta_rad: float
) -> None:
    try:
        if level <= 0 or length <= 0:
            return

        x2 = x + length * math.cos(angle)
        y2 = y + length * math.sin(angle)

        segments.append(((x, y), (x2, y2)))

        next_len = length * decay
        next_level = level - 1
        build_segments(x2, y2, next_len, angle + delta_rad, next_level, segments, decay, delta_rad)
        build_segments(x2, y2, next_len, angle - delta_rad, next_level, segments, decay, delta_rad)
    except Exception as e:
        print(f"Помилка у build_segments: {e}")



# ----------     Готуємо дані та виконує швидкий рендер  ----------

def draw_tree_fast(level: int) -> None:
    try:
        # Параметри фрактала (можна змінити під задачі/смак)
        START_LEN = 1.0      
        DECAY = 0.72           
        DELTA_RAD = math.pi/4  

        segments: List[Tuple[Tuple[float, float], Tuple[float, float]]] = []

        # Побудова сегментів
        build_segments(
            x=0.0, y=0.0,
            length=START_LEN,
            angle=math.pi/2,
            level=level,
            segments=segments,
            decay=DECAY,
            delta_rad=DELTA_RAD
        )

        # Рендер одним махом
        fig, ax = plt.subplots(figsize=(7.5, 7.5))
        lc = LineCollection(segments, linewidths=1.2)  # одна колекція ліній — дуже швидко
        ax.add_collection(lc)

        # Аксіси: рівний масштаб і невелика рамка навколо
        ax.autoscale()
        ax.set_aspect("equal", adjustable="box")
        ax.axis("off")
        plt.tight_layout()
        plt.show()
    except Exception as e:
        print(f"Помилка у draw_tree_fast: {e}")


# ----------  Головна функція з безпечним парсингом рівня рекурсії ----------
def main():
    # Дозволяємо рівень у межах 1..15, щоб уникнути надто довгого рендеру/глибокої рекурсії.
    MIN_LEVEL, MAX_LEVEL = 1, 15
    tries = 0
    level = None

    while tries < 3:
        try:
            raw = input(f"Вкажіть рівень рекурсії ({MIN_LEVEL}..{MAX_LEVEL}, напр. 9): ").strip()
            # Порожній ввід — візьмемо дефолт (9)
            if raw == "":
                level = 9
                break

            level = int(raw)
            if MIN_LEVEL <= level <= MAX_LEVEL:
                break
            else:
                print(f"❌ Рівень має бути у межах від {MIN_LEVEL} до {MAX_LEVEL}.")
        except ValueError:
            print("❌ Потрібно ввести саме ціле число.")
        tries += 1

    if level is None or not (MIN_LEVEL <= level <= MAX_LEVEL):
        print("Спробуйте наступним разом.")
        return

    # Захист від глибокої рекурсії
    import sys, time
    sys.setrecursionlimit(max(2000, 10 * level))

    t0 = time.perf_counter()
    draw_tree_fast(level)
    t1 = time.perf_counter()
    print(f"[INFO] Рівень={level}, час побудови ≈ {t1 - t0:.3f} с")



if __name__ == "__main__":
    main()
