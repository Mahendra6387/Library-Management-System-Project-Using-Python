import sqlite3
import datetime
import os
import textwrap

DB_FILE = "library.db"

def get_db_conn():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    if not os.path.exists(DB_FILE):
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE books (
            book_id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT,
            year INTEGER,
            isbn TEXT UNIQUE,
            total_copies INTEGER NOT NULL DEFAULT 1,
            available_copies INTEGER NOT NULL DEFAULT 1
        );
        """)

        cur.execute("""
        CREATE TABLE members (
            member_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT,
            phone TEXT
        );
        """)

        cur.execute("""
        CREATE TABLE issues (
            issue_id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER NOT NULL,
            member_id INTEGER NOT NULL,
            issue_date TEXT NOT NULL,
            due_date TEXT NOT NULL,
            return_date TEXT,
            FOREIGN KEY(book_id) REFERENCES books(book_id),
            FOREIGN KEY(member_id) REFERENCES members(member_id)
        );
        """)

        conn.commit()
        conn.close()


def add_book(title, author=None, year=None, isbn=None, copies=1):
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO books (title, author, year, isbn, total_copies, available_copies) VALUES (?, ?, ?, ?, ?, ?)",
        (title, author, year, isbn, copies, copies)
    )
    conn.commit()
    conn.close()
    print("Book added successfully.")


def update_book(book_id, title=None, author=None, year=None, isbn=None, total_copies=None):
    conn = get_db_conn()
    cur = conn.cursor()
    book = cur.execute("SELECT * FROM books WHERE book_id = ?", (book_id,)).fetchone()
    if not book:
        print("No book found with that ID.")
        conn.close()
        return


    new_title = title if title is not None else book["title"]
    new_author = author if author is not None else book["author"]
    new_year = year if year is not None else book["year"]
    new_isbn = isbn if isbn is not None else book["isbn"]
    new_total = total_copies if total_copies is not None else book["total_copies"]

    available = book["available_copies"] + (new_total - book["total_copies"])
    if available < 0:
        print("Cannot reduce total copies below the number currently issued out.")
        conn.close()
        return

    cur.execute(
        "UPDATE books SET title=?, author=?, year=?, isbn=?, total_copies=?, available_copies=? WHERE book_id=?",
        (new_title, new_author, new_year, new_isbn, new_total, available, book_id)
    )
    conn.commit()
    conn.close()
    print("Book updated.")


def delete_book(book_id):
    conn = get_db_conn()
    cur = conn.cursor()
    book = cur.execute("SELECT * FROM books WHERE book_id = ?", (book_id,)).fetchone()
    if not book:
        print("No book found with that ID.")
        conn.close()
        return

    issued_count = cur.execute("SELECT COUNT(*) FROM issues WHERE book_id = ? AND return_date IS NULL", (book_id,)).fetchone()[0]
    if issued_count > 0:
        print("Cannot delete book: some copies are currently issued.")
        conn.close()
        return

    cur.execute("DELETE FROM books WHERE book_id = ?", (book_id,))
    conn.commit()
    conn.close()
    print("Book deleted.")


def list_books():
    conn = get_db_conn()
    cur = conn.cursor()
    rows = cur.execute("SELECT * FROM books ORDER BY title").fetchall()
    conn.close()
    if not rows:
        print("No books in the library yet.")
        return

    print("{:<5} {:<30} {:<20} {:<6} {:<12} {:<10}".format("ID", "Title", "Author", "Year", "Total", "Avail"))
    print("-" * 90)
    for r in rows:
        print("{:<5} {:<30} {:<20} {:<6} {:<12} {:<10}".format(r["book_id"], r["title"][:28], str(r["author"] or "")[:18], str(r["year"] or ""), r["total_copies"], r["available_copies"]))


def search_books(keyword):
    conn = get_db_conn()
    cur = conn.cursor()
    pattern = f"%{keyword}%"
    rows = cur.execute("SELECT * FROM books WHERE title LIKE ? OR author LIKE ? OR isbn LIKE ?", (pattern, pattern, pattern)).fetchall()
    conn.close()
    if not rows:
        print("No matching books found.")
        return

    for r in rows:
        print(f"ID: {r['book_id']} | {r['title']} - {r['author']} ({r['year']}) | Total: {r['total_copies']} Avail: {r['available_copies']}")




def add_member(name, email=None, phone=None):
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO members (name, email, phone) VALUES (?, ?, ?)", (name, email, phone))
    conn.commit()
    conn.close()
    print("Member added.")


def list_members():
    conn = get_db_conn()
    cur = conn.cursor()
    rows = cur.execute("SELECT * FROM members ORDER BY name").fetchall()
    conn.close()
    if not rows:
        print("No members yet.")
        return
    print("{:<5} {:<25} {:<25} {:<15}".format("ID", "Name", "Email", "Phone"))
    print("-" * 80)
    for r in rows:
        print("{:<5} {:<25} {:<25} {:<15}".format(r["member_id"], r["name"][:24], r["email"] or "", r["phone"] or ""))




def issue_book(book_id, member_id, days=14):
    conn = get_db_conn()
    cur = conn.cursor()

    book = cur.execute("SELECT * FROM books WHERE book_id = ?", (book_id,)).fetchone()
    member = cur.execute("SELECT * FROM members WHERE member_id = ?", (member_id,)).fetchone()

    if not book:
        print("Book not found.")
        conn.close()
        return
    if not member:
        print("Member not found.")
        conn.close()
        return
    if book["available_copies"] <= 0:
        print("No available copies to issue.")
        conn.close()
        return

    issue_date = datetime.date.today()
    due_date = issue_date + datetime.timedelta(days=days)

    cur.execute(
        "INSERT INTO issues (book_id, member_id, issue_date, due_date) VALUES (?, ?, ?, ?)",
        (book_id, member_id, issue_date.isoformat(), due_date.isoformat())
    )

    cur.execute("UPDATE books SET available_copies = available_copies - 1 WHERE book_id = ?", (book_id,))
    conn.commit()
    conn.close()
    print(f"Book issued to {member['name']}. Due on {due_date.isoformat()}.")


def return_book(issue_id):
    conn = get_db_conn()
    cur = conn.cursor()
    issue = cur.execute("SELECT * FROM issues WHERE issue_id = ?", (issue_id,)).fetchone()
    if not issue:
        print("No such issue record.")
        conn.close()
        return
    if issue["return_date"] is not None:
        print("This book has already been returned on", issue["return_date"])
        conn.close()
        return

    return_date = datetime.date.today().isoformat()
    cur.execute("UPDATE issues SET return_date = ? WHERE issue_id = ?", (return_date, issue_id))
    cur.execute("UPDATE books SET available_copies = available_copies + 1 WHERE book_id = ?", (issue["book_id"],))
    conn.commit()
    conn.close()
    print("Book returned. Thank you.")


def list_issued_books(show_all=False):
    conn = get_db_conn()
    cur = conn.cursor()
    if show_all:
        rows = cur.execute("SELECT i.issue_id, b.title, m.name, i.issue_date, i.due_date, i.return_date FROM issues i JOIN books b ON i.book_id=b.book_id JOIN members m ON i.member_id=m.member_id ORDER BY i.issue_date DESC").fetchall()
    else:
        rows = cur.execute("SELECT i.issue_id, b.title, m.name, i.issue_date, i.due_date FROM issues i JOIN books b ON i.book_id=b.book_id JOIN members m ON i.member_id=m.member_id WHERE i.return_date IS NULL ORDER BY i.due_date").fetchall()
    conn.close()

    if not rows:
        print("No issued books found.")
        return
    if show_all:
        print("{:<5} {:<30} {:<20} {:<12} {:<12} {:<12}".format("ID", "Title", "Member", "Issued", "Due", "Returned"))
        print("-" * 100)
        for r in rows:
            print("{:<5} {:<30} {:<20} {:<12} {:<12} {:<12}".format(r["issue_id"], r["title"][:28], r["name"][:18], r["issue_date"], r["due_date"], r["return_date"] or "-"))
    else:
        print("{:<5} {:<30} {:<20} {:<12} {:<12}".format("ID", "Title", "Member", "Issued", "Due"))
        print("-" * 90)
        for r in rows:
            due = datetime.date.fromisoformat(r["due_date"])
            overdue = " (OVERDUE)" if due < datetime.date.today() else ""
            print("{:<5} {:<30} {:<20} {:<12} {:<12}".format(r["issue_id"], r["title"][:28], r["name"][:18], r["issue_date"], r["due_date"] + overdue))




def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


def pause():
    input("Press Enter to continue...")


def main_menu():
    menu = textwrap.dedent("""
    ===== Library Management System =====
    1. Add book
    2. Update book
    3. Delete book
    4. List books
    5. Search books
    6. Add member
    7. List members
    8. Issue book
    9. Return book
    10. List issued books (open)
    11. List all issue records
    12. Exit
    """)
    while True:
        clear_screen()
        print(menu)
        choice = input("Choose an option > ").strip()
        try:
            c = int(choice)
        except ValueError:
            print("Please enter a number.")
            pause()
            continue

        if c == 1:
            title = input("Title: ")
            author = input("Author: ")
            year = input("Year (optional): ")
            isbn = input("ISBN (optional): ")
            copies = input("Number of copies (default 1): ") or "1"
            try:
                year_v = int(year) if year else None
                copies_v = int(copies)
            except ValueError:
                print("Year and copies must be numbers.")
                pause()
                continue
            add_book(title, author or None, year_v, isbn or None, copies_v)
            pause()

        elif c == 2:
            book_id = input("Book ID to update: ")
            try:
                bid = int(book_id)
            except ValueError:
                print("Invalid ID.")
                pause()
                continue
            print("Leave fields blank to keep existing value.")
            title = input("New title: ") or None
            author = input("New author: ") or None
            year = input("New year: ") or None
            isbn = input("New ISBN: ") or None
            total = input("New total copies (enter number): ") or None
            try:
                year_v = int(year) if year else None
                total_v = int(total) if total else None
            except ValueError:
                print("Year and total must be numbers.")
                pause()
                continue
            update_book(bid, title, author, year_v, isbn, total_v)
            pause()

        elif c == 3:
            bid = input("Book ID to delete: ")
            try:
                delete_book(int(bid))
            except ValueError:
                print("Invalid ID.")
            pause()

        elif c == 4:
            list_books()
            pause()

        elif c == 5:
            kw = input("Search keyword (title/author/isbn): ")
            search_books(kw)
            pause()

        elif c == 6:
            name = input("Member name: ")
            email = input("Email (optional): ")
            phone = input("Phone (optional): ")
            add_member(name, email or None, phone or None)
            pause()

        elif c == 7:
            list_members()
            pause()

        elif c == 8:
            bid = input("Book ID to issue: ")
            mid = input("Member ID: ")
            days = input("Days for issue (default 14): ") or "14"
            try:
                issue_book(int(bid), int(mid), int(days))
            except ValueError:
                print("IDs and days must be numbers.")
            pause()

        elif c == 9:
            iid = input("Issue ID to return: ")
            try:
                return_book(int(iid))
            except ValueError:
                print("Invalid issue ID.")
            pause()

        elif c == 10:
            list_issued_books(show_all=False)
            pause()

        elif c == 11:
            list_issued_books(show_all=True)
            pause()

        elif c == 12:
            print("Goodbye!")
            break
        else:
            print("Invalid option.")
            pause()


if __name__ == '__main__':
    init_db()
    main_menu()
