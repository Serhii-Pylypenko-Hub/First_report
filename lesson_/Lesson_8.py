# from typing import Callable

# def add(a: int, b: int) -> int:
#     return a + b

# def multiply(a: int, b: int) -> int:
#     return a * b

# def apply_operation(a: int, b: int, operation: Callable[[int, int], int]) -> int:
#     return operation(a, b)

# # Використання
# result_add = apply_operation(5, 3, add)
# result_multiply = apply_operation(5, 3, multiply)

# print(result_add, result_multiply)
# from typing import Callable

# def power(exponent: int) -> Callable[[int], int]:
#     def inner(base: int) -> int:
#         return base ** exponent
#     return inner

# # Використання
# square = power(2)
# cube = power(3)

# print(square(4)) 
# print(cube(4))
# from typing import Callable, Dict

# # Визначення функцій
# def add(a: int, b: int) -> int:
#     return a + b

# def multiply(a: int, b: int) -> int:
#     return a * b

# def power(exponent: int) -> Callable[[int], int]:
#     def inner(base: int) -> int:
#         return base ** exponent
#     return inner

# # Використання power для створення функцій square та cube
# square = power(2)
# cube = power(3)

# # Словник операцій
# operations: Dict[str, Callable] = {
#     'add': add,
#     'multiply': multiply,
#     'square': square,
#     'cube': cube
# }

# # Використання операцій
# result_add = operations['add'](10, 20)  # 30
# result_square = operations['square'](5)  # 25

# print(result_add)  
# print(result_square)  
# def outer_function(msg):
#     message = msg

#     def inner_function():
#         print(message)

#     return inner_function

# # Створення замикання
# my_func = outer_function("Hello, world!")
# my_func()
# from typing import Callable

# def counter() -> Callable[[], int]:
#     count = 0

#     def increment() -> int:
#         # використовуємо nonlocal, щоб змінити змінну в замиканні
#         nonlocal count  
#         count += 1
#         return count

#     return increment

# # Створення лічильника
# count_calls = counter()

# # Виклики лічильника
# print(count_calls())  # Виведе 1
# print(count_calls())  # Виведе 2
# print(count_calls())  # Виведе 3
# print(count_calls())
# from typing import Callable

# def discount(discount_percentage: int) -> Callable[[float], float]:
#     def apply_discount(price: float) -> float:
#         return price * (1 - discount_percentage / 100)
#     return apply_discount

# # Каррінг в дії
# ten_percent_discount = discount(10)
# twenty_percent_discount = discount(20)

# # Застосування знижок
# discounted_price = ten_percent_discount(500)  # 450.0
# print(discounted_price)

# discounted_price = twenty_percent_discount(500)  # 400.0
# print(discounted_price)

# from typing import Callable, Dict

# def discount(discount_percentage: int)-> Callable[[float],float]:
#     def apply_discount(price: float) -> float:
#         return price * (1- discount_percentage/100)
#     return apply_discount

# discount_functions: dict[str, Callable] = {"10%":discount(10),"20%":discount(20),"30%":discount(30)}

# price = 500
# discount_tuple = "20%"

# discount_price = discount_functions[discount_tuple](price)
# print(f"Ціна зі знижкою  {discount_tuple}:{discount_price}")

# def complicated(x: int, y: int) -> int:
#     return x + y

# def logger(func):
#     def inner(x: int, y: int) -> int:
#         print(f'Call functoin: {func.__name__}:{x},{y}')
#         result = func(x, y)
#         print(f'Function {func.__name__} stop action: {result}')
#         return result
#     return inner

# complicated = logger(complicated)
# print(complicated(2,3))

# from functools import wraps

# def logger(func):
#     @wraps(func)
#     def inner(x: int, y: int) -> int:
#         print(f"Викликається функція: {func.__name__}: {x}, {y}")
#         result = func(x, y)
#         print(f"Функція {func.__name__} завершила виконання: {result}")
#         return result

#     return inner

# @logger
# def complicated(x: int, y: int) -> int:
#     return x + y

# print(complicated(2, 3))
# print(complicated.__name__)
# nums = [1, 2, 3, 4, 5]
# nums_sorted = sorted(nums, key=lambda x: -x)
# print(nums_sorted)
# nums1 = [1, 2, 3, ]
# # for i in map(lambda x: x**2, nums):
# #     print(i) 
# # squared_nums = list(map(lambda x: x**2, nums))
# # print(squared_nums)
# nums2 = [4, 5, 6]
# sum_sum = map(lambda x, y: x + y, nums1, nums2)
# # print(list(sum_sum))
# nums = [1, 2, 3, 4, 5]
# squared_nums = [x * x for x in nums]
# print(squared_nums)
# nums1 = [1, 2, 3]
# nums2 = [4, 5, 6]
# sum_nums = [x + y for x, y in zip(nums1, nums2)]
# print(sum_nums)
# event_num = filter(lambda x: x % 2 == 0, range (1,11))
# print(list(event_num))
# def is_positive(x):
#     return x >= 0
# num = [-2, -1, 0, 1, 2]
# positive_num = filter(is_positive,num)
# print(list(positive_num))
# some_str = 'Видавництво А-БА-БА-ГА-ЛА-МА-ГА'
# new_str = ''.join(list(filter(lambda x: x.islower(),some_str)))
# print(new_str)
# nums = [1, 2, 3, 4, 5, 6]
# even_nums = [x for x in nums if x % 2 == 0]
# print(even_nums)
# nums = [0, False, 5, 0]
# result = any(nums)  
# print(result)
# nums = [1, 3, 5, 7, 9]
# result = any(x % 2 == 0 for x in nums)
# print(result)
# nums = [1, 2, 3, 4]
# result = all(nums) 
#  
# print(result)
# words = ["Hello", "World", "Python"]
# is_all_even = all(word.istitle() for word in words)
# print(is_all_even)