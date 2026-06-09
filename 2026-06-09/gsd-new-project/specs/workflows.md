# Workflows

## Book Management Workflow

1. Admin logs in.
2. Admin opens the book management page.
3. Admin adds, edits, or deletes book data.
4. System validates the submitted data.
5. System updates the database.
6. Updated book information is displayed.

## Book Borrowing Workflow

1. Member logs in.
2. Member views available books.
3. Member selects a book.
4. Member clicks Borrow.
5. System validates that stock is greater than zero.
6. System creates a borrowing record.
7. System decreases the book stock by one.
8. Borrowing history displays the new transaction.

## Book Returning Workflow

1. Member logs in.
2. Member opens borrowing history.
3. Member selects an active borrowed book.
4. Member clicks Return.
5. System validates the borrowing record.
6. System updates the borrowing status to `returned`.
7. System records the return date.
8. System increases the book stock by one.
