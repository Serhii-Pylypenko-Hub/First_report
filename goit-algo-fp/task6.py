#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import Dict, List, Tuple

items = {
  "pizza": {"cost": 50, "calories": 300},
  "hamburger": {"cost": 40, "calories": 250},
  "hot-dog": {"cost": 30, "calories": 200},
  "pepsi": {"cost": 10, "calories": 100},
  "cola": {"cost": 15, "calories": 220},
  "potato": {"cost": 25, "calories": 350}
}

def greedy_algorithm(items: Dict[str, Dict[str,int]], budget: int) -> List[str]:
    """Жадібний відбір за співвідношенням калорії/вартість.
    Для чого: простий швидкий baseline, не завжди оптимальний.
    """
    try:
        ranked = sorted(items.items(), key=lambda kv: kv[1]["calories"]/kv[1]["cost"], reverse=True)
        chosen, spent = [], 0
        for name, meta in ranked:
            if spent + meta["cost"] <= budget:
                chosen.append(name)
                spent += meta["cost"]
        return chosen
    except Exception as e:
        print(f"Помилка у greedy_algorithm: {e}")
        return []

def dynamic_programming(items: Dict[str, Dict[str,int]], budget: int) -> List[str]:
    """0/1 knapSack по бюджету. Повертає оптимальний набір назв."""
    try:
        names = list(items.keys())
        costs = [items[n]["cost"] for n in names]
        cals  = [items[n]["calories"] for n in names]
        n = len(names)

        # dp[b] = макс калорій при бюджеті b; keep[b] = індекс останнього доданого
        dp = [0]*(budget+1)
        keep = [[False]*(budget+1) for _ in range(n)]

        for i in range(n):
            for b in range(budget, costs[i]-1, -1):
                cand = dp[b - costs[i]] + cals[i]
                if cand > dp[b]:
                    dp[b] = cand
                    keep[i][b] = True

        # Відновлення набору
        res = []
        b = budget
        for i in range(n-1, -1, -1):
            if keep[i][b]:
                res.append(names[i])
                b -= costs[i]
        res.reverse()
        return res
    except Exception as e:
        print(f"Помилка у dynamic_programming: {e}")
        return []

def main():
    tries = 0
    budget = None
    while tries < 3:
        try:
            raw = input("Вкажіть бюджет (ціле число від 0 до 170, напр. 100): ").strip()
            budget = int(raw)
            if 0 <= budget <= 170:
                break
            else:
                print("❌ Бюджет має бути у межах від 0 до 170.")
        except ValueError:
            print("❌ Потрібно ввести саме ціле число.")
        tries += 1

    if budget is None or not (0 <= budget <= 170):
        print("Спробуйте наступним разом.")
        return

    print("✅ Бюджет:", budget)
    g = greedy_algorithm(items, budget)
    d = dynamic_programming(items, budget)
    print("Greedy вибір:", g, "-> калорій:", sum(items[x]['calories'] for x in g), "вартість:", sum(items[x]['cost'] for x in g))
    print("DP вибір:",     d, "-> калорій:", sum(items[x]['calories'] for x in d), "вартість:", sum(items[x]['cost'] for x in d))

if __name__ == "__main__":
    main()
