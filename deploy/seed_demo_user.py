"""Create the reviewer's demo account if it is not already there."""
import os
import sys

sys.path.insert(0, "/app")

from sqlalchemy import create_engine, text

from backend.config import settings
from backend.utils import get_password_hash

USERNAME = os.environ.get("DEMO_USERNAME", "reviewer")
PASSWORD = os.environ.get("DEMO_PASSWORD", "rekomme")

engine = create_engine(settings.POSTGRES_URI)
with engine.begin() as conn:
    exists = conn.execute(
        text("SELECT 1 FROM public.users WHERE username = :u"), {"u": USERNAME}
    ).first()
    if exists:
        print(f"Demo user '{USERNAME}' already present")
    else:
        conn.execute(
            text(
                "INSERT INTO public.users (username, password, email, full_name, active) "
                "VALUES (:u, :p, :e, :f, TRUE)"
            ),
            {
                "u": USERNAME,
                "p": get_password_hash(PASSWORD),
                "e": f"{USERNAME}@example.com",
                "f": "Demo Reviewer",
            },
        )
        print(f"Created demo user '{USERNAME}'")
