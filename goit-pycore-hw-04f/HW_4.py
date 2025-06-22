# Завдання 1

def total_salary(path):
    try:
        with open(path, "r", encoding="utf-8") as file:
            total = 0
            count = 0
            for line in file:
                line = line.strip()
                if not line:
                    continue  # Пропускаємо порожні рядки
                try:
                    _, salary = line.split(",")
                    total += int(salary)
                    count += 1
                except ValueError:
                    print(f"Некоректний рядок: {line}")
            if count == 0:
                return (0, 0)
            average = total // count
            return (total, average)
    except FileNotFoundError:
        print(f"Файл не знайдено: {path}")
        return (0, 0)
    except Exception as e:
        print(f"Помилка при обробці файлу: {e}")
        return (0, 0)

total, average = total_salary("D:\Projects\First_report\goit-pycore-hw-04\Salary.txt")
print(f"Загальна сума заробітної плати: {total}, Середня заробітна плата: {average}")

# Завдання 2

def get_cats_info(path):
    cats = []
    try:
        with open(path, "r", encoding="utf-8") as file:
            for line in file:
                parts = line.strip().split(",")
                if len(parts) == 3:
                    cat_id, name, age = parts
                    cats.append({
                        "id": cat_id,
                        "name": name,
                        "age": age
                    })
                else:
                    print(f"Пропущено некоректний рядок: {line.strip()}")
        return cats
    except FileNotFoundError:
        print(f"Файл не знайдено: {path}")
        return []
    except Exception as e:
        print(f"Помилка при читанні файлу: {e}")
        return []

cats_info = get_cats_info("D:\Projects\First_report\goit-pycore-hw-04\Cat.txt")
print(cats_info)



# Завдання 3

import sys
from pathlib import Path
from colorama import init, Fore, Style

# Ініціалізація colorama
init(autoreset=True)

def print_directory_tree(path: Path, prefix: str = ""):
    try:
        for item in sorted(path.iterdir()):
            if item.is_dir():
                print(f"{prefix}{Fore.BLUE}{item.name}/")
                print_directory_tree(item, prefix + "    ")
            else:
                print(f"{prefix}{Fore.GREEN}{item.name}")
    except PermissionError:
        print(f"{prefix}{Fore.RED}[Permission denied]")

def main():
    if len(sys.argv) < 2:
        print(f"{Fore.RED}❗️ Вкажіть шлях до директорії як аргумент командного рядка.")
        return

    dir_path = Path(sys.argv[1])

    if not dir_path.exists():
        print(f"{Fore.RED}❗️ Шлях не існує: {dir_path}")
        return

    if not dir_path.is_dir():
        print(f"{Fore.RED}❗️ Це не директорія: {dir_path}")
        return

    print(f"{Fore.YELLOW}📁 Структура директорії: {dir_path}\n")
    print_directory_tree(dir_path)

if __name__ == "__main__":
    main()



# Завдання 4

def parse_input(user_input):
    cmd, *args = user_input.strip().split()
    return cmd.lower(), args


def add_contact(args, contacts):
    if len(args) != 2:
        return "❗ Please use: add <name> <phone>"

    name, phone = args
    if not phone.isdigit():
        return "❗ Phone number must contain only digits."

    contacts[name] = phone
    return f"✅ Contact '{name}' added."


def show_all(contacts):
    if not contacts:
        return "📭 No contacts saved yet."
    return "\n".join([f"{name}: {phone}" for name, phone in contacts.items()])


def main():
    contacts = {}
    print("👋 Welcome to the assistant bot!")
    while True:
        user_input = input("📝 Enter a command: ")
        command, args = parse_input(user_input)

        if command in ["close", "exit"]:
            print("👋 Good bye!")
            break
        elif command == "hello":
            print("🤖 How can I help you?")
        elif command == "add":
            print(add_contact(args, contacts))
        elif command == "all":
            print(show_all(contacts))
        else:
            print("⚠️ Invalid command. Please try again.")


if __name__ == "__main__":
    main()


         



