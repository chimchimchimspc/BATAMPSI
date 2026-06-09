# Data Model

## Entity: Books

| Field | Type | Description |
| --- | --- | --- |
| `id` | Integer | Primary key. |
| `title` | String | Book title. |
| `author` | String | Book author. |
| `stock` | Integer | Number of available copies. Must be zero or greater. |

## Entity: Users

| Field | Type | Description |
| --- | --- | --- |
| `id` | Integer | Primary key. |
| `username` | String | Unique login username. |
| `password` | String | Login password for demo use. |
| `role` | String | User role: `admin` or `member`. |

## Entity: Borrowings

| Field | Type | Description |
| --- | --- | --- |
| `id` | Integer | Primary key. |
| `book_id` | Integer | Foreign key referencing `books.id`. |
| `user_id` | Integer | Foreign key referencing `users.id`. |
| `borrow_date` | Date | Date when the book was borrowed. |
| `return_date` | Date | Date when the book was returned. Empty while active. |
| `status` | String | Borrowing status: `borrowed` or `returned`. |

## Relationships

- One book can have many borrowing records.
- One user can have many borrowing records.
- Each borrowing record must reference one existing book.
- Each borrowing record must reference one existing user.
