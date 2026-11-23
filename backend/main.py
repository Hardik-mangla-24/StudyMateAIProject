
from backend.database import create_tables, migrate_quiz_history

if __name__ == "__main__":

    # Required database tables create karo
    create_tables()

    # Existing database ko new structure mein migrate karo
    migrate_quiz_history()

    print("StudyMate AI database initialized successfully!")
    print("Users and Quiz History tables ready!")
