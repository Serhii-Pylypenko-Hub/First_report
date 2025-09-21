# Bot/comands_file.py

from Bot.utils import print_colored
from Bot.Config.setting import USER_DATA_PATH
from colorama import Fore
import json
import os

def say_hello():
    print_colored("Hello, user! 🤝", Fore.GREEN)

def show_help():
    print_colored("Available commands:", Fore.BLUE)
    print("  hello       - Greet the assistant")
    print("  help        - Show this help message")
    print("  add [name]  - Add user to the database")
    print("  show        - Show all saved users")
    print("  exit        - Exit the assistant")

def add_user(name):
    if not name:
        print_colored("⚠ Please provide a name.", Fore.YELLOW)
        return

    users = []

    if os.path.exists(USER_DATA_PATH):
        with open(USER_DATA_PATH, "r", encoding="utf-8") as f:
            try:
                users = json.load(f)
            except json.JSONDecodeError:
                users = []

    users.append({"name": name})

    with open(USER_DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

    print_colored(f"✅ User '{name}' added!", Fore.GREEN)

def show_users():
    if not os.path.exists(USER_DATA_PATH):
        print_colored("🗂 No users found.", Fore.YELLOW)
        return

    with open(USER_DATA_PATH, "r", encoding="utf-8") as f:
        try:
            users = json.load(f)
        except json.JSONDecodeError:
            print_colored("❌ Could not read users.json", Fore.RED)
            return

    if not users:
        print_colored("🗂 No users saved yet.", Fore.YELLOW)
    else:
        print_colored("📋 Saved users:", Fore.CYAN)
        for i, user in enumerate(users, start=1):
            print(f"{i}. {user['name']}")
