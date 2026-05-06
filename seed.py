"""
Minimal seed: ensures default admin (sara_admin@gmail.com) and sample citizen (citizen@spgrs.com) exist.
Run after create_database.py if you need these users without re-running full DB setup.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.utils import db, Roles, get_pool, close_pool
from backend.services.auth_service import get_password_hash


async def seed_data():
    try:
        await get_pool()
        print("Database connected.")

        admin_email = "sara_admin@gmail.com"
        admin_pass = "admin123"
        
        row = await db.fetch_one("SELECT user_id FROM users WHERE email = $1", admin_email)
        
        if not row:
            print(f"Creating admin user: {admin_email}")
            result = await db.fetch_one(
                """
                INSERT INTO users (full_name, email, phone, password_hash, role)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING user_id
                """,
                "System Admin", admin_email, "9999999999", get_password_hash(admin_pass), Roles.ADMIN
            )
            user_id = result['user_id']
            
            await db.execute(
                """
                INSERT INTO admins (user_id)
                VALUES ($1)
                """,
                user_id
            )
            print("Admin user created.")
        else:
            print(f"Admin user {admin_email} already exists.")

        user_email = "citizen@spgrs.com"
        user_pass = "user123"
        
        row = await db.fetch_one("SELECT user_id FROM users WHERE email = $1", user_email)
        
        if not row:
            print(f"Creating sample citizen: {user_email}")
            await db.execute(
                """
                INSERT INTO users (full_name, email, phone, password_hash, role)
                VALUES ($1, $2, $3, $4, $5)
                """,
                "John Doe", user_email, "8888888888", get_password_hash(user_pass), Roles.USER
            )
            print("Sample citizen created.")
        else:
            print(f"User {user_email} already exists.")
            
    except Exception as e:
        print(f"Error seeding data: {e}")
    finally:
        await close_pool()


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(seed_data())
