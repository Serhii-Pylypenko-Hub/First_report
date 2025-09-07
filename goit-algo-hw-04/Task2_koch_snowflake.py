from __future__ import annotations
import math
from pathlib import Path
from typing import List, Tuple
import matplotlib.pyplot as plt  

Point = Tuple[float, float]

def rotate(vx: float, vy: float, degrees: float) -> Point:
    r = math.radians(degrees)
    c, s = math.cos(r), math.sin(r)
    return vx * c - vy * s, vx * s + vy * c

def koch_segment(p1: Point, p2: Point, order: int) -> List[Point]:
    if order == 0:
        return [p1, p2]
    x1, y1 = p1
    x2, y2 = p2
    dx, dy = (x2 - x1) / 3.0, (y2 - y1) / 3.0
    a = (x1 + dx, y1 + dy)
    b = (x1 + 2 * dx, y1 + 2 * dy)
    vx, vy = b[0] - a[0], b[1] - a[1]
    rx, ry = rotate(vx, vy, 60)
    c = (a[0] + rx, a[1] + ry)

    s1 = koch_segment(p1, a, order - 1)
    s2 = koch_segment(a, c, order - 1)
    s3 = koch_segment(c, b, order - 1)
    s4 = koch_segment(b, p2, order - 1)
    return s1[:-1] + s2[:-1] + s3[:-1] + s4  

def build_snowflake(order: int, size: float = 1.0) -> List[Point]:
    h = math.sqrt(3) / 2 * size
    A = (0.0, 0.0)
    B = (size, 0.0)
    C = (size / 2.0, h)
    s1 = koch_segment(A, B, order)
    s2 = koch_segment(B, C, order)
    s3 = koch_segment(C, A, order)
    return s1[:-1] + s2[:-1] + s3  

def plot(points: List[Point], save_path: Path | None = None) -> None:
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    fig, ax = plt.subplots()
    ax.plot(xs, ys, linewidth=1.0) 
    ax.set_aspect("equal", adjustable="box")
    ax.axis("off")
    pad_x = (max(xs) - min(xs)) * 0.06 if len(xs) > 1 else 0.1
    pad_y = (max(ys) - min(ys)) * 0.06 if len(ys) > 1 else 0.1
    ax.set_xlim(min(xs) - pad_x, max(xs) + pad_x)
    ax.set_ylim(min(ys) - pad_y, max(ys) + pad_y)
    if save_path:
        fig.savefig(save_path, dpi=200, bbox_inches="tight", pad_inches=0)
        print(f"[OK] Збережено: {save_path}")
    plt.show()
    plt.close(fig)

def main():
    raw = input("Вкажіть рівень рекурсії (ціле, Enter = 3): ").strip()
    try:
        order = int(raw) if raw else 3
    except ValueError:
        print("[WARN] Некоректне значення, використовую 3")
        order = 3
    if order < 0:
        print("[WARN] Рівень не може бути від’ємним, використовую 0")
        order = 0
    if order > 7:
        print("[WARN] Дуже великий рівень може бути повільним (обмежую до 7)")
        order = 7

    save_ans = input("Зберегти у PNG? (вкажіть ім'я файлу або Enter, щоб пропустити): ").strip()
    save_path = Path(save_ans) if save_ans else None

    pts = build_snowflake(order, size=1.0)
    plot(pts, save_path)

if __name__ == "__main__":
    main()
