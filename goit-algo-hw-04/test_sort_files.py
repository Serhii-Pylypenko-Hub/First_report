# test_sort_files.py
from __future__ import annotations
import os, sys, shutil, subprocess, tempfile
from pathlib import Path

def find_sort_script() -> Path:
    """
    Повертає шлях до sort_files.py:
    1) у тій самій теці, що й тест;
    2) у підтеці goit-algo-hw-04/ (типовий кейс);
    3) пошук від поточної теки на глибину 3.
    """
    here = Path(__file__).parent
    candidates = [
        here / "sort_files.py",
        here / "goit-algo-hw-04" / "sort_files.py",
        Path.cwd() / "sort_files.py",
        Path.cwd() / "goit-algo-hw-04" / "sort_files.py",
    ]
    for c in candidates:
        if c.is_file():
            return c

    # остання спроба — неглибокий пошук
    for p in Path.cwd().rglob("sort_files.py"):
        if len(p.relative_to(Path.cwd()).parts) <= 4:
            return p

    raise FileNotFoundError("Не знайшов sort_files.py. "
                            "Поклади test_sort_files.py поряд із sort_files.py "
                            "або в корінь поруч із текою goit-algo-hw-04/.")

def try_symlink(src: Path, dst: Path) -> bool:
    try:
        if dst.exists() or dst.is_symlink():
            dst.unlink()
        os.symlink(src, dst)
        return True
    except Exception:
        return False  # на Windows може вимагати права

def make_fixture(base: Path) -> None:
    (base / "img").mkdir(parents=True, exist_ok=True)
    (base / "docs").mkdir(parents=True, exist_ok=True)
    (base / "nested/deep").mkdir(parents=True, exist_ok=True)
    (base / "other").mkdir(parents=True, exist_ok=True)
    (base / "a.txt").write_text("A", encoding="utf-8")
    (base / "b.TXT").write_text("B (upper ext)", encoding="utf-8")
    (base / "img/photo.jpg").write_text("JPG", encoding="utf-8")
    (base / "docs/readme").write_text("noext", encoding="utf-8")  # без розширення
    (base / "nested/deep/dup.txt").write_text("dup1", encoding="utf-8")
    (base / "other/dup.txt").write_text("dup2", encoding="utf-8")
    try_symlink(base / "a.txt", base / "link_to_a.txt")  # може не створитися — ок

def run_cli(script: Path, src: Path, dst: Path, *extra: str) -> subprocess.CompletedProcess:
    cmd = [sys.executable, str(script), str(src), str(dst), *extra]
    return subprocess.run(cmd, text=True, capture_output=True, check=True)

def assert_exists(p: Path) -> None:
    if not p.exists():
        raise AssertionError(f"Очікував існування: {p}")

def test_dst_outside(script: Path) -> None:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        src, dst = tmp / "input", tmp / "dist"
        src.mkdir()
        make_fixture(src)

        # dry-run (має відпрацювати без помилок)
        run_cli(script, src, dst, "--dry-run")

        # реальний запуск
        res = run_cli(script, src, dst)
        print("=== SUMMARY 1 ===\n", res.stdout)

        # перевірки
        assert_exists(dst / "txt" / "a.txt")
        assert_exists(dst / "txt" / "b.TXT")       # ім'я збережено, тека — 'txt'
        assert_exists(dst / "jpg" / "photo.jpg")
        assert_exists(dst / "_noext" / "readme")

        # колізії імен
        txt_files = [p.name for p in (dst / "txt").glob("*.txt")]
        if "dup.txt" not in txt_files or "dup (1).txt" not in txt_files:
            raise AssertionError(f"Не знайшов 'dup.txt' і 'dup (1).txt' у {txt_files}")

        # симлінк пропускаємо (якщо він взагалі створився)
        assert not (dst / "txt" / "link_to_a.txt").exists()

def test_dst_inside(script: Path) -> None:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        src = tmp / "input"
        src.mkdir()
        make_fixture(src)
        dst = src / "dist"  # DST всередині SRC

        res = run_cli(script, src, dst)
        print("=== SUMMARY 2 ===\n", res.stdout)

        assert_exists(dst / "txt" / "a.txt")
        total_dst_files = sum(1 for p in dst.rglob("*") if p.is_file())
        if not (3 <= total_dst_files <= 10):
            raise AssertionError(f"Підозріло багато файлів у DST: {total_dst_files}")

def main():
    script = find_sort_script()
    print(f"Використовую sort_files.py: {script}\n")

    try:
        print("== ТЕСТ 1: DST поза SRC ==")
        test_dst_outside(script)
        print("OK ✅\n")

        print("== ТЕСТ 2: DST всередині SRC ==")
        test_dst_inside(script)
        print("OK ✅\n")

        print("ВСІ ТЕСТИ ПРОЙДЕНО ✅")
    except subprocess.CalledProcessError as e:
        print("❌ Помилка під час виконання CLI")
        print("CMD failed, returncode:", e.returncode)
        print("STDOUT:\n", e.stdout)
        print("STDERR:\n", e.stderr)
    except AssertionError as e:
        print("❌ ТЕСТ НЕ ПРОЙДЕНО:", e)
        raise

if __name__ == "__main__":
    main()
