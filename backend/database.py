
# SQLite database ko use karne ke liye library import ki
import sqlite3

# File aur folder paths manage karne ke liye
from pathlib import Path


# ==========================================
# 1. DATABASE FILE PATH
# ==========================================

# Current file -> backend folder -> project root -> studymate.db
DB_PATH = Path(__file__).resolve().parent.parent / "studymate.db"


# ==========================================
# 2. DATABASE CONNECTION
# ==========================================

def get_connection():

    # SQLite database se connection establish karo
    connection = sqlite3.connect(DB_PATH)

    # Database records ko column names se access kar sakte hain
    connection.row_factory = sqlite3.Row

    # Har connection par foreign key checking enable karo
    connection.execute("PRAGMA foreign_keys = ON")

    return connection


# ==========================================
# 3. CREATE DATABASE TABLES
# ==========================================

def create_tables():

    with get_connection() as connection:

        # --------------------------------------
        # USERS TABLE
        # --------------------------------------

        # New users ke account details store karta hai
        connection.execute("""
            CREATE TABLE IF NOT EXISTS users (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                full_name TEXT NOT NULL,

                email TEXT NOT NULL UNIQUE,

                password_hash TEXT NOT NULL,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

            )
        """)

        # --------------------------------------
        # QUIZ HISTORY TABLE
        # --------------------------------------

        # Har user's quiz result store karta hai
        connection.execute("""
            CREATE TABLE IF NOT EXISTS quiz_history (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                user_id INTEGER,

                pdf_name TEXT NOT NULL,

                total_questions INTEGER NOT NULL,

                correct_answers INTEGER NOT NULL,

                score_percentage REAL NOT NULL,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (user_id) REFERENCES users(id)

            )
        """)

        # Database changes save karo
        connection.commit()


# ==========================================
# 4. MIGRATE EXISTING DATABASE
# ==========================================

def migrate_quiz_history():

    with get_connection() as connection:

        # Existing quiz_history table ke columns check karo
        columns = connection.execute(
            "PRAGMA table_info(quiz_history)"
        ).fetchall()

        # Column names ki list banao
        column_names = [
            column["name"] for column in columns
        ]

        # Agar user_id column missing hai toh add karo
        if "user_id" not in column_names:

            connection.execute("""
                ALTER TABLE quiz_history
                ADD COLUMN user_id INTEGER REFERENCES users(id)
            """)

            connection.commit()


# ==========================================
# 5. SAVE QUIZ RESULT
# ==========================================

def save_quiz_result(
    user_id,
    pdf_name,
    total_questions,
    correct_answers
):

    # Total questions zero ya negative nahi hone chahiye
    if total_questions <= 0:
        raise ValueError(
            "Total questions must be greater than zero."
        )

    # Correct answers valid range mein hone chahiye
    if not 0 <= correct_answers <= total_questions:
        raise ValueError(
            "Invalid correct answers count."
        )

    # Quiz percentage calculate karo
    percentage = (
        correct_answers / total_questions
    ) * 100

    with get_connection() as connection:

        # Quiz result ko user_id ke saath save karo
        connection.execute(
            """
            INSERT INTO quiz_history
            (
                user_id,
                pdf_name,
                total_questions,
                correct_answers,
                score_percentage
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                user_id,
                pdf_name,
                total_questions,
                correct_answers,
                percentage
            )
        )

        connection.commit()


# ==========================================
# 6. GET QUIZ HISTORY
# ==========================================

def get_quiz_history(user_id):

    with get_connection() as connection:

        # Sirf logged-in user ki quiz history fetch karo
        # Latest quiz sabse pehle show hoga
        history = connection.execute(
            """
            SELECT *
            FROM quiz_history
            WHERE user_id = ?
            ORDER BY created_at DESC
            """,
            (user_id,)
        ).fetchall()

    return history


# ==========================================
# 7. GET USER DETAILS
# ==========================================

def get_user_by_email(email):

    # Email ke through user search karo
    email = email.strip().lower()

    with get_connection() as connection:

        user = connection.execute(
            """
            SELECT id, full_name, email, created_at
            FROM users
            WHERE email = ?
            """,
            (email,)
        ).fetchone()

    return user
