from __future__ import annotations

import os
import sqlite3
from datetime import date, timedelta
import random

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(ROOT, "data")
SCHEMA_PATH = os.path.join(ROOT, "schema.sql")

DBS = {
    "Access": os.path.join(DATA_DIR, "library_access.sqlite3"),
    "Postgres": os.path.join(DATA_DIR, "library_postgres.sqlite3"),
}

STATUSES = [
    (1, "выдано"),
    (2, "возвращено"),
    (3, "просрочка"),
]

# --- ИМЕНА ---
MALE_NAMES = [
    "Иван Иванов", "Алексей Смирнов", "Дмитрий Кузнецов", "Сергей Попов",
    "Андрей Васильев", "Николай Соколов", "Павел Михайлов", "Евгений Фёдоров",
    "Владимир Никитин", "Константин Орлов", "Максим Захаров", "Юрий Белов", "Олег Тарасов",
    "Роман Гусев", "Виктор Крылов", "Игорь Лебедев", "Артур Егоров", "Георгий Макаров", "Степан Дорофеев"
]

FEMALE_NAMES = [
    "Анна Иванова", "Мария Смирнова", "Елена Кузнецова", "Ольга Попова",
    "Татьяна Морозова", "Наталья Волкова", "Ирина Павлова",
    "Светлана Алексеевна", "Дарья Романова", "Ксения Орлова", "Юлия Николаева"
]

ALL_NAMES = MALE_NAMES + FEMALE_NAMES
random.shuffle(ALL_NAMES)  # перемешиваем один раз для уникальной раздачи

LIBRARIAN_NAMES = [
    "Валерий Жуков", "Станислав Киселёв", "Григорий Исаев", "Леонид Зайцев",
    "Руслан Сафонов", "Вячеслав Корнилов", "Аркадий Фролов", "Борис Громов",
    "Людмила Сергеева", "Вера Андреева"
]

# --- КНИГИ ---
BOOKS = [
    ("Война и мир", "Лев Толстой"),
    ("Преступление и наказание", "Фёдор Достоевский"),
    ("Мастер и Маргарита", "Михаил Булгаков"),
    ("Анна Каренина", "Лев Толстой"),
    ("Идиот роман", "Фёдор Достоевский"),
    ("Отцы и дети", "Иван Тургенев"),
    ("Евгений Онегин", "Александр Пушкин"),
    ("Герой нашего времени", "Михаил Лермонтов"),
    ("Доктор Живаго", "Борис Пастернак"),
    ("Тихий Дон", "Михаил Шолохов"),
    ("Роман 1984", "Джордж Оруэлл"),
    ("Скотный двор", "Джордж Оруэлл"),
    ("Улисс роман", "Джеймс Джойс"),
    ("Великий Гэтсби", "Фрэнсис Скотт Фицджеральд"),
    ("Над пропастью во ржи", "Джером Сэлинджер"),
    ("451 градус по Фаренгейту", "Рэй Брэдбери"),
    ("О дивный новый мир", "Олдос Хаксли"),
    ("Моби Дик роман", "Герман Мелвилл"),
    ("Гамлет трагедия", "Уильям Шекспир"),
    ("Король Лир трагедия", "Уильям Шекспир"),
    ("Фауст поэма", "Иоганн Гёте"),
    ("Дон Кихот роман", "Мигель де Сервантес"),
    ("Сто лет одиночества", "Габриэль Гарсиа Маркес"),
    ("Имя розы", "Умберто Эко"),
    ("Парфюмер история", "Патрик Зюскинд"),
    ("Алхимик роман", "Пауло Коэльо"),
    ("Шантарам роман", "Грегори Дэвид Робертс"),
    ("Атлант расправил плечи", "Айн Рэнд"),
    ("Игра престолов книга", "Джордж Мартин"),
    ("Гарри Поттер философский камень", "Джоан Роулинг"),
]


def read_schema() -> str:
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return f.read()


def ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)


def random_phone():
    return "+7" + "".join(str(random.randint(0, 9)) for _ in range(10))


def make_reader(i: int, salt: int):
    card = f"RC{salt:02d}-{i:04d}"
    full_name = ALL_NAMES[i - 1]  # гарантированно уникально
    phone = None if i % 4 == 0 else random_phone()
    email = None if i % 5 == 0 else f"r{i:02d}@mail.ru"
    return (card, full_name, phone, email)


def make_book(i: int, salt: int):
    inv = f"INV{salt:02d}-{i:04d}"
    title, author = BOOKS[i - 1]
    year = random.randint(1950, 2024)
    isbn = "".join(str(random.randint(0, 9)) for _ in range(13))
    return (inv, title, author, year, isbn)


def make_librarian(i: int, salt: int):
    emp = f"EMP{salt:02d}{i:02d}"
    full_name = LIBRARIAN_NAMES[i - 1]  # уникальные ФИО для библиотекарей
    phone = None if i % 3 == 0 else random_phone()
    return (emp, full_name, phone)


def random_date_between(start: date, end: date) -> date:
    days = (end - start).days
    return start + timedelta(days=random.randint(0, max(days, 0)))


def seed_one(db_path: str, salt: int):
    if os.path.exists(db_path):
        os.remove(db_path)

    schema = read_schema()
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON;")

    con.executescript(schema)

    con.executemany("INSERT INTO statuses(id, title) VALUES (?, ?);", STATUSES)

    for i in range(1, 11):
        emp, full_name, phone = make_librarian(i, salt)
        con.execute(
            "INSERT INTO librarians(id, employee_number, full_name, phone) VALUES (?, ?, ?, ?);",
            (i, emp, full_name, phone)
        )

    readers = [make_reader(i, salt) for i in range(1, 31)]
    books = [make_book(i, salt) for i in range(1, 31)]

    con.executemany(
        "INSERT INTO readers(reader_card_number, full_name, phone, email) VALUES (?, ?, ?, ?);",
        readers,
    )
    con.executemany(
        "INSERT INTO books(inventory_number, title, author, publish_year, isbn) VALUES (?, ?, ?, ?, ?);",
        books,
    )

    today = date.today()
    start = date(2026, 1, 1)

    for i in range(1, 31):
        reader_id = i
        book_id = i
        librarian_id = 1 + (i % 10)

        issue = random_date_between(start, today)
        due = min(issue + timedelta(days=14), today)

        if i % 3 == 0:
            status_id = 2
            return_date = min(due, today).isoformat()
        elif i % 5 == 0:
            status_id = 3
            return_date = None
        else:
            status_id = 1
            return_date = None

        con.execute(
            """
            INSERT INTO loans(
              reader_id, book_id, librarian_id, status_id,
              issue_date, due_date, return_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?);
            """,
            (reader_id, book_id, librarian_id, status_id,
             issue.isoformat(), due.isoformat(), return_date)
        )

    con.commit()
    con.close()


def main():
    ensure_dirs()
    seed_one(DBS["Access"], salt=10)
    seed_one(DBS["Postgres"], salt=20)
    print("OK: seeded Access and Postgres DBs")


if __name__ == "__main__":
    main()
