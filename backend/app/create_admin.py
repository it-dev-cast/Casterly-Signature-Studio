"""Create (or reset) a production admin login.  Run:  python -m app.create_admin --email you@company.com

The password is prompted for (never passed on the command line, so it stays out of shell history).
Use this instead of app.seed on a production database.
"""
import argparse
import getpass
import sys

from sqlalchemy import select

from app.core.security import hash_password
from app.database.database import SessionLocal
from app.database.models import User, UserRole

MIN_PASSWORD_LENGTH = 12


def run(email: str, reset: bool) -> int:
    email = email.strip().lower()
    password = getpass.getpass(f"Password for {email}: ")
    if len(password) < MIN_PASSWORD_LENGTH:
        print(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.", file=sys.stderr)
        return 1
    if getpass.getpass("Repeat password: ") != password:
        print("Passwords do not match.", file=sys.stderr)
        return 1

    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.email == email))
        if user is not None and not reset:
            print(f"{email} already exists. Re-run with --reset to set a new password.", file=sys.stderr)
            return 1
        if user is None:
            user = User(email=email, role=UserRole.ADMIN)
            db.add(user)
        user.password_hash = hash_password(password)
        user.role = UserRole.ADMIN
        user.is_active = True
        db.commit()
    finally:
        db.close()
    print(f"Admin ready: {email}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", required=True)
    parser.add_argument("--reset", action="store_true", help="reset the password of an existing account")
    args = parser.parse_args()
    sys.exit(run(args.email, args.reset))
