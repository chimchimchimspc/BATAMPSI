# Acceptance Criteria

## Book Management

- Admin can create books successfully.
- Admin can edit book title, author, and stock.
- Admin can delete books that are not actively borrowed.
- Updated book information is displayed immediately after changes.
- Members cannot access book management pages.

## Book Borrowing

- Members can view books with stock greater than zero.
- Members can borrow available books.
- Stock decreases by one after borrowing.
- Borrowing transaction is saved in the database.
- Books with zero stock cannot be borrowed.

## Book Returning

- Members can view their borrowing history.
- Members can return active borrowed books.
- Stock increases by one after return.
- Return date is recorded.
- Borrowing status changes from `borrowed` to `returned`.

## Admin Monitoring

- Admin can view borrowing records.
- Borrowing records show book, member, borrow date, return date, and status.
