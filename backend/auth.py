
import hashlib
import hmac
import secrets
import re

from backend.database import get_connection


# ==========================================
# 1. PASSWORD HASHING
# ==========================================

def hash_password(password):

    # Har password ke liye random salt generate karo
    salt = secrets.token_bytes(16)

    # Password ko PBKDF2 algorithm se hash karo
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        600000
    )

    # Salt aur hashed password ko string mein convert karo
    return salt.hex() + ":" + password_hash.hex()


# ==========================================
# 2. PASSWORD VERIFICATION
# ==========================================

def verify_password(password, stored_password):

    try:

        # Database se saved salt aur hash alag karo
        salt_hex, hash_hex = stored_password.split(":")

        salt = bytes.fromhex(salt_hex)

        # User ke entered password ka hash banao
        new_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            600000
        )

        # Saved hash aur new hash compare karo
        return hmac.compare_digest(
            new_hash,
            bytes.fromhex(hash_hex)
        )

    except (ValueError, TypeError):
        return False


# ==========================================
# 3. USER REGISTRATION
# ==========================================

def register_user(full_name, email, password):

    # Input values clean karo
    full_name = full_name.strip()
    email = email.strip().lower()

    # Name validation
    if not full_name:
        return False, "Please enter your name."

    # Email validation
    if not re.fullmatch(
        r"[^@\s]+@[^@\s]+\.[^@\s]+",
        email
    ):
        return False, "Please enter a valid email."

    # Password length validation
    if len(password) < 8:
        return False, "Password must contain at least 8 characters."

    # Password hash generate karo
    password_hash = hash_password(password)

    try:

        # Database connection open karo
        with get_connection() as connection:

            # New user ka record insert karo
            connection.execute(
                """
                INSERT INTO users
                (full_name, email, password_hash)
                VALUES (?, ?, ?)
                """,
                (
                    full_name,
                    email,
                    password_hash
                )
            )

            connection.commit()

        return True, "Registration successful!"

    except Exception as e:

        # Duplicate email ko handle karo
        if "UNIQUE constraint failed" in str(e):
            return False, "This email is already registered."

        return False, f"Registration failed: {e}"


# ==========================================
# 4. USER LOGIN
# ==========================================

def authenticate_user(email, password):

    # Email clean karo
    email = email.strip().lower()

    # Database se user search karo
    with get_connection() as connection:

        user = connection.execute(
            """
            SELECT *
            FROM users
            WHERE email = ?
            """,
            (email,)
        ).fetchone()

    # Agar user nahi mila
    if user is None:
        return None

    # Password verify karo
    if verify_password(
        password,
        user["password_hash"]
    ):

        # Password hash ko return mat karo
        return {
            "id": user["id"],
            "full_name": user["full_name"],
            "email": user["email"]
        }

    # Wrong password
    return None
