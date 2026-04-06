DROP TABLE IF EXISTS loans;
DROP TABLE IF EXISTS readers;
DROP TABLE IF EXISTS books;
DROP TABLE IF EXISTS librarians;
DROP TABLE IF EXISTS statuses;

CREATE TABLE readers (
  id INTEGER PRIMARY KEY NOT NULL
    CHECK (id BETWEEN 1 AND 300),

  reader_card_number TEXT NOT NULL
    CHECK (length(reader_card_number) BETWEEN 1 AND 20),

  full_name TEXT NOT NULL
    CHECK (length(full_name) BETWEEN 5 AND 30),

  phone TEXT NULL
    CHECK (phone IS NULL OR length(phone) BETWEEN 0 AND 15),

  email TEXT NULL
    CHECK (email IS NULL OR length(email) BETWEEN 0 AND 30),

  UNIQUE(reader_card_number)
);

CREATE TABLE books (
  id INTEGER PRIMARY KEY NOT NULL
    CHECK (id BETWEEN 1 AND 2000),

  inventory_number TEXT NOT NULL
    CHECK (length(inventory_number) BETWEEN 1 AND 30),

  title TEXT NOT NULL
    CHECK (length(title) BETWEEN 5 AND 50),

  author TEXT NOT NULL
    CHECK (length(author) BETWEEN 5 AND 30),

  publish_year INTEGER NOT NULL
    CHECK (publish_year BETWEEN 1800 AND 2026),

  isbn TEXT NOT NULL
    CHECK (length(isbn) = 13),

  UNIQUE(inventory_number),
  UNIQUE(isbn)
);

CREATE TABLE librarians (
  id INTEGER PRIMARY KEY NOT NULL
    CHECK (id BETWEEN 1 AND 15),

  employee_number TEXT NOT NULL
    CHECK (length(employee_number) BETWEEN 1 AND 15),

  full_name TEXT NOT NULL
    CHECK (length(full_name) BETWEEN 5 AND 30),

  phone TEXT NULL
    CHECK (phone IS NULL OR length(phone) BETWEEN 0 AND 15),

  UNIQUE(employee_number)
);

-- ❗ фиксированный справочник
CREATE TABLE statuses (
  id INTEGER PRIMARY KEY NOT NULL
    CHECK (id BETWEEN 1 AND 3),

  title TEXT NOT NULL
    CHECK (length(title) BETWEEN 6 AND 15),

  UNIQUE(title)
);

CREATE TABLE loans (
  id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL
    CHECK (id BETWEEN 1 AND 2500),

  reader_id INTEGER NOT NULL
    REFERENCES readers(id) ON DELETE CASCADE,

  book_id INTEGER NOT NULL
    REFERENCES books(id) ON DELETE CASCADE,

  librarian_id INTEGER NOT NULL
    REFERENCES librarians(id) ON DELETE CASCADE,

  status_id INTEGER NOT NULL
    REFERENCES statuses(id) ON DELETE RESTRICT,

  issue_date TEXT NOT NULL
    CHECK (issue_date >= '2026-01-01'),

  due_date TEXT NOT NULL
    CHECK (due_date >= issue_date),

  return_date TEXT NULL
    CHECK (
      return_date IS NULL OR
      return_date >= issue_date
    ),

  CHECK ( (status_id = 2 AND return_date IS NOT NULL) OR (status_id <> 2) )
);

CREATE INDEX idx_readers_full_name ON readers(full_name);
CREATE INDEX idx_books_title ON books(title);
CREATE INDEX idx_loans_reader ON loans(reader_id);
CREATE INDEX idx_loans_book ON loans(book_id);
CREATE INDEX idx_loans_librarian ON loans(librarian_id);
CREATE INDEX idx_loans_issue_date ON loans(issue_date);