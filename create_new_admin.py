"""
Create or update the default admin user (sara_admin@gmail.com / admin123).
Ensures user exists in users and has an entry in admins table.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.utils import db, get_pool, close_pool
from backend.utils.constants import Roles
from backend.services.auth_service import get_password_hash

async def create_new_admin():
    """Create a new admin account."""
    try:
        await get_pool()
        
        admin_email = "sara_admin@gmail.com"
        admin_password = "admin123"
        admin_name = "Sara Admin"
        admin_phone = "9999999999"
        
        existing_user = await db.fetch_one(
            "SELECT user_id FROM users WHERE email = $1",
            admin_email
        )
        
        if existing_user:
            print(f"User with email {admin_email} already exists.")
            user_id = existing_user['user_id']
            
            hashed_password = get_password_hash(admin_password)
            await db.execute(
                "UPDATE users SET password_hash = $1 WHERE user_id = $2",
                hashed_password,
                user_id
            )
            print(f"✓ Password updated for {admin_email}")
        else:
            hashed_password = get_password_hash(admin_password)
            
            result = await db.fetch_one(
                """
                INSERT INTO users (full_name, email, phone, password_hash, role)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING user_id
                """,
                admin_name,
                admin_email,
                admin_phone,
                hashed_password,
                Roles.ADMIN
            )
            
            user_id = result['user_id']
            print(f"✓ New admin user created: {admin_email}")
        
        existing_admin = await db.fetch_one(
            "SELECT admin_id FROM admins WHERE user_id = $1",
            user_id
        )
        
        if not existing_admin:
            await db.execute(
                """
                INSERT INTO admins (user_id, created_at)
                VALUES ($1, NOW())
                """,
                user_id
            )
            print(f"✓ Admin entry created in admins table")
        else:
            print(f"✓ Admin entry already exists")
        
        print("\n" + "=" * 60)
        print("NEW ADMIN LOGIN CREDENTIALS:")
        print("=" * 60)
        print(f"Email:    {admin_email}")
        print(f"Password: {admin_password}")
        print("\nAdmin Portal: http://localhost:8000/static/admin/admin_login.html")
        print("=" * 60)
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await close_pool()

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(create_new_admin())
