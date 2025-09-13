import timeit
import requests
import timeit
import re

# ================= Алгоритми ==================

def boyer_moore(text, pattern):
    m, n = len(pattern), len(text)
    if m == 0:
        return 0
    skip = {c: m for c in set(text)}
    for i in range(m - 1):
        skip[pattern[i]] = m - i - 1
    i = 0
    while i <= n - m:
        j = m - 1
        while j >= 0 and text[i + j] == pattern[j]:
            j -= 1
        if j < 0:
            return i
        i += skip.get(text[i + m - 1], m)
    return -1


def kmp(text, pattern):
    m, n = len(pattern), len(text)
    if m == 0:
        return 0
    lps = [0] * m
    length = 0
    i = 1
    while i < m:
        if pattern[i] == pattern[length]:
            length += 1
            lps[i] = length
            i += 1
        else:
            if length:
                length = lps[length - 1]
            else:
                lps[i] = 0
                i += 1
    i = j = 0
    while i < n:
        if pattern[j] == text[i]:
            i += 1
            j += 1
        if j == m:
            return i - j
        elif i < n and pattern[j] != text[i]:
            if j:
                j = lps[j - 1]
            else:
                i += 1
    return -1


def rabin_karp(text, pattern):
    m, n = len(pattern), len(text)
    if m == 0:
        return 0
    q = 1_000_000_007
    d = 256
    h = pow(d, m - 1, q)
    p = t = 0
    for i in range(m):
        p = (d * p + ord(pattern[i])) % q
        t = (d * t + ord(text[i])) % q
    for s in range(n - m + 1):
        if p == t:
            if text[s:s + m] == pattern:
                return s
        if s < n - m:
            t = (d * (t - ord(text[s]) * h) + ord(text[s + m])) % q
            if t < 0:
                t += q
    return -1

# ================= Допоміжні функції ==================

def download_text(url):
    """Завантаження тексту з Google Drive"""
    response = requests.get(url)
    response.raise_for_status()
    return response.text

def measure_time(func, text, pattern, repeat=5):
    stmt = lambda: func(text, pattern)
    times = [timeit.timeit(stmt, number=1) for _ in range(repeat)]
    mean = sum(times) / repeat
    std = (sum((t - mean) ** 2 for t in times) / repeat) ** 0.5
    return mean, std

def get_middle_word(text, min_len=6):
    """Вибираємо слово з тексту для перевірки (яке точно існує)"""
    words = re.findall(r'\w+', text)
    for word in words:
        if len(word) >= min_len:
            return word
    return text[:min_len]

# ================= Основна програма ==================

def main():
    url1 = "https://drive.google.com/uc?id=1EdQUqE_qLDCL_54v8aQ5zlcMf2L9dF_B"
    url2 = "https://drive.google.com/uc?id=1o5uZ8NBMtZmThGIeilCRWgspIOfOnbzQ"

    try:
        text1 = download_text(url1)
        text2 = download_text(url2)
    except Exception as e:
        print(f"Помилка завантаження: {e}")
        return

    exist1 = get_middle_word(text1, min_len=10)
    fake1 = "qwertyuiop"
    exist2 = get_middle_word(text2, min_len=10)
    fake2 = "zxcvbnmasd"

    algos = [
        ("Boyer-Moore", boyer_moore),
        ("Knuth-Morris-Pratt", kmp),
        ("Rabin-Karp", rabin_karp),
    ]

    print("=== Стаття 1 ===")
    for name, fn in algos:
        mean1, std1 = measure_time(fn, text1, exist1)
        mean2, std2 = measure_time(fn, text1, fake1)
        print(f"{name}: існуючий: {mean1:.6f}±{std1:.6f} c, вигаданий: {mean2:.6f}±{std2:.6f} c")

    print("\n=== Стаття 2 ===")
    for name, fn in algos:
        mean1, std1 = measure_time(fn, text2, exist2)
        mean2, std2 = measure_time(fn, text2, fake2)
        print(f"{name}: існуючий: {mean1:.6f}±{std1:.6f} c, вигаданий: {mean2:.6f}±{std2:.6f} c")


if __name__ == "__main__":
    main()

