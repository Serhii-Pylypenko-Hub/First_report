from colorama import init, Fore, Style

init(autoreset=True)

def print_colored(text: str, color: Fore):
    print(f"{color}{text}")

def print_title(text: str):
    print(f"{Fore.YELLOW}{Style.BRIGHT}{text}")
