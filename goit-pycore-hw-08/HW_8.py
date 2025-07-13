import pickle
import os 
from collections import UserDict
from datetime import datetime, timedelta

class Field:
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return str(self.value)

class Name(Field):
    def __init__(self, value: str):
        if not isinstance(value, str):
            raise ValueError("Name must be a string")
        # Забираємо зайві пробіли й робимо першу літеру великою
        formatted = value.strip().capitalize()
        super().__init__(formatted)

class Phone(Field):
    def __init__(self, value):
        if not isinstance(value, str):
            raise ValueError("Phone number must be a string of 10 digits")
        if len(value) != 10 or not value.isdigit():
            raise ValueError("Phone number must be a string of 10 digits")
        super().__init__(value)

class Birthday(Field):
    def __init__(self, value: str):
        try:
            date_obj = datetime.strptime(value, "%d.%m.%Y").date()
        except ValueError:
            raise ValueError("Invalid date format. Use DD.MM.YYYY")
        super().__init__(date_obj)



class Record:
    def __init__(self, name):
        self.name = Name(name)
        self.phones = []
        self.birthday = None

    def add_phone(self, phone):
        self.phones.append(Phone(phone))

    def remove_phone(self, phone):
        self.phones = [p for p in self.phones if p.value != phone]

    def edit_phone(self, old_phone, new_phone):
        for idx, p in enumerate(self.phones):
            if p.value == old_phone:
                self.phones[idx] = Phone(new_phone)
                return True
        return False

    def find_phone(self, phone):
        for p in self.phones:
            if p.value == phone:
                return p
        return None

    def add_birthday(self, birthday):
        self.birthday = Birthday(birthday)

    def __str__(self):
        phones = '; '.join(p.value for p in self.phones)
        birthday = f", birthday: {self.birthday.value.strftime('%d.%m.%Y')}" if self.birthday else ""
        return f"Contact name: {self.name.value}, phones: {phones}{birthday}"

class AddressBook(UserDict):
    def add_record(self, record: Record):
        self.data[record.name.value] = record

    def find(self, name):
        return self.data.get(name)

    def delete(self, name):
        if name in self.data:
            del self.data[name]


    def get_upcoming_birthdays(self):
        today = datetime.today().date()
        next_week = today + timedelta(days=7)
        greetings = []

        for record in self.data.values():
            if not record.birthday:
                continue

            bday_this_year = record.birthday.value.replace(year=today.year)

            if today <= bday_this_year <= next_week:
                weekday = bday_this_year.weekday()
                if weekday >= 5:  # Saturday or Sunday
                    congrat_day = bday_this_year + timedelta(days=(7 - weekday))
                else:
                    congrat_day = bday_this_year

                greetings.append({
                    "name": record.name.value,
                    "congratulations_date": congrat_day.strftime("%Y-%m-%d")
                })

        return greetings

def input_error(func):   
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (ValueError, IndexError) as e:
            return f"❌ Error: {e}"
    return wrapper

def save_data(book, filename="addressbook.pkl"):
    with open(filename, "wb") as f:
        pickle.dump(book, f)

def load_data(filename="addressbook.pkl"):
    if os.path.exists(filename):
        with open(filename, "rb") as f:
            return pickle.load(f)
    return AddressBook()

def input_error(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (ValueError, IndexError) as e:
            return f"❌ Error: {e}"
    return wrapper

@input_error
def add_contact(args, book):
    name, phone, *_ = args
    record = book.find(name)
    message = "Contact updated."
    if record is None:
        record = Record(name)
        book.add_record(record)
        message = "Contact added."
    if phone:
        record.add_phone(phone)
    return message

@input_error
def change_contact(args, book):
    name, old_phone, new_phone = args
    record = book.find(name)
    if record and record.edit_phone(old_phone, new_phone):
        return "Phone number updated."
    return "Contact or phone number not found."

@input_error
def get_phones(args, book):
    name = args[0]
    record = book.find(name)
    if record:
        return '; '.join(p.value for p in record.phones)
    return "Contact not found."

@input_error
def show_all(args, book):
    return '\n'.join(str(record) for record in book.data.values()) or "No contacts yet."

@input_error
def add_birthday(args, book):   
    name, date = args
    record = book.find(name)
    if record:
        record.add_birthday(date)
        return "Birthday added."
    return "Contact not found."

@input_error
def show_birthday(args, book): 
    name = args[0]
    record = book.find(name)
    if record and record.birthday:
        return record.birthday.value.strftime("%d.%m.%Y")
    return "Birthday not found."

@input_error
def birthdays(args, book):    
    return '\n'.join(f"{b['name']}: {b['congratulations_date']}" for b in book.get_upcoming_birthdays()) or "No birthdays next week."

# ==== PARSER ====
def parse_input(user_input):
    parts = user_input.strip().split()
    return parts[0].lower(), parts[1:]

# ==== MAIN LOOP ====
def main():
    book = load_data()
    print("Welcome to the assistant bot!")
    while True:
        user_input = input("Enter a command: ")
        command, args = parse_input(user_input)

        if command in ["close", "exit"]:
            save_data(book)
            print("Good bye!")
            break
        elif command == "hello":
            print("How can I help you?")
        elif command == "add":
            print(add_contact(args, book))
        elif command == "change":
            print(change_contact(args, book))
        elif command == "phone":
            print(get_phones(args, book))
        elif command == "all":
            print(show_all(args, book))
        elif command == "add-birthday":     
            print(add_birthday(args, book))
        elif command == "show-birthday":    
            print(show_birthday(args, book))
        elif command == "birthdays":        
            print(birthdays(args, book))
        else:
            print("Invalid command.")

if __name__ == "__main__":
    main()


