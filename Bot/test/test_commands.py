# Bot/test/test_commands.py

import sys
import os

# Додаємо корінь проєкту до sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from Bot.comands_file import say_hello

def test_say_hello(capsys):
    """
    Тестуємо команду say_hello(), перевіряємо вивід у консоль.
    """
    say_hello()
    captured = capsys.readouterr()
    assert "Hello, user!" in captured.out

