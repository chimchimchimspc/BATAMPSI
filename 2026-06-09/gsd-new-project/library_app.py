from __future__ import annotations

import html
import secrets
import sqlite3
from datetime import date
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote, urlparse


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "library.db"
SESSIONS: dict[str, dict[str, Any]] = {}


class ClosingConnection(sqlite3.Connection):
    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> bool:
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


def connect(db_path: Path | str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, factory=ClosingConnection)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: Path | str = DB_PATH) -> None:
    with connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('admin', 'member'))
            );

            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                stock INTEGER NOT NULL CHECK(stock >= 0)
            );

            CREATE TABLE IF NOT EXISTS borrowings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                borrow_date TEXT NOT NULL,
                return_date TEXT,
                status TEXT NOT NULL CHECK(status IN ('borrowed', 'returned')),
                FOREIGN KEY(book_id) REFERENCES books(id) ON DELETE RESTRICT,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """
        )

        if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
            conn.executemany(
                "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                [
                    ("admin", "admin123", "admin"),
                    ("member", "member123", "member"),
                ],
            )

        if conn.execute("SELECT COUNT(*) FROM books").fetchone()[0] == 0:
            conn.executemany(
                "INSERT INTO books (title, author, stock) VALUES (?, ?, ?)",
                [
                    ("Clean Code", "Robert C. Martin", 3),
                    ("Database System Concepts", "Abraham Silberschatz", 2),
                    ("The Pragmatic Programmer", "Andrew Hunt and David Thomas", 1),
                    ("Introduction to Algorithms", "Thomas H. Cormen", 0),
                ],
            )


def authenticate(username: str, password: str, db_path: Path | str = DB_PATH) -> sqlite3.Row | None:
    with connect(db_path) as conn:
        return conn.execute(
            "SELECT id, username, role FROM users WHERE username = ? AND password = ?",
            (username.strip(), password),
        ).fetchone()


def add_book(title: str, author: str, stock: int, db_path: Path | str = DB_PATH) -> None:
    if stock < 0:
        raise ValueError("Stock cannot be negative.")
    with connect(db_path) as conn:
        conn.execute(
            "INSERT INTO books (title, author, stock) VALUES (?, ?, ?)",
            (title.strip(), author.strip(), stock),
        )


def edit_book(book_id: int, title: str, author: str, stock: int, db_path: Path | str = DB_PATH) -> None:
    if stock < 0:
        raise ValueError("Stock cannot be negative.")
    with connect(db_path) as conn:
        cursor = conn.execute(
            "UPDATE books SET title = ?, author = ?, stock = ? WHERE id = ?",
            (title.strip(), author.strip(), stock, book_id),
        )
        if cursor.rowcount == 0:
            raise ValueError("Book not found.")


def delete_book(book_id: int, db_path: Path | str = DB_PATH) -> None:
    with connect(db_path) as conn:
        active = conn.execute(
            "SELECT COUNT(*) FROM borrowings WHERE book_id = ? AND status = 'borrowed'",
            (book_id,),
        ).fetchone()[0]
        if active:
            raise ValueError("Cannot delete a book that is currently borrowed.")
        cursor = conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
        if cursor.rowcount == 0:
            raise ValueError("Book not found.")


def borrow_book(book_id: int, user_id: int, db_path: Path | str = DB_PATH) -> None:
    with connect(db_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        book = conn.execute("SELECT stock FROM books WHERE id = ?", (book_id,)).fetchone()
        if book is None:
            raise ValueError("Book not found.")
        if book["stock"] <= 0:
            raise ValueError("This book is out of stock.")

        conn.execute("UPDATE books SET stock = stock - 1 WHERE id = ?", (book_id,))
        conn.execute(
            """
            INSERT INTO borrowings (book_id, user_id, borrow_date, return_date, status)
            VALUES (?, ?, ?, NULL, 'borrowed')
            """,
            (book_id, user_id, date.today().isoformat()),
        )


def return_book(borrowing_id: int, user_id: int | None = None, db_path: Path | str = DB_PATH) -> None:
    with connect(db_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        params: list[Any] = [borrowing_id]
        owner_clause = ""
        if user_id is not None:
            owner_clause = " AND user_id = ?"
            params.append(user_id)
        borrowing = conn.execute(
            f"SELECT book_id FROM borrowings WHERE id = ? AND status = 'borrowed'{owner_clause}",
            params,
        ).fetchone()
        if borrowing is None:
            raise ValueError("Borrowing record not found or already returned.")

        conn.execute(
            "UPDATE borrowings SET status = 'returned', return_date = ? WHERE id = ?",
            (date.today().isoformat(), borrowing_id),
        )
        conn.execute("UPDATE books SET stock = stock + 1 WHERE id = ?", (borrowing["book_id"],))


def list_books(db_path: Path | str = DB_PATH, available_only: bool = False) -> list[sqlite3.Row]:
    with connect(db_path) as conn:
        where = "WHERE stock > 0" if available_only else ""
        return conn.execute(f"SELECT * FROM books {where} ORDER BY title").fetchall()


def list_borrowings(db_path: Path | str = DB_PATH, user_id: int | None = None) -> list[sqlite3.Row]:
    with connect(db_path) as conn:
        params: list[Any] = []
        where = ""
        if user_id is not None:
            where = "WHERE borrowings.user_id = ?"
            params.append(user_id)
        return conn.execute(
            f"""
            SELECT borrowings.*, books.title, books.author, users.username
            FROM borrowings
            JOIN books ON books.id = borrowings.book_id
            JOIN users ON users.id = borrowings.user_id
            {where}
            ORDER BY borrowings.id DESC
            """,
            params,
        ).fetchall()


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def page(title: str, body: str, user: dict[str, Any] | None = None, notice: str = "") -> bytes:
    nav = ""
    if user:
        if user["role"] == "admin":
            nav = """
            <a href="/books">Books</a>
            <a href="/admin/borrowings">Borrowings</a>
            """
        else:
            nav = """
            <a href="/member">Available Books</a>
            <a href="/borrowings">My Borrowings</a>
            """
        nav += '<a href="/logout">Logout</a>'

    alert = f'<div class="notice">{esc(notice)}</div>' if notice else ""
    return f"""<!doctype html>
    <html lang="en">
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title>{esc(title)} - Library Management System</title>
      <link rel="stylesheet" href="/static/styles.css">
    </head>
    <body>
      <header class="topbar">
        <div>
          <strong>Library Management System</strong>
          <span>{esc(user["username"] + " · " + user["role"]) if user else "Educational demo"}</span>
        </div>
        <nav>{nav}</nav>
      </header>
      <main>
        {alert}
        {body}
      </main>
    </body>
    </html>""".encode()


STYLES = """
:root {
  color-scheme: light;
  --ink: #1f2933;
  --muted: #637083;
  --line: #d8dee8;
  --paper: #ffffff;
  --bg: #f4f7fb;
  --accent: #216869;
  --accent-2: #d1495b;
  --warn: #a15c00;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: Arial, Helvetica, sans-serif;
  background: var(--bg);
  color: var(--ink);
}
.topbar {
  min-height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 14px 26px;
  background: var(--paper);
  border-bottom: 1px solid var(--line);
}
.topbar strong { display: block; font-size: 18px; }
.topbar span { color: var(--muted); font-size: 13px; }
nav { display: flex; gap: 10px; flex-wrap: wrap; }
a { color: var(--accent); font-weight: 700; text-decoration: none; }
main { width: min(1120px, calc(100% - 32px)); margin: 28px auto 60px; }
h1 { margin: 0 0 6px; font-size: 30px; }
p.lede { margin: 0 0 22px; color: var(--muted); }
.panel {
  background: var(--paper);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 18px;
  margin-bottom: 18px;
}
.grid { display: grid; grid-template-columns: repeat(4, minmax(120px, 1fr)); gap: 12px; }
label { display: grid; gap: 6px; color: var(--muted); font-size: 13px; font-weight: 700; }
input {
  width: 100%;
  min-height: 40px;
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 8px 10px;
  color: var(--ink);
  background: #fff;
}
button {
  min-height: 40px;
  border: 0;
  border-radius: 6px;
  padding: 8px 13px;
  color: #fff;
  background: var(--accent);
  font-weight: 700;
  cursor: pointer;
}
button.danger { background: var(--accent-2); }
button.secondary { background: #52677a; }
table {
  width: 100%;
  border-collapse: collapse;
  background: var(--paper);
  border: 1px solid var(--line);
  border-radius: 8px;
  overflow: hidden;
}
th, td { padding: 12px; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; }
th { background: #edf2f7; font-size: 13px; color: #425466; }
tr:last-child td { border-bottom: 0; }
.actions { display: flex; gap: 8px; flex-wrap: wrap; align-items: end; }
.inline { display: contents; }
.badge {
  display: inline-block;
  border-radius: 999px;
  padding: 4px 9px;
  font-size: 12px;
  font-weight: 700;
  background: #e7f4ef;
  color: #17634d;
}
.badge.returned { background: #f3edf7; color: #674188; }
.notice {
  padding: 12px 14px;
  border: 1px solid #f0d28a;
  border-radius: 8px;
  margin-bottom: 18px;
  background: #fff8e6;
  color: var(--warn);
  font-weight: 700;
}
.login {
  max-width: 430px;
  margin: 70px auto;
}
.muted { color: var(--muted); font-size: 13px; }
@media (max-width: 800px) {
  .topbar { align-items: flex-start; flex-direction: column; }
  .grid { grid-template-columns: 1fr; }
  table, thead, tbody, th, td, tr { display: block; }
  thead { display: none; }
  td { border-bottom: 0; padding: 8px 12px; }
  tr { border-bottom: 1px solid var(--line); padding: 8px 0; }
}
"""


class LibraryHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        init_db()
        path = urlparse(self.path).path
        if path == "/static/styles.css":
            return self.respond(STYLES.encode(), "text/css")
        if path == "/logout":
            token = self.cookie("session")
            if token:
                SESSIONS.pop(token, None)
            return self.redirect("/login", "Logged out.")

        user = self.current_user()
        if path in ("/", "/login"):
            if user:
                return self.redirect("/books" if user["role"] == "admin" else "/member")
            return self.respond(page("Login", self.login_view(), notice=self.query_notice()))

        if not user:
            return self.redirect("/login", "Please log in first.")

        if path == "/books":
            if user["role"] != "admin":
                return self.error_page(HTTPStatus.FORBIDDEN, "This page is restricted.")
            return self.respond(self.admin_books_view(user))
        if path == "/admin/borrowings":
            if user["role"] != "admin":
                return self.error_page(HTTPStatus.FORBIDDEN, "This page is restricted.")
            return self.respond(self.borrowings_view(user, None))
        if path == "/member":
            if user["role"] != "member":
                return self.error_page(HTTPStatus.FORBIDDEN, "This page is restricted.")
            return self.respond(self.member_books_view(user))
        if path == "/borrowings":
            if user["role"] != "member":
                return self.error_page(HTTPStatus.FORBIDDEN, "This page is restricted.")
            return self.respond(self.borrowings_view(user, user["id"]))
        self.error_page(HTTPStatus.NOT_FOUND, "Page not found.")

    def do_POST(self) -> None:
        init_db()
        path = urlparse(self.path).path
        form = self.form()

        if path == "/login":
            user = authenticate(form.get("username", ""), form.get("password", ""))
            if not user:
                return self.redirect("/login", "Invalid username or password.")
            token = secrets.token_urlsafe(24)
            SESSIONS[token] = dict(user)
            self.send_response(HTTPStatus.SEE_OTHER)
            self.send_header("Location", "/books" if user["role"] == "admin" else "/member")
            self.send_header("Set-Cookie", f"session={token}; Path=/; HttpOnly; SameSite=Lax")
            self.end_headers()
            return

        user = self.current_user()
        if not user:
            return self.redirect("/login", "Please log in first.")

        try:
            if path == "/books/add" and user["role"] == "admin":
                add_book(form["title"], form["author"], int(form["stock"]))
                return self.redirect("/books", "Book added.")
            if path == "/books/edit" and user["role"] == "admin":
                edit_book(int(form["id"]), form["title"], form["author"], int(form["stock"]))
                return self.redirect("/books", "Book updated.")
            if path == "/books/delete" and user["role"] == "admin":
                delete_book(int(form["id"]))
                return self.redirect("/books", "Book deleted.")
            if path == "/borrow" and user["role"] == "member":
                borrow_book(int(form["book_id"]), user["id"])
                return self.redirect("/borrowings", "Book borrowed.")
            if path == "/return" and user["role"] == "member":
                return_book(int(form["borrowing_id"]), user["id"])
                return self.redirect("/borrowings", "Book returned.")
        except (KeyError, ValueError, sqlite3.IntegrityError) as exc:
            target = "/books" if user["role"] == "admin" else "/member"
            return self.redirect(target, str(exc))

        self.error_page(HTTPStatus.FORBIDDEN, "You do not have permission to perform this action.")

    def login_view(self) -> str:
        return """
        <section class="panel login">
          <h1>Sign in</h1>
          <p class="lede">Use admin/admin123 or member/member123.</p>
          <form method="post" action="/login" class="grid" style="grid-template-columns: 1fr;">
            <label>Username <input name="username" required autofocus></label>
            <label>Password <input name="password" type="password" required></label>
            <button type="submit">Login</button>
          </form>
        </section>
        """

    def admin_books_view(self, user: dict[str, Any]) -> bytes:
        rows = "".join(
            f"""
            <tr>
              <form method="post" action="/books/edit" class="inline">
                <td><input type="hidden" name="id" value="{book['id']}"><input name="title" value="{esc(book['title'])}" required></td>
                <td><input name="author" value="{esc(book['author'])}" required></td>
                <td><input name="stock" type="number" min="0" value="{book['stock']}" required></td>
                <td class="actions">
                  <button type="submit">Save</button>
              </form>
              <form method="post" action="/books/delete">
                  <input type="hidden" name="id" value="{book['id']}">
                  <button type="submit" class="danger">Delete</button>
              </form>
                </td>
            </tr>
            """
            for book in list_books()
        )
        body = f"""
        <h1>Book Management</h1>
        <p class="lede">Create, update, delete, and monitor book availability.</p>
        <section class="panel">
          <form method="post" action="/books/add" class="grid">
            <label>Title <input name="title" required></label>
            <label>Author <input name="author" required></label>
            <label>Stock <input name="stock" type="number" min="0" value="1" required></label>
            <div class="actions"><button type="submit">Add Book</button></div>
          </form>
        </section>
        <table>
          <thead><tr><th>Title</th><th>Author</th><th>Stock</th><th>Actions</th></tr></thead>
          <tbody>{rows or '<tr><td colspan="4">No books yet.</td></tr>'}</tbody>
        </table>
        """
        return page("Book Management", body, user, self.query_notice())

    def member_books_view(self, user: dict[str, Any]) -> bytes:
        books = list_books(available_only=True)
        rows = "".join(
            f"""
            <tr>
              <td>{esc(book['title'])}</td>
              <td>{esc(book['author'])}</td>
              <td>{book['stock']}</td>
              <td>
                <form method="post" action="/borrow">
                  <input type="hidden" name="book_id" value="{book['id']}">
                  <button type="submit">Borrow</button>
                </form>
              </td>
            </tr>
            """
            for book in books
        )
        body = f"""
        <h1>Available Books</h1>
        <p class="lede">Only books with stock greater than zero can be borrowed.</p>
        <table>
          <thead><tr><th>Title</th><th>Author</th><th>Stock</th><th>Action</th></tr></thead>
          <tbody>{rows or '<tr><td colspan="4">No books are available right now.</td></tr>'}</tbody>
        </table>
        """
        return page("Available Books", body, user, self.query_notice())

    def borrowings_view(self, user: dict[str, Any], user_id: int | None) -> bytes:
        rows = ""
        for item in list_borrowings(user_id=user_id):
            return_action = ""
            if user["role"] == "member" and item["status"] == "borrowed":
                return_action = f"""
                <form method="post" action="/return">
                  <input type="hidden" name="borrowing_id" value="{item['id']}">
                  <button type="submit" class="secondary">Return</button>
                </form>
                """
            rows += f"""
            <tr>
              <td>{esc(item['title'])}</td>
              <td>{esc(item['username'])}</td>
              <td>{esc(item['borrow_date'])}</td>
              <td>{esc(item['return_date'] or '-')}</td>
              <td><span class="badge {esc(item['status'])}">{esc(item['status'])}</span></td>
              <td>{return_action}</td>
            </tr>
            """
        body = f"""
        <h1>{"Borrowing Records" if user["role"] == "admin" else "My Borrowings"}</h1>
        <p class="lede">Borrow and return transactions are saved in the relational database.</p>
        <table>
          <thead><tr><th>Book</th><th>Member</th><th>Borrow Date</th><th>Return Date</th><th>Status</th><th>Action</th></tr></thead>
          <tbody>{rows or '<tr><td colspan="6">No borrowing records yet.</td></tr>'}</tbody>
        </table>
        """
        return page("Borrowing Records", body, user, self.query_notice())

    def current_user(self) -> dict[str, Any] | None:
        token = self.cookie("session")
        return SESSIONS.get(token or "")

    def cookie(self, name: str) -> str | None:
        header = self.headers.get("Cookie", "")
        for chunk in header.split(";"):
            if "=" in chunk:
                key, value = chunk.strip().split("=", 1)
                if key == name:
                    return value
        return None

    def form(self) -> dict[str, str]:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode()
        return {key: values[0] for key, values in parse_qs(raw).items()}

    def query_notice(self) -> str:
        query = parse_qs(urlparse(self.path).query)
        return query.get("notice", [""])[0]

    def redirect(self, target: str, notice: str = "") -> None:
        suffix = ("?notice=" + quote(notice)) if notice else ""
        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header("Location", target + suffix)
        self.end_headers()

    def respond(self, body: bytes, content_type: str = "text/html") -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def error_page(self, status: HTTPStatus, message: str) -> None:
        self.send_response(status)
        body = page(status.phrase, f'<section class="panel"><h1>{status.phrase}</h1><p>{esc(message)}</p></section>')
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        return


def run(host: str = "127.0.0.1", port: int = 8000) -> None:
    init_db()
    server = ThreadingHTTPServer((host, port), LibraryHandler)
    print(f"Library Management System running at http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run()
