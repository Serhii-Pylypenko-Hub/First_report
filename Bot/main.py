# Bot/main.py

from Bot.comands_file import say_hello, show_help, add_user, show_users
from Bot.utils import print_title

def main():
    print_title("🤖 Welcome to TechBees Assistant!")
    show_help()  # ← одразу показати перелік команд

    while True:
        command = input("\n>> ").strip().lower()

        if command == "hello":
            say_hello()
        elif command == "help":
            show_help()
        elif command.startswith("add "):
            name = command[4:].strip()
            add_user(name)
        elif command == "show":
            show_users()
        elif command in ["exit", "quit"]:
            print("👋 Goodbye!")
            break
        else:
            print("❗ Unknown command. Type 'help' to see all available commands.")

if __name__ == "__main__":
    main()
