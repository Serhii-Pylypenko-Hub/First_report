

# from datetime import datetime, timedelta
# from difflib import get_close_matches
# from colorama import Fore, Style, init
# import pickle
# import os
# import re

# init(autoreset=True)

# # === Класи полів ===
# class Field:
#     def __init__(self, value):
#         self.value = value
#     def __str__(self):
#         return str(self.value)

# class Name(Field):
#     def __init__(self, value):
#         formatted = value.strip().capitalize()
#         super().__init__(formatted)

# class LastName(Field):
#     def __init__(self, value):
#         formatted = value.strip().capitalize()
#         super().__init__(formatted)

# class Phone(Field):
#     def __init__(self, value):
#         if not value.isdigit() or len(value) != 10:
#             raise ValueError("Phone must be 10 digits")
#         super().__init__(value)

# class Email(Field):
#     def __init__(self, value):
#         pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
#         if not re.match(pattern, value):
#             raise ValueError("Invalid email format")
#         super().__init__(value)

# class Birthday(Field):
#     def __init__(self, value):
#         try:
#             datetime.strptime(value, "%d.%m.%Y")
#         except ValueError:
#             raise ValueError("Birthday must be in DD.MM.YYYY format")
#         super().__init__(value)

# class Note(Field):
#     def __init__(self, value):
#         super().__init__(value)

# class Tag(Field):
#     def __init__(self, value):
#         super().__init__(value)

# # === Клас Record — зберігає один контакт ===
# class Record:
#     def __init__(self, name: Name):
#         self.name = name
#         self.last_name = None
#         self.phones = []
#         self.emails = []
#         self.birthday = None
#         self.notes = []
#         self.tags = []

#     def add_phone(self, phone):
#         self.phones.append(Phone(phone))

#     def add_email(self, email):
#         self.emails.append(Email(email))

#     def add_birthday(self, bday):
#         self.birthday = Birthday(bday)

#     def add_note(self, note):
#         self.notes.append(Note(note))

#     def add_tag(self, tag):
#         self.tags.append(Tag(tag))

#     def days_to_birthday(self):
#         if not self.birthday:
#             return None
#         today = datetime.today().date()
#         bday = datetime.strptime(self.birthday.value, "%d.%m.%Y").date()
#         next_bday = bday.replace(year=today.year)
#         if next_bday < today:
#             next_bday = bday.replace(year=today.year + 1)
#         return (next_bday - today).days

# # === Клас AddressBook — зберігає всі контакти ===
# class AddressBook:
#     def __init__(self):
#         self.data = {}

#     def add_record(self, record):
#         self.data[record.name.value] = record

#     def get(self, name):
#         return self.data.get(name.capitalize())

#     def get_all(self):
#         return self.data.values()

#     def find(self, name):
#         return self.data.get(name.capitalize())

# # === Функції збереження / завантаження ===
# DATA_FILE = "contacts.pkl"

# def save_data(book):
#     with open(DATA_FILE, "wb") as f:
#         pickle.dump(book, f)

# def load_data():
#     if os.path.exists(DATA_FILE):
#         with open(DATA_FILE, "rb") as f:
#             return pickle.load(f)
#     return AddressBook()

# # === Вивід списку контактів ===
# def show_all(book):
#     if not book.data:
#         print("No contacts yet.")
#         return
#     print(f"{Style.BRIGHT}\n{Fore.YELLOW}{'First':<12}{'Last':<12}{'Phone':<15}{'Email':<25}{'Bday':<12}{'Note':<20}{'Tag':<15}")
#     print("-" * 110)
#     for rec in book.get_all():
#         print(f"{rec.name.value:<12}{(rec.last_name.value if rec.last_name else ''):<12}"
#               f"{(rec.phones[0].value if rec.phones else ''):<15}"
#               f"{(rec.emails[0].value if rec.emails else ''):<25}"
#               f"{(rec.birthday.value if rec.birthday else ''):<12}"
#               f"{(rec.notes[0].value if rec.notes else ''):<20}"
#               f"{(rec.tags[0].value if rec.tags else ''):<15}")
#     print_help()

# # === Показати дні народження наступних 7 днів ===
# def birthdays(book):
#     today = datetime.today().date()
#     next_7 = today + timedelta(days=7)
#     found = False
#     for rec in book.get_all():
#         if rec.birthday:
#             bday = datetime.strptime(rec.birthday.value, "%d.%m.%Y").date()
#             bday_this_year = bday.replace(year=today.year)
#             if today <= bday_this_year <= next_7:
#                 print(f"{rec.name.value}: {rec.birthday.value}")
#                 found = True
#     if not found:
#         print("No upcoming birthdays in the next 7 days.")
#     print_help()

# # === Показати допомогу ===
# def print_help():
#     print(f"""
# {Fore.YELLOW}Available commands:{Style.RESET_ALL}
#   add           - Add contact interactively
#   add-phone     - Add a phone (to existing contact or new)
#   add-email     - Add an email (to existing contact or new)
#   add-birthday  - Add birthday to contact
#   note          - Add note (one-time or attach to contact)
#   search-note   - Search notes by tag or keyword
#   change        - Edit contact details (interactive)
#   all           - Show all contacts
#   birthdays     - Show next 7 days birthdays
#   help          - Show this help
#   exit / close  - Exit and save
# """)

# # === Підказка yes/no з підтримкою y/n незалежно від регістру ===
# def ask_yes_no(prompt):
#     while True:
#         ans = input(prompt).strip().lower()
#         if ans in ("y", "yes"):
#             return True
#         elif ans in ("n", "no"):
#             return False
#         else:
#             print("Please enter 'y' or 'n'.")

# # === Функції додавання різних даних ===
# def add_phones(record):
#     while True:
#         phone = input("Enter phone (10 digits): ").strip()
#         try:
#             record.add_phone(phone)
#         except Exception as e:
#             print(f"{Fore.RED}Invalid phone. {e}")
#             continue
#         if not ask_yes_no("Add another phone? (y/n): "):
#             break

# def add_emails(record):
#     while True:
#         email = input("Enter email (example@domain.com): ").strip()
#         try:
#             record.add_email(email)
#         except Exception as e:
#             print(f"{Fore.RED}Invalid email. {e}")
#             continue
#         if not ask_yes_no("Add another email? (y/n): "):
#             break

# def add_birthday(record):
#     while True:
#         bday = input("Enter birthday (DD.MM.YYYY): ").strip()
#         try:
#             record.add_birthday(bday)
#             break
#         except Exception as e:
#             print(f"{Fore.RED}Invalid birthday. {e}")

# def add_notes(record):
#     while True:
#         note = input("Enter note text: ").strip()
#         if note:
#             record.add_note(note)
#         if not ask_yes_no("Add another note? (y/n): "):
#             break

# def add_tags(record):
#     while True:
#         tag = input("Enter tag: ").strip()
#         if tag:
#             record.add_tag(tag)
#         if not ask_yes_no("Add another tag? (y/n): "):
#             break

# # === Діалог додавання контакту повністю ===
# def cmd_add(book):
#     while True:
#         name = input("Enter first name (required): ").strip()
#         if name:
#             break
#         else:
#             print(f"{Fore.RED}First name is required.")
#     record = Record(Name(name))

#     last = input("Enter last name (optional): ").strip()
#     if last:
#         record.last_name = LastName(last)

#     print("Add phones:")
#     add_phones(record)

#     print("Add emails:")
#     add_emails(record)

#     print("Add birthday:")
#     add_birthday(record)

#     print("Add notes:")
#     add_notes(record)

#     print("Add tags:")
#     add_tags(record)

#     book.add_record(record)
#     print(f"{Fore.GREEN}Contact '{name}' added successfully.")
#     print_help()

# # === Діалог додавання телефону ===
# def cmd_add_phone(book):
#     name = select_contact(book, "Enter contact name to add phone: ")
#     if not name:
#         return
#     record = book.get(name)
#     print("Add phones:")
#     add_phones(record)
#     print_help()

# # === Діалог додавання емейлу ===
# def cmd_add_email(book):
#     name = select_contact(book, "Enter contact name to add email: ")
#     if not name:
#         return
#     record = book.get(name)
#     print("Add emails:")
#     add_emails(record)
#     print_help()

# # === Діалог додавання дня народження ===
# def cmd_add_birthday(book):
#     name = select_contact(book, "Enter contact name to add birthday: ")
#     if not name:
#         return
#     record = book.get(name)
#     print("Add birthday:")
#     add_birthday(record)
#     print_help()

# # === Діалог додавання нотатки ===
# def cmd_note(book):
#     print("1) One-time note\n2) Attach to contact")
#     mode = input("Select option: ").strip()
#     if mode == "1":
#         note = input("Enter note text: ").strip()
#         tag = input("Enter tag(s), comma separated: ").strip()
#         temp = Record(Name("Note"))
#         temp.add_note(note)
#         if tag:
#             for t in tag.split(","):
#                 temp.add_tag(t.strip())
#         book.add_record(temp)
#         print(f"{Fore.GREEN}Note saved.")
#     elif mode == "2":
#         name = select_contact(book, "Enter contact name to attach note: ")
#         if not name:
#             return
#         rec = book.get(name)
#         note = input("Enter note text: ").strip()
#         tag = input("Enter tag(s), comma separated: ").strip()
#         rec.add_note(note)
#         if tag:
#             for t in tag.split(","):
#                 rec.add_tag(t.strip())
#         print(f"{Fore.GREEN}Note added to {name}.")
#     else:
#         print("Invalid option.")
#     print_help()

# # === Функція вибору контакту зі списку за частиною імені ===
# def select_contact(book, prompt):
#     while True:
#         part = input(prompt).strip().capitalize()
#         matches = [name for name in book.data if part in name]
#         if not matches:
#             print(f"No contact found containing '{part}'.")
#             continue
#         if len(matches) == 1:
#             return matches[0]
#         print("Multiple matches found:")
#         for i, name in enumerate(matches, 1):
#             print(f"{i}. {name}")
#         while True:
#             choice = input("Select number: ").strip()
#             if choice.isdigit() and 1 <= int(choice) <= len(matches):
#                 return matches[int(choice) - 1]
#             print("Invalid choice. Enter a number from the list.")

# # === Діалог зміни даних контакту ===
# def cmd_change(book):
#     name = select_contact(book, "Enter contact name to change: ")
#     if not name:
#         return
#     record = book.get(name)
#     print("Fields to change:")
#     fields = ["First name", "Last name", "Phone", "Email", "Birthday", "Note", "Tag"]
#     for i, f in enumerate(fields, 1):
#         print(f"{i}. {f}")
#     while True:
#         choice = input("Select field number to change: ").strip()
#         if not choice.isdigit() or not 1 <= int(choice) <= len(fields):
#             print("Invalid choice.")
#             continue
#         field = fields[int(choice) - 1]
#         old_val = ""
#         if field == "First name":
#             old_val = record.name.value
#             new_val = input(f"Enter new first name (old: {old_val}): ").strip()
#             if new_val:
#                 record.name = Name(new_val)
#         elif field == "Last name":
#             old_val = record.last_name.value if record.last_name else ""
#             new_val = input(f"Enter new last name (old: {old_val}): ").strip()
#             if new_val:
#                 record.last_name = LastName(new_val)
#         elif field == "Phone":
#             if not record.phones:
#                 print("No phones to change.")
#             else:
#                 for i, p in enumerate(record.phones, 1):
#                     print(f"{i}. {p.value}")
#                 p_choice = input("Select phone number to change: ").strip()
#                 if p_choice.isdigit() and 1 <= int(p_choice) <= len(record.phones):
#                     new_phone = input(f"Enter new phone (old: {record.phones[int(p_choice) - 1].value}): ").strip()
#                     try:
#                         record.phones[int(p_choice) - 1] = Phone(new_phone)
#                     except Exception as e:
#                         print(f"Error: {e}")
#                 else:
#                     print("Invalid choice.")
#         elif field == "Email":
#             if not record.emails:
#                 print("No emails to change.")
#             else:
#                 for i, e in enumerate(record.emails, 1):
#                     print(f"{i}. {e.value}")
#                 e_choice = input("Select email number to change: ").strip()
#                 if e_choice.isdigit() and 1 <= int(e_choice) <= len(record.emails):
#                     new_email = input(f"Enter new email (old: {record.emails[int(e_choice) - 1].value}): ").strip()
#                     try:
#                         record.emails[int(e_choice) - 1] = Email(new_email)
#                     except Exception as e:
#                         print(f"Error: {e}")
#                 else:
#                     print("Invalid choice.")
#         elif field == "Birthday":
#             old_val = record.birthday.value if record.birthday else ""
#             new_val = input(f"Enter new birthday (DD.MM.YYYY) (old: {old_val}): ").strip()
#             try:
#                 record.birthday = Birthday(new_val)
#             except Exception as e:
#                 print(f"Error: {e}")
#         elif field == "Note":
#             if not record.notes:
#                 print("No notes to change.")
#             else:
#                 for i, n in enumerate(record.notes, 1):
#                     print(f"{i}. {n.value}")
#                 n_choice = input("Select note number to change: ").strip()
#                 if n_choice.isdigit() and 1 <= int(n_choice) <= len(record.notes):
#                     new_note = input(f"Enter new note (old: {record.notes[int(n_choice) - 1].value}): ").strip()
#                     record.notes[int(n_choice) - 1] = Note(new_note)
#                 else:
#                     print("Invalid choice.")
#         elif field == "Tag":
#             if not record.tags:
#                 print("No tags to change.")
#             else:
#                 for i, t in enumerate(record.tags, 1):
#                     print(f"{i}. {t.value}")
#                 t_choice = input("Select tag number to change: ").strip()
#                 if t_choice.isdigit() and 1 <= int(t_choice) <= len(record.tags):
#                     new_tag = input(f"Enter new tag (old: {record.tags[int(t_choice) - 1].value}): ").strip()
#                     record.tags[int(t_choice) - 1] = Tag(new_tag)
#                 else:
#                     print("Invalid choice.")
#         else:
#             print("Invalid field.")
#             continue

#         print(f"{Fore.GREEN}Field '{field}' updated.")
#         print_help()
#         break

# # === Основна функція ===
# def main():
#     book = load_data()
#     print_help()

#     while True:
#         command = input(f"\n{Fore.CYAN}Enter command: {Style.RESET_ALL}").strip().lower()

#         if command in ("exit", "close"):
#             save_data(book)
#             print(f"{Fore.CYAN}Goodbye!")
#             break

#         elif command == "add":
#             cmd_add(book)

#         elif command == "add-phone":
#             cmd_add_phone(book)

#         elif command == "add-email":
#             cmd_add_email(book)

#         elif command == "add-birthday":
#             cmd_add_birthday(book)

#         elif command == "note":
#             cmd_note(book)

#         elif command == "search-note":
#             tag = input("Enter tag to search: ").strip()
#             found = False
#             for rec in book.get_all():
#                 for t in rec.tags:
#                     if tag.lower() in t.value.lower():
#                         print(f"{rec.name.value}: {', '.join(n.value for n in rec.notes)}")
#                         found = True
#             if not found:
#                 print("No notes found with this tag.")
#             print_help()

#         elif command == "birthdays":
#             birthdays(book)

#         elif command == "all":
#             show_all(book)

#         elif command == "change":
#             cmd_change(book)

#         elif command == "help":
#             print_help()

#         else:
#             matches = get_close_matches(command, ["add", "add-phone", "add-email", "add-birthday", "note", "search-note", "all", "birthdays", "change", "help", "exit", "close"])
#             if matches:
#                 print(f"Unknown command. Did you mean '{matches[0]}'?")
#             else:
#                 print("Unknown command. Type 'help'.")

# if __name__ == "__main__":
#     main()

from datetime import datetime, timedelta
from difflib import get_close_matches
from colorama import Fore, Style, init
import pickle
import os

init(autoreset=True)

# === Класи полів ===
class Field:
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return str(self.value)

class Name(Field):
    def __init__(self, value):
        formatted = value.strip().capitalize()
        super().__init__(formatted)

class LastName(Field):
    def __init__(self, value):
        formatted = value.strip().capitalize()
        super().__init__(formatted)

class Phone(Field):
    def __init__(self, value):
        if not value.isdigit() or len(value) != 10:
            raise ValueError("Phone must be 10 digits")
        super().__init__(value)

class Email(Field):
    def __init__(self, value):
        if "@" not in value:
            raise ValueError("Invalid email format")
        super().__init__(value)

class Birthday(Field):
    def __init__(self, value):
        try:
            datetime.strptime(value, "%d.%m.%Y")
        except ValueError:
            raise ValueError("Birthday must be in DD.MM.YYYY format")
        super().__init__(value)

class Note(Field):
    pass

class Tag(Field):
    pass

# === Клас Record — зберігає один контакт ===
class Record:
    def __init__(self, name: Name):
        self.name = name
        self.last_name = None
        self.phones = []
        self.emails = []
        self.birthday = None
        self.notes = []
        self.tags = []

    def add_phone(self, phone):
        self.phones.append(Phone(phone))

    def add_email(self, email):
        self.emails.append(Email(email))

    def add_birthday(self, bday):
        self.birthday = Birthday(bday)

    def add_note(self, note):
        self.notes.append(Note(note))

    def add_tag(self, tag):
        self.tags.append(Tag(tag))

    def days_to_birthday(self):
        if not self.birthday:
            return None
        today = datetime.today().date()
        bday = datetime.strptime(self.birthday.value, "%d.%m.%Y").date()
        next_bday = bday.replace(year=today.year)
        if next_bday < today:
            next_bday = bday.replace(year=today.year + 1)
        return (next_bday - today).days

# === Клас AddressBook — зберігає всі контакти ===
class AddressBook:
    def __init__(self):
        self.data = {}

    def add_record(self, record):
        self.data[record.name.value] = record

    def get(self, name):
        return self.data.get(name.capitalize())

    def get_all(self):
        return self.data.values()

    def find(self, name):
        return self.data.get(name.capitalize())

# === Функції збереження / завантаження ===
DATA_FILE = "contacts.pkl"

def save_data(book):
    with open(DATA_FILE, "wb") as f:
        pickle.dump(book, f)

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "rb") as f:
            return pickle.load(f)
    return AddressBook()

# === Функції додавання з перевіркою ===
def yes_no_prompt(message):
    while True:
        ans = input(message).strip().lower()
        if ans in ("y", "yes"):
            return True
        elif ans in ("n", "no"):
            return False
        else:
            print("Please enter 'y' or 'n'.")

def add_phones(record):
    while True:
        phone = input("Enter phone (10 digits): ").strip()
        try:
            record.add_phone(phone)
        except Exception as e:
            print(f"{Fore.RED}Invalid phone. {e}")
            continue
        if not yes_no_prompt("Add another phone? (y/n): "):
            break

def add_emails(record):
    while True:
        email = input("Enter email (example@domain.com): ").strip()
        try:
            record.add_email(email)
        except Exception as e:
            print(f"{Fore.RED}Invalid email. {e}")
            continue
        if not yes_no_prompt("Add another email? (y/n): "):
            break

def add_notes(record):
    while True:
        note = input("Enter note text: ").strip()
        if note:
            record.add_note(note)
        if not yes_no_prompt("Add another note? (y/n): "):
            break

def add_tags(record):
    while True:
        tag = input("Enter tag: ").strip()
        if tag:
            record.add_tag(tag)
        if not yes_no_prompt("Add another tag? (y/n): "):
            break

# === Вивід списку контактів ===
def show_all(book):
    if not book.data:
        print("No contacts yet.")
        return
    print(f"{Style.BRIGHT}\n{Fore.YELLOW}{'First':<12}{'Last':<12}{'Phone':<15}{'Email':<25}{'Bday':<12}{'Note':<20}{'Tag':<15}")
    print("-" * 110)
    for rec in book.get_all():
        phones = "\n".join(p.value for p in rec.phones)
        emails = "\n".join(e.value for e in rec.emails)
        notes = "\n".join(n.value for n in rec.notes)
        tags = "\n".join(t.value for t in rec.tags)
        print(f"{rec.name.value:<12}{(rec.last_name.value if rec.last_name else ''):<12}"
              f"{phones:<15}{emails:<25}"
              f"{(rec.birthday.value if rec.birthday else ''):<12}"
              f"{notes:<20}{tags:<15}")

# === Вивід днів народжень наступних 7 днів ===
def birthdays(book):
    today = datetime.today().date()
    next_7 = today + timedelta(days=7)
    found = False
    for rec in book.get_all():
        if rec.birthday:
            bday = datetime.strptime(rec.birthday.value, "%d.%m.%Y").date()
            bday_this_year = bday.replace(year=today.year)
            if today <= bday_this_year <= next_7:
                print(f"{rec.name.value}: {rec.birthday.value}")
                found = True
    if not found:
        print("No upcoming birthdays in the next 7 days.")

# === Вивід допомоги ===
def print_help():
    print(f"""
{Fore.YELLOW}Available commands:{Style.RESET_ALL}
  add           - Add contact interactively
  add-phone     - Add a phone (to existing contact or new)
  add-email     - Add an email (to existing contact or new)
  add-birthday  - Add birthday to contact
  note          - Add note (one-time or attach to contact)
  search-note   - Search notes by tag or keyword
  change        - Edit contact details (interactive)
  all           - Show all contacts
  birthdays     - Show next 7 days birthdays
  help          - Show this help
  exit / close  - Exit and save
""")

# === Знайти контакт і запропонувати вибір при кількох співпадіннях ===
def find_contact_interactive(book, name):
    name_lower = name.lower()
    matches = [rec for rec in book.get_all() if rec.name.value.lower() == name_lower or (rec.last_name and rec.last_name.value.lower() == name_lower)]
    if not matches:
        return None
    if len(matches) == 1:
        return matches[0]

    print("Multiple contacts found with that name:")
    for idx, rec in enumerate(matches, 1):
        print(f"{idx}. {rec.name.value} {(rec.last_name.value if rec.last_name else '')}")
    while True:
        choice = input(f"Select number (1-{len(matches)}): ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(matches):
            return matches[int(choice) - 1]
        print(f"Please enter a number between 1 and {len(matches)}.")

# === Редагування контакту ===
def cmd_change(book):
    name = input("Enter name to change: ").strip().capitalize()
    record = find_contact_interactive(book, name)
    if not record:
        print(f"{Fore.RED}No contact found with this name.")
        return
    print(f"Editing contact: {record.name.value} {(record.last_name.value if record.last_name else '')}")
    fields = ["first name", "last name", "phone", "email", "birthday", "note", "tag"]
    while True:
        print("Fields:", ", ".join(fields))
        field = input("Enter field to change (or 'exit' to quit): ").strip().lower()
        if field == "exit":
            break
        if field not in fields:
            print("Unknown field. Try again.")
            continue
        if field == "first name":
            new_val = input(f"Enter new first name (current: {record.name.value}): ").strip()
            if new_val:
                record.name = Name(new_val)
        elif field == "last name":
            new_val = input(f"Enter new last name (current: {(record.last_name.value if record.last_name else '')}): ").strip()
            if new_val:
                record.last_name = LastName(new_val)
        elif field == "phone":
            if not record.phones:
                print("No phones to edit.")
            else:
                for i, p in enumerate(record.phones, 1):
                    print(f"{i}. {p.value}")
                idx = input("Enter phone number to edit (number): ").strip()
                if idx.isdigit() and 1 <= int(idx) <= len(record.phones):
                    new_val = input(f"Enter new phone (current: {record.phones[int(idx)-1].value}): ").strip()
                    try:
                        record.phones[int(idx)-1] = Phone(new_val)
                    except Exception as e:
                        print(f"{Fore.RED}Invalid phone. {e}")
                else:
                    print("Invalid selection.")
        elif field == "email":
            if not record.emails:
                print("No emails to edit.")
            else:
                for i, e in enumerate(record.emails, 1):
                    print(f"{i}. {e.value}")
                idx = input("Enter email number to edit (number): ").strip()
                if idx.isdigit() and 1 <= int(idx) <= len(record.emails):
                    new_val = input(f"Enter new email (current: {record.emails[int(idx)-1].value}): ").strip()
                    try:
                        record.emails[int(idx)-1] = Email(new_val)
                    except Exception as e:
                        print(f"{Fore.RED}Invalid email. {e}")
                else:
                    print("Invalid selection.")
        elif field == "birthday":
            new_val = input(f"Enter new birthday (DD.MM.YYYY) (current: {(record.birthday.value if record.birthday else '')}): ").strip()
            try:
                record.add_birthday(new_val)
            except Exception as e:
                print(f"{Fore.RED}Invalid birthday. {e}")
        elif field == "note":
            if not record.notes:
                print("No notes to edit.")
            else:
                for i, n in enumerate(record.notes, 1):
                    print(f"{i}. {n.value}")
                idx = input("Enter note number to edit (number): ").strip()
                if idx.isdigit() and 1 <= int(idx) <= len(record.notes):
                    new_val = input(f"Enter new note (current: {record.notes[int(idx)-1].value}): ").strip()
                    if new_val:
                        record.notes[int(idx)-1] = Note(new_val)
                else:
                    print("Invalid selection.")
        elif field == "tag":
            if not record.tags:
                print("No tags to edit.")
            else:
                for i, t in enumerate(record.tags, 1):
                    print(f"{i}. {t.value}")
                idx = input("Enter tag number to edit (number): ").strip()
                if idx.isdigit() and 1 <= int(idx) <= len(record.tags):
                    new_val = input(f"Enter new tag (current: {record.tags[int(idx)-1].value}): ").strip()
                    if new_val:
                        record.tags[int(idx)-1] = Tag(new_val)
                else:
                    print("Invalid selection.")

# === Додавання контакту (інтерактивно) ===
def cmd_add(book):
    while True:
        name = input("Enter first name (required): ").strip()
        if name:
            break
        print("First name is required.")
    record = Record(Name(name))
    last = input("Enter last name (optional): ").strip()
    if last:
        record.last_name = LastName(last)

    print("Add phones:")
    add_phones(record)
    print("Add emails:")
    add_emails(record)
    print("Add birthday:")
    while True:
        bday = input("Enter birthday (DD.MM.YYYY) or leave empty to skip: ").strip()
        if not bday:
            break
        try:
            record.add_birthday(bday)
            break
        except Exception as e:
            print(f"{Fore.RED}Invalid birthday. {e}")

    print("Add notes:")
    add_notes(record)
    print("Add tags:")
    add_tags(record)

    book.add_record(record)
    print(f"{Fore.GREEN}Contact '{record.name.value}' added successfully.")

# === Основна функція ===
def main():
    book = load_data()
    print_help()

    while True:
        command = input(f"\nEnter command: ").strip().lower()
        if command in ("exit", "close"):
            save_data(book)
            print(f"{Fore.CYAN}Goodbye!")
            break
        elif command == "add":
            cmd_add(book)
            print_help()
        elif command == "change":
            cmd_change(book)
            print_help()
        elif command == "all":
            show_all(book)
        elif command == "birthdays":
            birthdays(book)
            print_help()
        elif command == "help":
            print_help()
        else:
            matches = get_close_matches(command, ["add", "change", "all", "birthdays", "help"])
            if matches:
                print(f"Unknown command. Did you mean '{matches[0]}'?")
            else:
                print("Unknown command. Type 'help'.")

if __name__ == "__main__":
    main()
