from __future__ import annotations
from typing import Optional, Iterable, Tuple

# ---------- Вузол однозв'язного списку. ----------

class Node:
    __slots__ = ("value", "next")
    def __init__(self, value: int, next: Optional["Node"]=None):
        self.value = value
        self.next = next

    def __repr__(self) -> str:
        return f"Node({self.value})"


# ---------- Допоміжні перетворення ----------
def from_iterable(items: Iterable[int]) -> Optional[Node]:
    try:
        head = None
        tail = None
        for x in items:
            node = Node(int(x))
            if head is None:
                head = tail = node
            else:
                tail.next = node
                tail = node
        return head
    except Exception as e:
        print(f"Помилка у from_iterable: {e}")
        return None

# ---------- Перетворює однозв'язний список у Python-список (для друку/тестів). ----------

def to_list(head: Optional[Node]) -> list[int]:
    out: list[int] = []
    try:
        cur = head
        while cur:
            out.append(cur.value)
            cur = cur.next
    except Exception as e:
        print(f"Помилка у to_list: {e}")
    return out


# ----------  Реверс ----------

# ----------  РІтеративний розворот списку (in-place). Повертає новий head. ----------

def reverse(head: Optional[Node]) -> Optional[Node]:
    try:
        prev = None
        cur = head
        while cur:
            nxt = cur.next
            cur.next = prev
            prev = cur
            cur = nxt
        return prev
    except Exception as e:
        print(f"Помилка у reverse: {e}")
        return head


# ----------  Сортування (merge sort для списку) ----------

# ----------  Розділяє список навпіл (slow/fast). Повертає (ліва_половина, права_половина). ----------

def _split(head: Optional[Node]) -> Tuple[Optional[Node], Optional[Node]]:
    try:
        if head is None or head.next is None:
            return head, None
        slow, fast = head, head.next
        while fast and fast.next:
            slow = slow.next  # type: ignore
            fast = fast.next.next
        mid = slow.next  # type: ignore
        slow.next = None  # type: ignore
        return head, mid
    except Exception as e:
        print(f"Помилка у _split: {e}")
        return head, None


# ----------  Злиття двох відсортованих списків у новий відсортований. ----------
def merge_sorted_lists(a: Optional[Node], b: Optional[Node]) -> Optional[Node]:
    try:
        dummy = Node(0)
        tail = dummy
        i, j = a, b
        while i and j:
            if i.value <= j.value:
                tail.next, i = i, i.next
            else:
                tail.next, j = j, j.next
            tail = tail.next
        tail.next = i if i else j
        return dummy.next
    except Exception as e:
        print(f"Помилка у merge_sorted_lists: {e}")
        return None

# ----------  Merge sort для однозв'язного списку (стабільне сортування). ----------
def sort_list(head: Optional[Node]) -> Optional[Node]:
    try:
        if head is None or head.next is None:
            return head
        left, right = _split(head)
        left_sorted = sort_list(left)
        right_sorted = sort_list(right)
        return merge_sorted_lists(left_sorted, right_sorted)
    except Exception as e:
        print(f"Помилка у sort_list: {e}")
        return head


# ---------- Демонстрація роботи ----------
def _demo_reverse():
    try:
        print("\n=== DEMO: reverse ===")
        data = [5, 1, 4, 2, 3]
        head = from_iterable(data)
        print("Функція reverse() розвертає список.")
        print("Вхідний список:      ", to_list(head))
        head = reverse(head)
        print("Очікувано зворотний: ", to_list(head))  # [3,2,4,1,5]
    except Exception as e:
        print(f"Помилка у _demo_reverse: {e}")

def _demo_sort():
    try:
        print("\n=== DEMO: sort_list (merge sort) ===")
        data = [7, 3, 9, 1, 1, 8, 2]
        head = from_iterable(data)
        print("Функція sort_list() сортує елементи у зростаючому порядку.")
        print("Вхідний список:      ", to_list(head))
        head = sort_list(head)
        print("Очікувано відсорт.:  ", to_list(head))  # [1,1,2,3,8,9]
    except Exception as e:
        print(f"Помилка у _demo_sort: {e}")

def _demo_merge_two_sorted():
    try:
        print("\n=== DEMO: merge_sorted_lists ===")
        a = from_iterable([1, 3, 5, 7])
        b = from_iterable([2, 2, 4, 6, 8])
        print("Функція merge_sorted_lists() з'єднує два відсортовані списки.")
        print("Перший:  ", to_list(a))
        print("Другий:  ", to_list(b))
        merged = merge_sorted_lists(a, b)
        print("Очікувано об'єднаний:", to_list(merged))  # [1,2,2,3,4,5,6,7,8]
    except Exception as e:
        print(f"Помилка у _demo_merge_two_sorted: {e}")

def _quick_self_check():
    """Короткі самоперевірки: показують, що функції працюють коректно."""
    try:
        # Перевірка reverse: чи дійсно список розгортається
        h = from_iterable([1, 2, 3])
        r = reverse(h)
        assert to_list(r) == [3, 2, 1], "reverse: очікували [3,2,1]"

        # Перевірка sort_list: чи відсортований у зростанні порядок
        h2 = from_iterable([4, 1, 3, 2])
        s = sort_list(h2)
        assert to_list(s) == [1, 2, 3, 4], "sort_list: очікували [1,2,3,4]"

        # Перевірка merge_sorted_lists: чи елементи йдуть у правильному порядку
        a = from_iterable([1, 3, 5])
        b = from_iterable([2, 4, 6])
        m = merge_sorted_lists(a, b)
        assert to_list(m) == [1, 2, 3, 4, 5, 6], "merge: очікували [1,2,3,4,5,6]"

        print("\n[OK] Усі швидкі перевірки пройдені успішно.")
    except AssertionError as ae:
        print(f"[FAIL] Перевірка: {ae}")
    except Exception as e:
        print(f"Помилка у _quick_self_check: {e}")

def main():
    _demo_reverse()
    _demo_sort()
    _demo_merge_two_sorted()
    _quick_self_check()

if __name__ == "__main__":
    main()
