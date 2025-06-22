# Завдання 1
# Створіть функцію get_days_from_today(date), яка розраховує кількість днів між заданою датою і поточною датою.

import datetime
from datetime import date
def get_days_from_today():
    attempts = 3
    while attempts > 0:
            date_enter = input("Введіть дату у форматі РРРР-ММ-ДД (наприклад, '2020-10-09'): ") 
            try:
                parsed_date = datetime.datetime.strptime(date_enter, "%Y-%m-%d").date()
                today = datetime.datetime.today().date()
                delta = today - parsed_date
                print(f"Введена дата: {parsed_date}")
                print(f"Кількість днів між датами: {delta.days}")
                return  # вихід з функції після успішного введення
            except ValueError:
                attempts -= 1
                print(f"❌ Неправильний формат. Залишилось спроб: {attempts}")
                if attempts == 0:
                    print("🔴 Вичерпано всі спроби. Спробуйте пізніше.")

    get_days_from_today()

# Завдання 2
# Вам необхідно написати функцію get_numbers_ticket(min, max, quantity),
# яка допоможе генерувати набір унікальних випадкових чисел для таких лотерей.
# Вона буде повертати випадковий набір чисел у межах заданих параметрів,
# причому всі випадкові числа в наборі повинні бути унікальні.


import random

def get_numbers_ticket(min_value, max_value, quantity):
    min = 1
    max = 1000
    quantity = 5
    range_x = range(min_value, max_value + 1)
    lotary = sorted(random.sample(range_x,5))
    attempts = 5
    while attempts > 0:
        try:
            user_input = input(f"Введіть {quantity} чисел від {min} до {max} через пробіл: ")
            user_numbers = list(map(int, user_input.strip().split()))
            if len(set(user_numbers)) != 5:
                print(f"❌ Числа повинні бути унікальні та потрібно ввести рівно {quantity} чисел.")
                attempts -= 1
                continue
            if not all(1 <= num <= 1000 for num in user_numbers):
                print(f"❌ Усі числа мають бути в діапазоні від {min} до {max}.")
                attempts -= 1
                continue
            user_numbers.sort()
            print(f"🎟 Лотерейний квиток: {lotary}")
            print(f" Ваші числа:       {user_numbers}")
            if user_numbers == lotary:
                print(" Вітаємо! Ви вгадали всі числа!")
            else:
                print(" На жаль, спробуйте ще раз.")
            return  
        except ValueError:
            print("❌ Введіть тільки цілі числа.")
            attempts -= 1

    print("🔴 Ви вичерпали всі спроби.")
get_numbers_ticket(1, 1000, 5)



# Завдання 3

# У вашій компанії ведеться активна маркетингова кампанія за допомогою SMS-розсилок.
# Для цього ви збираєте телефонні номери клієнтів із бази даних,
# але часто стикаєтеся з тим, що номери записані у різних форматах.

import re
ч = "+380508889900"
print(len(ч))

def normalize_phone(phone_number: str) -> str:
    cleaned = re.sub(r'[^\d+]', '', phone_number.strip())
    len_num_tell = 13
    if len(cleaned) == 13 and cleaned.startswith('+380'):
        return cleaned
    elif cleaned.startswith('380') and len(cleaned) == len_num_tell -1 :
        return '+' + cleaned
    elif cleaned.startswith('0') and len(cleaned) == len_num_tell -3 :
        return '+38' + cleaned
    else :
        cleaned 

raw_numbers = [
    "067\\t123 4567",
    "(095) 234-5678\\n",
    "+380 44 123 4567",
    "380501234567",
    "    +38(050)123-32-34",
    "     0503451234",
    "(050)8889900",
    "38050-111-22-22",
    "38050 111 22 11   ",
]

sanitized_numbers = [normalize_phone(num) for num in raw_numbers]
print("Нормалізовані номери телефонів для SMS-розсилки:", sanitized_numbers)

# Завдання 4

# У межах вашої організації, ви відповідаєте за організацію привітань колег з днем народження.
# Щоб оптимізувати цей процес, вам потрібно створити функцію get_upcoming_birthdays,
# яка допоможе вам визначати, кого з колег потрібно привітати.
# Функція повинна повернути список всіх у кого день народження вперед на 7 днів включаючи поточний день.

from datetime import datetime, timedelta, date
def get_upcoming_birthdays(users):
    today = date.today()
    end_date = today + timedelta(days=7)
    congratulations = []
    for user in users:
        birthday = datetime.strptime(user["birthday"], "%Y.%m.%d").date()
        birthday_this_year = birthday.replace(year=today.year)
        if birthday_this_year < today:
            birthday_this_year = birthday_this_year.replace(year=today.year + 1)
        if today <= birthday_this_year <= end_date:
            congr_date = birthday_this_year
            if congr_date.weekday() == 5:
                congr_date += timedelta(days=2)
            elif congr_date.weekday() == 6:
                congr_date += timedelta(days=1)
            congratulations.append({"name":user["name"],"congratulations_date":congr_date.strftime("%Y.%m.%d")})       
    return congratulations
users = [
    {"name": "John Doe", "birthday": "1985.06.16"},
    {"name": "Jane Smith", "birthday": "1990.06.22"},
    {"name": "Anna Lee", "birthday": "1992.06.28"}
]

upcoming = get_upcoming_birthdays(users)
print(upcoming)
