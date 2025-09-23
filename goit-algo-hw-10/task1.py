from __future__ import annotations
from typing import Dict, List

# Система монет (канонічна для greedy): від найбільших до найменших
COINS: List[int] = [50, 25, 10, 5, 2, 1]


# ============================================================
# Функція жадібного алгоритму
# ============================================================

def find_coins_greedy(amount: int, coins: List[int] = COINS) -> Dict[int, int]:
    if amount < 0:
        raise ValueError("Сума не може бути від'ємною")

    remaining = amount
    res: Dict[int, int] = {}
    for c in sorted(coins, reverse=True):
        if remaining == 0:
            break
        k = remaining // c
        if k:
            res[c] = k
            remaining -= k * c

    if remaining != 0:
        # У нашій системі цього не трапиться, але лишаємо саніті-гак.
        res["_uncovered"] = remaining  # type: ignore
    return res

# ============================================================
# Функція динамічного програмування
# ============================================================


def find_min_coins(amount: int, coins: List[int] = COINS) -> Dict[int, int]:
    if amount < 0:
        raise ValueError("Сума не може бути від'ємною")
    if amount == 0:
        return {}

    INF = amount + 1
    dp = [0] + [INF] * amount
    prev = [-1] * (amount + 1)

    for s in range(1, amount + 1):
        best = INF
        best_coin = -1
        for c in coins:
            if s - c >= 0 and dp[s - c] + 1 < best:
                best = dp[s - c] + 1
                best_coin = c
        dp[s] = best
        prev[s] = best_coin

    if dp[amount] == INF:
        return {"_uncovered": amount}

    # Відновлення рішення: словник {номінал: кількість}
    res: Dict[int, int] = {}
    s = amount
    while s > 0:
        c = prev[s]
        if c == -1:
            return {"_uncovered": s}
        res[c] = res.get(c, 0) + 1
        s -= c
    # Зручно повертати відсортованим
    return dict(sorted(res.items(), reverse=True))


# ============================================================
# ТЕСТ (перевірка та вивід результатів)
# ============================================================

def _pretty(d: Dict[int, int]) -> str:
    return "{" + ", ".join(f"{k}: {v}" for k, v in d.items() if isinstance(k, int)) + "}"

if __name__ == "__main__":
    amount = 113

    greedy = find_coins_greedy(amount)
    dp = find_min_coins(amount)

    print("=== ТЕСТ ДЛЯ СУМИ:", amount, "===")
    print("Greedy:", _pretty(greedy))
    print("DP    :", _pretty(dp))

    # sanity-check для канонічної системи монет (результати мають збігатися за набором монет)
    assert {k: v for k, v in greedy.items() if isinstance(k, int)} == \
           {k: v for k, v in dp.items() if isinstance(k, int)}, \
           "Для канонічної системи монет greedy і DP мають збігатися."


# ============================================================
# ВИСНОВКИ 
# ============================================================

"""

- **Жадібний алгоритм (Greedy)**:
  - Для системи монет `[50, 25, 10, 5, 2, 1]` завжди знаходить оптимальне розбиття.
  - Дуже швидкий: для фіксованої кількості номіналів має часову складність ~ **O(1)**/O(n),
    пам'ять **O(1)**.
  - Простий в реалізації та ідеально підходить для касових систем з «канонічними» монетами.

- **Динамічне програмування (DP)**:
  - Гарантує **мінімальну** кількість монет для **будь-якого** набору номіналів.
  - Складність **O(n · S)** (де `S` — сума), пам'ять **O(S)**; на великих сумах повільніше за greedy.
  - Використовує таблицю, що дозволяє відновити конкретний набір монет.

- **Підсумок**:
  - У нашому випадку (канонічні монети) обидва підходи дають однаковий результат,
    але **greedy** значно **швидший** і **достатній**.
  - Якщо набір номіналів зміниться на «нетиповий» і greedy почне помилятись,
    **DP** гарантує коректність.
"""
