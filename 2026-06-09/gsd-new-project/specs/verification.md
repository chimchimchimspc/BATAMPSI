# Verification Steps

## Test 1: Add Book

1. Login as Admin.
2. Add a new book.
3. Verify the book appears in the list.

Expected result: The new book is stored and displayed.

## Test 2: Edit Book

1. Login as Admin.
2. Select a book.
3. Modify book title, author, or stock.
4. Save the changes.

Expected result: Updated information is displayed immediately.

## Test 3: Delete Book

1. Login as Admin.
2. Select a book that is not actively borrowed.
3. Delete the book.

Expected result: The book is removed from the list.

## Test 4: Borrow Book

1. Login as Member.
2. Open available books.
3. Borrow a book with stock greater than zero.

Expected result:

- Stock decreases by one.
- Borrowing transaction is recorded.
- Borrowing appears in member history.

## Test 5: Return Book

1. Login as Member.
2. Open borrowing history.
3. Return an active borrowed book.

Expected result:

- Stock increases by one.
- Return date is recorded.
- Borrowing status changes to `returned`.

## Automated Verification

Run:

```powershell
& "C:\Users\LENOVO LOQ\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m unittest -v
```

Expected result: all tests pass.
