import tempfile
import unittest
from pathlib import Path

from library_app import (
    add_book,
    borrow_book,
    connect,
    delete_book,
    edit_book,
    init_db,
    list_books,
    list_borrowings,
    return_book,
)


class LibraryAppTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "test.db"
        init_db(self.db_path)

    def tearDown(self):
        self.tmp.cleanup()

    def member_id(self):
        with connect(self.db_path) as conn:
            return conn.execute("SELECT id FROM users WHERE username = 'member'").fetchone()[0]

    def book_stock(self, book_id):
        with connect(self.db_path) as conn:
            return conn.execute("SELECT stock FROM books WHERE id = ?", (book_id,)).fetchone()[0]

    def test_add_edit_and_delete_book(self):
        add_book("Refactoring", "Martin Fowler", 4, self.db_path)
        book = [row for row in list_books(self.db_path) if row["title"] == "Refactoring"][0]
        self.assertEqual(book["stock"], 4)

        edit_book(book["id"], "Refactoring", "M. Fowler", 5, self.db_path)
        updated = [row for row in list_books(self.db_path) if row["id"] == book["id"]][0]
        self.assertEqual(updated["author"], "M. Fowler")
        self.assertEqual(updated["stock"], 5)

        delete_book(book["id"], self.db_path)
        self.assertFalse([row for row in list_books(self.db_path) if row["id"] == book["id"]])

    def test_borrow_decreases_stock_and_records_transaction(self):
        add_book("Domain-Driven Design", "Eric Evans", 1, self.db_path)
        book = [row for row in list_books(self.db_path) if row["title"] == "Domain-Driven Design"][0]

        borrow_book(book["id"], self.member_id(), self.db_path)

        self.assertEqual(self.book_stock(book["id"]), 0)
        borrowings = list_borrowings(self.db_path, self.member_id())
        self.assertEqual(borrowings[0]["status"], "borrowed")
        self.assertEqual(borrowings[0]["title"], "Domain-Driven Design")

    def test_cannot_borrow_when_stock_is_zero(self):
        add_book("Unavailable Book", "No Copies", 0, self.db_path)
        book = [row for row in list_books(self.db_path) if row["title"] == "Unavailable Book"][0]

        with self.assertRaises(ValueError):
            borrow_book(book["id"], self.member_id(), self.db_path)

        self.assertEqual(self.book_stock(book["id"]), 0)

    def test_return_increases_stock_and_marks_returned(self):
        add_book("Working Effectively with Legacy Code", "Michael Feathers", 1, self.db_path)
        book = [row for row in list_books(self.db_path) if row["title"] == "Working Effectively with Legacy Code"][0]
        member_id = self.member_id()
        borrow_book(book["id"], member_id, self.db_path)
        borrowing_id = list_borrowings(self.db_path, member_id)[0]["id"]

        return_book(borrowing_id, member_id, self.db_path)

        self.assertEqual(self.book_stock(book["id"]), 1)
        returned = list_borrowings(self.db_path, member_id)[0]
        self.assertEqual(returned["status"], "returned")
        self.assertIsNotNone(returned["return_date"])


if __name__ == "__main__":
    unittest.main()
