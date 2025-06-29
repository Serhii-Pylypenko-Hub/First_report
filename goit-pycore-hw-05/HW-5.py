# Task1

def caching_fibonacci():
    cache = {}
    def fibonacci(n):
        if n in cache:
            return cache[n]
        if n == 0:
            cache[0] = 0
        elif n == 1:
            cache[1] = 1
        else:
            cache[n] = fibonacci(n - 1) + fibonacci(n - 2)
        return cache[n]
    attempts = 5 
    while attempts > 0:
        user_input = input("Введіть ціле невід’ємне число для обчислення Фібоначчі: ")

        if not user_input.isdigit():
            attempts -= 1
            print(f" Помилка: введене значення має бути цілим невід’ємним числом. Залишилось спроб: {attempts}")
            continue
        n = int(user_input)
        try:
            result = fibonacci(n)
            print(f" {n}-те число Фібоначчі: {result}")
            return  # успішно — виходимо
        except RecursionError:
            print(" Помилка: забагато рекурсивних викликів (число надто велике).")
            return
        except Exception as e:
            print(f" Неочікувана помилка: {e}")
            return
    print(" Вичерпано всі спроби. Спробуйте пізніше.")

# caching_fibonacci()

# Task2
      
import re
from typing import Callable, Generator

def generator_numbers(text: str) -> Generator[float, None, None]:

    try:
        # Знаходить всі дійсні числа, відокремлені пробілами
        for match in re.findall(r'\b\d+\.\d+\b', text):
            yield float(match)
    except Exception as e:
        print(f"❌ Помилка в generator_numbers: {e}")


def sum_profit(text: str, func: Callable[[str], Generator[float, None, None]]) -> float:
    try:
        return sum(func(text))
    except Exception as e:
        print(f"❌ Помилка в sum_profit: {e}")
        return 0.0


text = "Загальний дохід працівника складається з декількох частин: 1000.01 як основний дохід, доповнений додатковими надходженнями 27.45 і 324.00 доларів."
total_income = sum_profit(text, generator_numbers)
print(f"Загальний дохід: {total_income}")



        



