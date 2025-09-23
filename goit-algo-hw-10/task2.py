import random
import numpy as np
import matplotlib.pyplot as plt
from typing import Callable, Tuple

# Функція та межі інтегрування
def f(x: float) -> float:
    return x ** 2

A: float = 0.0
B: float = 2.0
N_SAMPLES: int = 100_000  # кількість випадкових точок для Монте-Карло

# Побудова графіка
x = np.linspace(-0.5, 2.5, 400)
y = f(x)

fig, ax = plt.subplots()
ax.plot(x, y, 'r', linewidth=2)

ix = np.linspace(A, B)
iy = f(ix)
ax.fill_between(ix, iy, color='gray', alpha=0.3)

ax.set_xlim([x[0], x[-1]])
ax.set_ylim([0, max(y) + 0.1])
ax.set_xlabel('x')
ax.set_ylabel('f(x)')
ax.axvline(x=A, color='gray', linestyle='--')
ax.axvline(x=B, color='gray', linestyle='--')
ax.set_title(f'Графік інтегрування f(x) = x^2 від {A} до {B}')
plt.grid()
plt.show()


# ============================================================
#  ФУНКЦІЇ: МОНТЕ-КАРЛО + АНАЛІТИКА + QUAD
# ============================================================

"""Обчислення інтеграла методом Монте-Карло."""

def monte_carlo_integral(func: Callable[[float], float],
                         a: float,
                         b: float,
                         n: int,
                         seed: int | None = 42) -> float:
    rng = random.Random(seed)
    acc = 0.0
    for _ in range(n):
        x = rng.uniform(a, b)
        acc += func(x)
    return (b - a) * (acc / n)

"""Аналітичне значення ∫ x^2 dx = (x^3)/3."""

def analytic_integral_x2(a: float, b: float) -> float:

    return (b ** 3 - a ** 3) / 3.0

"""Обчислення інтеграла через scipy.integrate.quad, якщо бібліотека доступна."""

def try_scipy_quad(func: Callable[[float], float],
                   a: float,
                   b: float) -> Tuple[float | None, float | None]:
    try:
        import scipy.integrate as spi
    except Exception:
        return None, None
    val, err = spi.quad(func, a, b)
    return float(val), float(err)


# ============================================================
#  ТЕСТ (запуск і порівняння результатів)
# ============================================================

if __name__ == "__main__":
    mc_val = monte_carlo_integral(f, A, B, N_SAMPLES)
    analytic_val = analytic_integral_x2(A, B)
    quad_val, quad_err = try_scipy_quad(f, A, B)

    print("=== ОБЧИСЛЕННЯ ІНТЕГРАЛА f(x)=x^2 НА [0,2] ===")
    print(f"Monte Carlo ({N_SAMPLES} точок) ≈ {mc_val:.8f}")
    print(f"Аналітично                = {analytic_val:.8f}")
    if quad_val is not None:
        print(f"SciPy quad                = {quad_val:.8f} (похибка ~ {quad_err:.2e})")

    # Перевірка: результат Монте-Карло має бути близьким до аналітичного
    assert abs(mc_val - analytic_val) < 0.05, "Monte Carlo занадто далеко від істини!"


# ============================================================
#  ВИСНОВКИ (Markdown у коді)
# ============================================================

"""
- **Метод Монте-Карло** оцінює інтеграл як середнє значення f(x) на [a,b], помножене на довжину інтервалу.
- Для f(x)=x² на [0,2] «правильне» значення інтеграла = 8/3 ≈ 2.6667.
- При N=100 000 результат Монте-Карло виходить дуже близьким до істинного значення.
- Перевірка через SciPy (quad) підтверджує точність (результати збігаються з аналітичним).
- Похибка Монте-Карло ~ O(1/√N): близький до інших методів, щоб у 10 разів зменшити похибку, потрібно більше точок.
- Висновок: метод зручний для складних функцій, коли аналітичний інтеграл важко обчислити, але для простих випадків краще використовувати точний метод.
"""
