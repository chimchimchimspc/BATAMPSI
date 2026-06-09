# Library Management System

A small educational Library Management System built with Python's standard library and SQLite.

## Features

- Admin login for book management.
- Member login for viewing, borrowing, and returning books.
- SQLite relational database with `users`, `books`, and `borrowings` tables.
- Stock validation prevents borrowing unavailable books.
- Borrowing and return records are persisted.

## Demo Accounts

| Role | Username | Password |
| --- | --- | --- |
| Admin | `admin` | `admin123` |
| Member | `member` | `member123` |

## Run

Use the bundled Python runtime in this Codex workspace:

```powershell
& 'C:\Users\LENOVO LOQ\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' library_app.py
```

Then open:

```text
http://127.0.0.1:8000
```

## Test

```powershell
& 'C:\Users\LENOVO LOQ\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m unittest -v
```

## Notes

Passwords are stored as plain text because this is an educational demo focused on the specified workflows. A production system should hash passwords, add CSRF protection, and use a stronger session store.
