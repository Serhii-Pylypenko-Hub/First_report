from typing import Iterable, List
import heapq

# ---- Мінімальна вартість з'єднання кабелів ----
def min_total_cable_cost(lengths: Iterable[int]) -> int:
    try:
        h: List[int] = []
        for x in lengths:
            if x < 0:
                raise ValueError("Довжини мають бути невід’ємними.")
            h.append(int(x))

        if len(h) <= 1:
            return 0

        heapq.heapify(h)
        total = 0
        while len(h) > 1:
            a = heapq.heappop(h)
            b = heapq.heappop(h)
            cost = a + b
            total += cost
            heapq.heappush(h, cost)
        return total
    except Exception as e:
        print(f"min_total_cable_cost error: {e}")
        return 0

# ---- невеликий тест ----

if __name__ == "__main__":
    tests = [
        ([1, 2, 3, 4], 19),          # відсортований список
        ([4, 3, 2, 1], 19),          # той самий, але у зворотному порядку
        ([5], 0),                    # один кабель — з'єднань немає
        ([], 0),                     # порожній список
        ([7, 7, 7, 7], 56),          # усі однакові значення
        ([10, 20, 30, 40, 50], 330), # довший список
    ]

    for cables, expected in tests:
        result = min_total_cable_cost(cables)
        status = "✅" if result == expected else "❌"
        print(f"{status} cables={cables} -> очікуємо {expected}, отримали {result}")

