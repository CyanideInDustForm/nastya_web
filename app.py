# app.py
from __future__ import annotations

import os
import sqlite3
from datetime import date
from typing import Any, Dict, List, Optional, Tuple
import pyodbc

def test_pyodbc_stub():
    print("pyodbc подключен")

test_pyodbc_stub()

from flask import (
    Flask, g, render_template, request, redirect, url_for,
    session, flash, jsonify
)

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(ROOT, "data")

DB_MAP = {
    "Access": os.path.join(DATA_DIR, "library_access.sqlite3"),
    "Postgres": os.path.join(DATA_DIR, "library_postgres.sqlite3"),
}

ALLOWED_ADMIN_TABLES = {"readers", "books", "librarians", "statuses", "loans"}

DATE_MIN = date(2026, 1, 1)

def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")

    def active_db_key() -> str:
        k = session.get("db_key", "Access")
        return k if k in DB_MAP else "Access"

    def get_db() -> sqlite3.Connection:
        if "db" not in g:
            conn = sqlite3.connect(DB_MAP[active_db_key()])
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON;")
            g.db = conn
        return g.db
    
    def seed_statuses():
        db = get_db()
        db.execute("DELETE FROM statuses;")
        db.executemany(
            "INSERT INTO statuses(id, title) VALUES (?, ?);",
            [
                (1, "выдана"),
                (2, "возвращено"),
                (3, "просрочена"),
            ]
        )
        db.commit()

    @app.teardown_appcontext
    def close_db(exc: Optional[BaseException]) -> None:
        db = g.pop("db", None)
        if db is not None:
            db.close()

    def q_all(sql: str, params: Tuple[Any, ...] = ()) -> List[Dict[str, Any]]:
        cur = get_db().execute(sql, params)
        rows = cur.fetchall()
        cur.close()
        return [dict(r) for r in rows]

    def q_one(sql: str, params: Tuple[Any, ...] = ()) -> Optional[Dict[str, Any]]:
        cur = get_db().execute(sql, params)
        row = cur.fetchone()
        cur.close()
        return dict(row) if row else None

    def exec1(sql: str, params: Tuple[Any, ...] = ()) -> int:
        db = get_db()
        cur = db.execute(sql, params)
        db.commit()
        last_id = cur.lastrowid
        cur.close()
        return last_id

    def parse_date(s: str) -> date:
        # 'YYYY-MM-DD' из <input type="date">. MDN: value нормализуется к yyyy-mm-dd.
        return date.fromisoformat(s)

    def validate_loan(issue_date_s: str, due_date_s: str, status_id: int, return_date_s: Optional[str]) -> None:
        today = date.today()

        issue = parse_date(issue_date_s)
        due = parse_date(due_date_s)
        ret = parse_date(return_date_s) if return_date_s else None

        if issue < DATE_MIN or issue > today:
            raise ValueError("issue_date должен быть между 2026-01-01 и текущей датой.")
        if due < DATE_MIN or due > today:
            raise ValueError("due_date должен быть между 2026-01-01 и текущей датой.")
        if due < issue:
            raise ValueError("due_date должен быть >= issue_date.")

        if ret is not None:
            if ret < DATE_MIN or ret > today:
                raise ValueError("return_date должен быть между 2026-01-01 и текущей датой.")
            if ret < issue:
                raise ValueError("return_date должен быть >= issue_date.")

        if status_id == 2 and ret is None:
            raise ValueError("Для статуса 'возвращено' return_date обязателен.")

    @app.get("/switch-db/<db_key>")
    def switch_db(db_key: str):
        if db_key in DB_MAP:
            session["db_key"] = db_key
            flash(f"Активная база: {db_key}", "info")
        else:
            flash("Неизвестная база.", "danger")
        return redirect(request.args.get("next") or url_for("index"))

    # ---------- Главная ----------
    @app.get("/")
    def index():
        readers = q_all("SELECT id, full_name FROM readers ORDER BY full_name;")
        books = q_all("SELECT id, title FROM books ORDER BY title;")
        librarians = q_all("SELECT id, full_name FROM librarians ORDER BY full_name;")
        statuses = q_all("SELECT id, title FROM statuses ORDER BY id;")

        loans = q_all("""
            SELECT
              l.id,
              l.issue_date,
              l.due_date,
              l.return_date,
              r.full_name AS reader_name,
              b.title AS book_title,
              lb.full_name AS librarian_name,
              s.title AS status_title
            FROM loans l
            JOIN readers r ON r.id = l.reader_id
            JOIN books b ON b.id = l.book_id
            JOIN librarians lb ON lb.id = l.librarian_id
            JOIN statuses s ON s.id = l.status_id
            ORDER BY l.issue_date DESC, l.id DESC
            LIMIT 200;
        """)

        return render_template(
            "index.html",
            readers=readers,
            books=books,
            librarians=librarians,
            statuses=statuses,
            loans=loans,
        )

    @app.post("/loans/create")
    def create_loan():
        try:
            reader_id = int(request.form["reader_id"])
            book_id = int(request.form["book_id"])
            librarian_id = int(request.form["librarian_id"])
            status_id = int(request.form["status_id"])

            issue_date = request.form["issue_date"].strip()
            due_date = request.form["due_date"].strip()

            return_date = request.form.get("return_date")
            return_date = return_date.strip() if return_date else None
            if return_date == "":
                return_date = None

            validate_loan(issue_date, due_date, status_id, return_date)

            exec1("""
                INSERT INTO loans(
                  reader_id, book_id, librarian_id, status_id,
                  issue_date, due_date, return_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?);
            """, (reader_id, book_id, librarian_id, status_id,
                  issue_date, due_date, return_date))

            flash("Выдача создана.", "success")
        except ValueError as e:
            flash(str(e), "danger")
        except sqlite3.IntegrityError as e:
            flash(f"Ошибка ограничения БД: {e}", "danger")
        except Exception:
            flash("Не удалось создать выдачу (ошибка формы).", "danger")

        return redirect(url_for("index"))

    # ---------- API: модалки создания сущностей ----------
    @app.post("/api/readers/create")
    def api_create_reader():
        try:
            card = request.form["reader_card_number"].strip()
            full_name = request.form["full_name"].strip()
            phone = (request.form.get("phone") or "").strip() or None
            email = (request.form.get("email") or "").strip() or None

            new_id = exec1("""
                INSERT INTO readers(reader_card_number, full_name, phone, email)
                VALUES (?, ?, ?, ?);
            """, (card, full_name, phone, email))

            row = q_one("SELECT id, full_name FROM readers WHERE id=?;", (new_id,))
            return jsonify({"ok": True, "id": row["id"], "label": row["full_name"]})
        except sqlite3.IntegrityError as e:
            return jsonify({"ok": False, "error": str(e)}), 400
        except Exception:
            return jsonify({"ok": False, "error": "Некорректные данные."}), 400

    @app.post("/api/books/create")
    def api_create_book():
        try:
            inv = request.form["inventory_number"].strip()
            title = request.form["title"].strip()
            author = request.form["author"].strip()
            year = int(request.form["publish_year"])
            isbn = request.form["isbn"].strip()

            new_id = exec1("""
                INSERT INTO books(inventory_number, title, author, publish_year, isbn)
                VALUES (?, ?, ?, ?, ?);
            """, (inv, title, author, year, isbn))

            row = q_one("SELECT id, title FROM books WHERE id=?;", (new_id,))
            return jsonify({"ok": True, "id": row["id"], "label": row["title"]})
        except sqlite3.IntegrityError as e:
            return jsonify({"ok": False, "error": str(e)}), 400
        except Exception:
            return jsonify({"ok": False, "error": "Некорректные данные."}), 400

    @app.post("/api/librarians/create")
    def api_create_librarian():
        try:
            emp = request.form["employee_number"].strip()
            full_name = request.form["full_name"].strip()
            phone = (request.form.get("phone") or "").strip() or None

            new_id = exec1("""
                INSERT INTO librarians(employee_number, full_name, phone)
                VALUES (?, ?, ?);
            """, (emp, full_name, phone))

            row = q_one("SELECT id, full_name FROM librarians WHERE id=?;", (new_id,))
            return jsonify({"ok": True, "id": row["id"], "label": row["full_name"]})
        except sqlite3.IntegrityError as e:
            return jsonify({"ok": False, "error": str(e)}), 400
        except Exception:
            return jsonify({"ok": False, "error": "Некорректные данные."}), 400

    # ---------- Поиск ----------
    @app.get("/search")
    def search():
        mode = request.args.get("mode", "one")

        # данные для форм (подтягиваются свежими => админка влияет сразу)
        readers = q_all("SELECT id, full_name FROM readers ORDER BY full_name;")
        librarians = q_all("SELECT id, full_name FROM librarians ORDER BY full_name;")
        statuses = q_all("SELECT id, title FROM statuses ORDER BY id;")
        authors = q_all("SELECT DISTINCT author FROM books ORDER BY author;")

        meta: Dict[str, Any] = {"mode": mode}
        results: List[Dict[str, Any]] = []

        if mode == "one":
            entity = request.args.get("entity", "readers")
            meta["entity"] = entity

            if entity == "readers":
                name_prefix = (request.args.get("full_name_prefix") or "").strip()
                card_prefix = (request.args.get("card_prefix") or "").strip()
                phone_contains = (request.args.get("phone_contains") or "").strip()

                where = []
                params: List[Any] = []
                if name_prefix:
                    where.append("full_name LIKE ?")
                    params.append(name_prefix + "%")
                if card_prefix:
                    where.append("reader_card_number LIKE ?")
                    params.append(card_prefix + "%")
                if phone_contains:
                    where.append("phone LIKE ?")
                    params.append("%" + phone_contains + "%")

                sql = "SELECT id, reader_card_number, full_name, phone, email FROM readers"
                if where:
                    sql += " WHERE " + " AND ".join(where)
                sql += " ORDER BY full_name LIMIT 200;"
                results = q_all(sql, tuple(params))

            elif entity == "books":
                title_prefix = (request.args.get("title_prefix") or "").strip()
                author = (request.args.get("author") or "").strip()
                year = (request.args.get("publish_year") or "").strip()

                where = []
                params: List[Any] = []
                if title_prefix:
                    where.append("title LIKE ?")
                    params.append(title_prefix + "%")
                if author:
                    where.append("author = ?")
                    params.append(author)
                if year:
                    where.append("publish_year = ?")
                    params.append(int(year))

                sql = "SELECT id, inventory_number, title, author, publish_year, isbn FROM books"
                if where:
                    sql += " WHERE " + " AND ".join(where)
                sql += " ORDER BY title LIMIT 200;"
                results = q_all(sql, tuple(params))

            elif entity == "loans":
                status_id = (request.args.get("status_id") or "").strip()
                librarian_id = (request.args.get("librarian_id") or "").strip()
                issue_from = (request.args.get("issue_from") or "").strip()

                where = []
                params: List[Any] = []
                if status_id:
                    where.append("l.status_id = ?")
                    params.append(int(status_id))
                if librarian_id:
                    where.append("l.librarian_id = ?")
                    params.append(int(librarian_id))
                if issue_from:
                    where.append("l.issue_date >= ?")
                    params.append(issue_from)

                sql = """
                    SELECT
                      l.id, l.issue_date, l.due_date, l.return_date,
                      r.full_name AS reader_name,
                      b.title AS book_title,
                      lb.full_name AS librarian_name,
                      s.title AS status_title
                    FROM loans l
                    JOIN readers r ON r.id = l.reader_id
                    JOIN books b ON b.id = l.book_id
                    JOIN librarians lb ON lb.id = l.librarian_id
                    JOIN statuses s ON s.id = l.status_id
                """
                if where:
                    sql += " WHERE " + " AND ".join(where)
                sql += " ORDER BY l.issue_date DESC, l.id DESC LIMIT 200;"
                results = q_all(sql, tuple(params))

        elif mode == "two":
            # каскад: reader -> доступные книги в loans
            reader_id = (request.args.get("reader_id") or "").strip()
            book_id = (request.args.get("book_id") or "").strip()
            meta["reader_id"] = reader_id
            meta["book_id"] = book_id

            if reader_id:
                sql = """
                    SELECT
                      r.full_name AS reader_name,
                      b.title AS book_title,
                      l.issue_date, l.due_date, l.return_date,
                      s.title AS status_title,
                      lb.full_name AS librarian_name
                    FROM loans l
                    JOIN readers r ON r.id = l.reader_id
                    JOIN books b ON b.id = l.book_id
                    JOIN statuses s ON s.id = l.status_id
                    JOIN librarians lb ON lb.id = l.librarian_id
                    WHERE l.reader_id = ?
                """
                params: List[Any] = [int(reader_id)]
                if book_id:
                    sql += " AND l.book_id = ?"
                    params.append(int(book_id))
                sql += " ORDER BY l.issue_date DESC, l.id DESC LIMIT 200;"
                results = q_all(sql, tuple(params))

        elif mode == "agg":
            # агрегат: количество выдач по библиотекарю
            results = q_all("""
                SELECT
                  lb.full_name AS librarian_name,
                  COUNT(l.id) AS loans_count
                FROM librarians lb
                LEFT JOIN loans l ON l.librarian_id = lb.id
                GROUP BY lb.id
                ORDER BY loans_count DESC, lb.full_name ASC;
            """)

        return render_template(
            "search.html",
            mode=mode,
            meta=meta,
            results=results,
            readers=readers,
            librarians=librarians,
            statuses=statuses,
            authors=authors,
        )

    @app.get("/api/options/books-by-reader")
    def api_books_by_reader():
        rid = request.args.get("reader_id", "").strip()
        if not rid:
            return jsonify({"ok": True, "items": []})
        try:
            rows = q_all("""
                SELECT DISTINCT b.id, b.title
                FROM loans l
                JOIN books b ON b.id = l.book_id
                WHERE l.reader_id = ?
                ORDER BY b.title;
            """, (int(rid),))
            items = [{"value": r["id"], "label": r["title"]} for r in rows]
            return jsonify({"ok": True, "items": items})
        except Exception:
            return jsonify({"ok": False, "error": "bad reader_id"}), 400

    # ---------- Админка ----------
    @app.get("/admin")
    def admin():
        table = request.args.get("table", "readers")
        if table not in ALLOWED_ADMIN_TABLES:
            table = "readers"

        rows = q_all(f"SELECT * FROM {table} LIMIT 200;")

        readers = q_all("SELECT id, full_name FROM readers ORDER BY full_name;")
        books = q_all("SELECT id, title FROM books ORDER BY title;")
        librarians = q_all("SELECT id, full_name FROM librarians ORDER BY full_name;")
        statuses = q_all("SELECT id, title FROM statuses ORDER BY id;")

        return render_template(
            "admin.html",
            table=table,
            readers=readers,
            books=books,
            librarians=librarians,
            statuses=statuses,
            today=date.today().isoformat(),
            rows=rows
        )

    @app.post("/admin/<table>/create")
    def admin_create(table: str):
        if table not in ALLOWED_ADMIN_TABLES:
            flash("Недопустимая таблица.", "danger")
            return redirect(url_for("admin"))

        try:
            if table == "readers":
                exec1("""
                    INSERT INTO readers(reader_card_number, full_name, phone, email)
                    VALUES (?, ?, ?, ?);
                """, (
                    request.form["reader_card_number"].strip(),
                    request.form["full_name"].strip(),
                    (request.form.get("phone") or "").strip() or None,
                    (request.form.get("email") or "").strip() or None,
                ))
                flash("Читатель добавлен.", "success")

            elif table == "books":
                exec1("""
                    INSERT INTO books(inventory_number, title, author, publish_year, isbn)
                    VALUES (?, ?, ?, ?, ?);
                """, (
                    request.form["inventory_number"].strip(),
                    request.form["title"].strip(),
                    request.form["author"].strip(),
                    int(request.form["publish_year"]),
                    request.form["isbn"].strip(),
                ))
                flash("Книга добавлена.", "success")

            elif table == "librarians":
                exec1("""
                    INSERT INTO librarians(employee_number, full_name, phone)
                    VALUES (?, ?, ?);
                """, (
                    request.form["employee_number"].strip(),
                    request.form["full_name"].strip(),
                    (request.form.get("phone") or "").strip() or None,
                ))
                flash("Библиотекарь добавлен.", "success")

            elif table == "loans":
                reader_id = int(request.form["reader_id"])
                book_id = int(request.form["book_id"])
                librarian_id = int(request.form["librarian_id"])
                status_id = int(request.form["status_id"])
                issue_date = request.form["issue_date"].strip()
                due_date = request.form["due_date"].strip()
                return_date = (request.form.get("return_date") or "").strip() or None

                validate_loan(issue_date, due_date, status_id, return_date)

                exec1("""
                    INSERT INTO loans(reader_id, book_id, librarian_id, status_id, issue_date, due_date, return_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?);
                """, (reader_id, book_id, librarian_id, status_id, issue_date, due_date, return_date))
                flash("Выдача добавлена.", "success")

            elif table == "statuses":
                flash("Справочник статусов фиксирован и не редактируется.", "warning")

        except ValueError as e:
            flash(str(e), "danger")
        except sqlite3.IntegrityError as e:
            flash(f"Ошибка ограничения БД: {e}", "danger")
        except Exception:
            flash("Некорректные данные.", "danger")

        return redirect(url_for("admin", table=table))
    
    @app.post("/admin/<table>/delete/<int:id>")
    def admin_delete(table: str, id: int):
        if table not in ALLOWED_ADMIN_TABLES:
            flash("Недопустимая таблица.", "danger")
            return redirect(url_for("admin"))
        
        if table in ("statuses"):
            flash("Эти записи нельзя удалять", "danger")
            return redirect(url_for("admin", table=table))

        try:
            exec1(f"DELETE FROM {table} WHERE id = ?;", (id,))
            flash("Запись удалена.", "success")
        except Exception as e:
            flash(f"Ошибка удаления: {e}", "danger")

        return redirect(url_for("admin", table=table))
    
    return app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
