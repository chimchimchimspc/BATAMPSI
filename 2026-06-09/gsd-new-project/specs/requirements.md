# Requirements

## Feature 1: Book Management

The system shall allow administrators to:

- Add new books.
- Edit book information.
- Delete books.
- View the list of books.

Only users with the `admin` role can access book management features.

## Feature 2: Book Borrowing

The system shall allow members to:

- View available books.
- Borrow a book if stock is available.
- Record borrowing transactions.

The system must reject borrowing requests when a book's stock is zero.

## Feature 3: Book Returning

The system shall allow members to:

- Return borrowed books.
- Update book availability after return.
- Record return transactions.

Only active borrowed records can be returned.

## Functional Constraints

- The system uses a relational database.
- A book cannot be borrowed if its stock is zero.
- Each borrowing record must reference an existing book.
- Only administrators can manage book data.
- Members can only return their own borrowed books.
- The system is designed for educational purposes.
