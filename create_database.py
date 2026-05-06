"""
SPGRS Database Setup Script
============================
Creates the database (if not exists), drops all tables, recreates them,
and seeds with initial data. Passwords are bcrypt-hashed.

Uses config/settings (and .env) for database credentials.

Usage:
    python create_database.py
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import asyncpg
from config import get_settings

settings = get_settings()


async def create_database_if_not_exists():
    """Connect to the default 'postgres' database and create our DB if missing."""
    print(f"[1/4] Checking if database '{settings.DB_NAME}' exists...")
    conn = await asyncpg.connect(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        database="postgres",
    )
    try:
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", settings.DB_NAME
        )
        if exists:
            print(f"  -> Database '{settings.DB_NAME}' already exists. Skipping creation.")
        else:
            await conn.execute(f'CREATE DATABASE "{settings.DB_NAME}"')
            print(f"  -> Database '{settings.DB_NAME}' created successfully.")
    finally:
        await conn.close()


DROP_TABLES_SQL = """
DROP TABLE IF EXISTS notifications CASCADE;
DROP TABLE IF EXISTS feedback CASCADE;
DROP TABLE IF EXISTS duplicate_grievances CASCADE;
DROP TABLE IF EXISTS peer_validations CASCADE;
DROP TABLE IF EXISTS grievance_assignments CASCADE;
DROP TABLE IF EXISTS priorities CASCADE;
DROP TABLE IF EXISTS sentiment_analysis CASCADE;
DROP TABLE IF EXISTS grievance_attachments CASCADE;
DROP TABLE IF EXISTS grievances CASCADE;
DROP TABLE IF EXISTS admins CASCADE;
DROP TABLE IF EXISTS departments CASCADE;
DROP TABLE IF EXISTS categories CASCADE;
DROP TABLE IF EXISTS locations CASCADE;
DROP TABLE IF EXISTS users CASCADE;
"""


CREATE_TABLES_SQL = """
-- Users table (email and phone are unique; password stored as bcrypt hash only)
CREATE TABLE users (
    user_id     SERIAL PRIMARY KEY,
    full_name   VARCHAR(150) NOT NULL,
    email       VARCHAR(255) NOT NULL UNIQUE,
    phone       VARCHAR(20) UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role        VARCHAR(20) NOT NULL DEFAULT 'USER',
    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Admins table
CREATE TABLE admins (
    admin_id    SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Locations table
CREATE TABLE locations (
    location_id SERIAL PRIMARY KEY,
    state       VARCHAR(100) NOT NULL,
    district    VARCHAR(100) NOT NULL,
    zone_name   VARCHAR(150),
    ward        VARCHAR(20),
    place_name  VARCHAR(200) NOT NULL
);

-- Categories table
CREATE TABLE categories (
    category_id   SERIAL PRIMARY KEY,
    category_name VARCHAR(150) NOT NULL UNIQUE
);

-- Departments table
CREATE TABLE departments (
    department_id   SERIAL PRIMARY KEY,
    department_name VARCHAR(200) NOT NULL,
    trust_score     NUMERIC(3,2) NOT NULL DEFAULT 0.50
);

-- Grievances table
CREATE TABLE grievances (
    grievance_id  VARCHAR(10) PRIMARY KEY,
    user_id       INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    category_id   INTEGER NOT NULL REFERENCES categories(category_id),
    location_id   INTEGER NOT NULL REFERENCES locations(location_id),
    complaint_text TEXT NOT NULL,
    status        VARCHAR(20) NOT NULL DEFAULT 'SUBMITTED',
    created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Grievance attachments table
CREATE TABLE grievance_attachments (
    attachment_id SERIAL PRIMARY KEY,
    grievance_id  VARCHAR(10) NOT NULL REFERENCES grievances(grievance_id) ON DELETE CASCADE,
    file_url      TEXT NOT NULL,
    file_type     VARCHAR(20) NOT NULL DEFAULT 'IMAGE',
    public_id     VARCHAR(255),
    original_name VARCHAR(255),
    uploaded_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Sentiment analysis table
CREATE TABLE sentiment_analysis (
    sentiment_id   SERIAL PRIMARY KEY,
    grievance_id   VARCHAR(10) NOT NULL REFERENCES grievances(grievance_id) ON DELETE CASCADE,
    compound_score NUMERIC(4,2) NOT NULL,
    analyzed_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Priorities table
CREATE TABLE priorities (
    priority_id    SERIAL PRIMARY KEY,
    grievance_id   VARCHAR(10) NOT NULL REFERENCES grievances(grievance_id) ON DELETE CASCADE,
    priority_level VARCHAR(20) NOT NULL DEFAULT 'MEDIUM',
    calculated_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Peer validations table
CREATE TABLE peer_validations (
    validation_id SERIAL PRIMARY KEY,
    grievance_id  VARCHAR(10) NOT NULL REFERENCES grievances(grievance_id) ON DELETE CASCADE,
    user_id       INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    validated_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(grievance_id, user_id)
);

-- Grievance assignments table
CREATE TABLE grievance_assignments (
    assignment_id  SERIAL PRIMARY KEY,
    grievance_id   VARCHAR(10) NOT NULL REFERENCES grievances(grievance_id) ON DELETE CASCADE,
    department_id  INTEGER NOT NULL REFERENCES departments(department_id),
    admin_id       INTEGER REFERENCES admins(admin_id),
    assigned_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Duplicate grievances table
CREATE TABLE duplicate_grievances (
    id                  SERIAL PRIMARY KEY,
    parent_grievance_id VARCHAR(10) NOT NULL REFERENCES grievances(grievance_id) ON DELETE CASCADE,
    child_grievance_id  VARCHAR(10) NOT NULL REFERENCES grievances(grievance_id) ON DELETE CASCADE,
    created_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Feedback table
CREATE TABLE feedback (
    feedback_id   SERIAL PRIMARY KEY,
    grievance_id  VARCHAR(10) NOT NULL REFERENCES grievances(grievance_id) ON DELETE CASCADE,
    user_id       INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    rating        INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
    comments      TEXT,
    submitted_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Notifications table
CREATE TABLE notifications (
    notification_id SERIAL PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    message         TEXT NOT NULL,
    is_read         BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_grievances_user_id ON grievances(user_id);
CREATE INDEX idx_grievances_status ON grievances(status);
CREATE INDEX idx_grievances_category ON grievances(category_id);
CREATE INDEX idx_grievances_location ON grievances(location_id);
CREATE INDEX idx_grievances_created ON grievances(created_at DESC);
CREATE INDEX idx_sentiment_grievance ON sentiment_analysis(grievance_id);
CREATE INDEX idx_priorities_grievance ON priorities(grievance_id);
CREATE INDEX idx_peer_validations_grievance ON peer_validations(grievance_id);
CREATE INDEX idx_assignments_grievance ON grievance_assignments(grievance_id);
CREATE INDEX idx_notifications_user ON notifications(user_id, is_read);
CREATE INDEX idx_feedback_grievance ON feedback(grievance_id);
CREATE INDEX idx_locations_district ON locations(district);
CREATE INDEX idx_locations_place ON locations(place_name);
"""


async def seed_data(conn):
    """Insert all seed data with bcrypt-hashed passwords."""
    from passlib.context import CryptContext
    from datetime import datetime
    pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def dt(s):
        """Convert timestamp string to datetime object."""
        return datetime.strptime(s, '%Y-%m-%d %H:%M:%S')

    print("  Inserting users...")
    users = [
        ('Sara Administrator', 'sara_admin@gmail.com', '9443000001', pwd.hash('admin123'), 'ADMIN', dt('2025-10-15 09:30:00')),
        ('Testing User', 'testing@gmail.com', '9000000010', pwd.hash('testing123'), 'USER', dt('2026-01-20 14:15:00')),
        ('Arunachalam M', 'arun.murugan@gmail.com', '9442100234', pwd.hash('pass1234'), 'USER', dt('2025-11-02 10:45:22')),
        ('Lakshmi Priya', 'lakshmi.priya@yahoo.com', '9487567890', pwd.hash('lakshmi456'), 'USER', dt('2025-11-10 13:20:11')),
        ('Raja Sekar', 'raja.sekar@outlook.com', '9623412345', pwd.hash('raja7890'), 'USER', dt('2025-11-25 16:55:33')),
        ('Meenakshi Sundaram', 'meena.sundar@gmail.com', '7598234567', pwd.hash('meena2025'), 'USER', dt('2025-12-05 09:10:44')),
        ('Karthikeyan P', 'karthik.pandian@hotmail.com', '6385123456', pwd.hash('karthi111'), 'USER', dt('2025-12-12 11:30:19')),
        ('Divya Bharathi', 'divya.bharathi@gmail.com', '9445678901', pwd.hash('divya@2026'), 'USER', dt('2025-12-28 15:40:55')),
        ('Suresh Kumar V', 'suresh.kumarv@gmail.com', '8123987654', pwd.hash('suresh555'), 'USER', dt('2026-01-08 08:25:30')),
        ('Padmavathi R', 'padma.rani@yahoo.com', '9842156789', pwd.hash('padma777'), 'USER', dt('2026-01-15 12:10:47')),
        ('Muthu Krishnan', 'muthu.krish@gmail.com', '9621345678', pwd.hash('muthu999'), 'USER', dt('2026-01-25 17:05:12')),
        ('Anitha Selvi', 'anitha.selvi@proton.me', '9443123789', pwd.hash('anitha321'), 'USER', dt('2026-02-01 10:35:22')),
        ('Vigneshwaran S', 'vignesh.s@gmail.com', '7598765432', pwd.hash('vignesh@22'), 'USER', dt('2026-02-05 14:50:33')),
        ('Saranya Devi', 'saranya.devi@gmail.com', '6385012345', pwd.hash('saranya88'), 'USER', dt('2026-02-10 09:15:44')),
    ]
    await conn.executemany(
        "INSERT INTO users (full_name, email, phone, password_hash, role, created_at) VALUES ($1,$2,$3,$4,$5,$6)",
        users
    )

    print("  Inserting locations...")
    locations = [
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '1', 'Nalmeippar Nagar'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '1', 'Chidambara Nagar'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '1', 'India Cements Colony'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '1', 'Ganapathi Mill Colony'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '1', 'Indira Nagar'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '1', 'Theneerkulam'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '1', 'Madurai Road'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '1', 'Valaja North Street'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '1', 'Senaiyar Street'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '2', 'Melakarai Pillaiyar Kovil Street'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '2', 'Tharapuram Main'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '2', 'CSI Church Street'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '2', 'Rajaji Street'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '2', 'Sundarapuram'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '2', 'Karaieruppu'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '2', 'Uchimahali Amman Kovil Street'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '2', 'Melakarai Kamarajar Street'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '3', 'Balaji Avenue'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '3', 'Grama Savadi Street'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '3', 'Mela Urudayarpuram'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '3', 'Mela Agraharam'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '3', 'Ananthapuram'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '3', 'Mathagadi Street'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '3', 'Sivasakthi Road'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '3', 'Ulagamman Kovil Street'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '4', 'New Street I'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '4', 'New Street II'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '4', 'K.N. Street'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '4', 'Thirumalai Nagar'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '4', 'Ganapathy Garden'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '4', 'Chattram Puthukulam'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '5', 'Tirunelveli Junction'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '5', 'Station Road'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '5', 'Meenakshipuram'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '5', 'Kailasapuram'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '5', 'Madurai Road Junction'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '5', 'Railway Colony'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '6', 'V.G. Rao Nagar'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '6', 'B-Sector Main Road'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '6', 'Jeganatha Nagar'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '6', 'Pillaiyar Kovil Street'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '6', 'A-Sector Streets'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '7', 'Bharathi Extension'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '7', 'Nethaji Road'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '7', 'V.O.C. Street'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '7', 'BHEL Nagar'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '7', 'Kasthuribai Street'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '7', 'Jaganatha Street'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '8', 'Kokkirakulam'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '8', 'Mariamman Kovil Street'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '8', 'Manakudavar Street'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '8', 'Selva Vinayagar Kovil Street'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '8', 'Thiru Nalaiku Povar Street'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '9', 'District Court Area'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '9', 'Collectorate Campus Streets'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '9', 'Kokkirakulam Main Road'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '9', 'Government Quarters'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '10', 'Thatchanallur North'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '10', 'Mettu Street'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '10', 'Peryaamman Kovil Street'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '10', 'South Street Thatchanallur'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '11', 'Udayarpatti'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '11', 'Salai Street'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '11', 'Manimoortheeswaram Road'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '11', 'North Car Street'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '12', 'Thatchanallur Bazaar'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '12', 'Railway Station Road Thatchai'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '12', 'Pillaiyar Kovil Street'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '13', 'Kamaraj Nagar'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '13', 'Ambedkar Nagar'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '13', 'Palkattalai East'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '13', 'Gramachavadi West'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '14', 'Theneerkulam New Colony'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '14', 'Durgai Amman Kovil Street'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '14', 'Paulpannai Street'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '14', 'Keela Mel Mudukku'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '15', 'Tirunelveli Town Arch Area'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '15', 'West Car Street'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '15', 'Nellaiappar High Road'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '15', 'South Mount Road'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '16', 'Tirunelveli Town Bazaar'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '16', 'North Car Street'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '16', 'Amman Sannathi'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '16', 'Swamy Sannathi'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '17', 'Rahmath Nagar'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '17', 'Maharaja Nagar North'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '17', 'High Ground'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '17', 'Tiruchendur Road'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '18', 'Velavar Colony'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '18', 'Perumalpuram'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '18', 'Lourdunathan Street'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '18', 'NGO A Colony'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '19', 'Kumaresan Nagar'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '19', 'Tiruchendur Main Road'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '19', 'TVS Nagar'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '19', 'Anbu Nagar'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '20', 'Vannarpettai'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '20', 'South Bypass Road'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '20', 'Chellapandian Flyover Area'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '20', 'Perumal Kovil Street'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '21', 'Vannarpettai North'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '21', 'River Bank Street'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '21', 'Vivekananda Street'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '21', 'Thiru-vi-ka Street'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '22', 'Pettai Industrial Estate'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '22', 'Cheranmahadevi Road'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '22', 'Puthumali Street'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '22', 'Main Bazaar Pettai'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '23', 'Pettai Town'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '23', 'Old Pettai North Street'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '23', 'Munsif Court Street'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '23', 'Police Station Road'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '24', 'Narasinganallur'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '24', 'River View Colony'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '24', 'Pettai West'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '24', 'Amman Kovil Street'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '25', 'Kondanagaram Road'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '25', 'Pettai Rural'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '25', 'Gandhi Nagar'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '25', 'Kamarajar Street'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '26', 'Sivanthipatti Road'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '26', 'Thiagaraja Nagar'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '26', 'V.M. Chattram'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '26', 'Housing Board Colony'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '27', 'NGO B Colony'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '27', 'Thirunagar'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '27', 'Amala School Area'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '27', 'Perumalpuram South'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '28', 'Manur Road'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '28', 'Thatchanallur Rural'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '28', 'Karisalpatti'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '28', 'Pillaiyar Kovil Street'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '29', 'Kurinji Nagar'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '29', 'Sankar Nagar'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '29', 'Talaiyuthu Road'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '29', 'Cements Nagar'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '30', 'Vannarpettai Junction'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '30', 'Bypass Service Road'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '30', 'Near District Science Centre'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '31', 'Melapalayam Bazaar'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '31', 'Hameempuram'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '31', 'Post Office Street'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '31', 'Big Mosque Street'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '32', 'Palayamkottai Bus Stand Area'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '32', 'Market Street'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '32', 'Police Quarters'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '32', 'South Car Street'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '33', 'St. Johns College Area'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '33', 'High Ground Hospital Road'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '33', 'Medical College Colony'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '34', 'Palayamkottai Central'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '34', 'Jawahar Nagar'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '34', 'VOC Ground Area'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '34', 'Prison Road'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '35', 'Shanthi Nagar'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '35', 'KTC Nagar West'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '35', 'Palay Main Road'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '36', 'KTC Nagar East'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '36', 'Maharaja Nagar South'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '36', 'Input Road'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '37', 'V.M. Chattram Main'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '37', 'Kamaraj Salai'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '37', 'Valluvar Nagar'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '38', 'Samathanapuram'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '38', 'High Road Palay'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '38', 'Bell Amusement Park Area'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '39', 'Murugankurichi'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '39', 'Clock Tower Area'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '39', 'Head Post Office Road'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '40', 'Melapalayam West'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '40', 'Malampattai Street'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '40', 'Karim Nagar'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '41', 'Melapalayam North'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '41', 'Nethaji Road'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '41', 'Alif Nagar'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '42', 'Melapalayam Central'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '42', 'Quaithe Millath Nagar'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '42', 'New Street'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '43', 'Melapalayam South'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '43', 'Rahmath Nagar South'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '43', 'Madina Nagar'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '44', 'Kurichi'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '44', 'River Side Melapalayam'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '44', 'Anwarabad'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '45', 'Melapalayam Rural'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '45', 'VST Nagar'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '45', 'Ambedkar Nagar Melapalayam'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '46', 'Melapalayam Bazaar Road'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '46', 'Vannar Street'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '46', 'Market Lane'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '47', 'Melapalayam East'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '47', 'Asath Nagar'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '47', 'Muthumariamman Kovil Street'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '48', 'Sasthri Nagar'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '48', 'Rail Nagar'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '48', 'Pothigai Nagar'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '49', 'Kulavanigarpuram'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '49', 'Railway Gate Area'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '49', 'South Bypass Road'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '50', 'M.S.K. Nagar'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '50', 'Burkitmanagar'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '50', 'Melapalayam Bypass'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '51', 'Konnadi Street'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '51', 'Melapalayam Junction'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '51', 'Bus Stop Area'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '52', 'Melapalayam Industrial Area'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '52', 'Tannery Road'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '52', 'Kamaraj Street'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '53', 'Kurichi North'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '53', 'Pillaiyar Kovil Street'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '53', 'Main Road Kurichi'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '54', 'Kurichi South'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '54', 'Mariamman Kovil Street'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '54', 'School Street'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '55', 'Palayamkottai Rural'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '55', 'Reddiarpatti Road'),
        ('Tamil Nadu', 'Tirunelveli', 'TIRUNELVELI ZONE', '55', 'Itteri Road'),
    ]
    await conn.executemany(
        "INSERT INTO locations (state, district, zone_name, ward, place_name) VALUES ($1,$2,$3,$4,$5)",
        locations
    )

    print("  Inserting categories...")
    categories = [
        ('Water Supply',), ('Electricity/Power',), ('Garbage Collection',),
        ('Road Maintenance',), ('Hospital Services',), ('Public Park',),
        ('Street Lighting',), ('Noise Pollution',), ('Public Transport',),
        ('Tree Maintenance',), ('Internet Services',), ('Security/Safety',),
        ('Traffic Management',), ('Drainage & Flooding',), ('Drinking Water Quality',),
        ('Street Vendor / Encroachment',), ('Mosquito / Vector Control',),
        ('Public Toilet / Sanitation',), ('Illegal Construction / Land Issue',),
        ('Animal Stray / Cattle Menace',),
    ]
    await conn.executemany(
        "INSERT INTO categories (category_name) VALUES ($1)", categories
    )

    print("  Inserting departments...")
    departments = [
        ('Water Supply Department', 0.48), ('Electricity Board (TNEB)', 0.41),
        ('Solid Waste Management', 0.55), ('Roads & Highways / Municipal Roads', 0.39),
        ('Public Health & Hospitals', 0.37), ('Parks & Gardens', 0.62),
        ('Street Lighting', 0.58), ('Public Transport (TNSTC)', 0.51),
        ('General Administration', 0.68), ('Traffic & Safety / Police Coordination', 0.45),
        ('Drainage & Sewerage', 0.42), ('Revenue & Land Records', 0.51),
        ('Public Works Department (PWD)', 0.46), ('Mosquito Control & Vector Borne Diseases', 0.44),
        ('Town Planning & Building Regulation', 0.50),
    ]
    await conn.executemany(
        "INSERT INTO departments (department_name, trust_score) VALUES ($1,$2)", departments
    )

    print("  Creating admin entry...")
    admin_user_id = await conn.fetchval(
        "SELECT user_id FROM users WHERE email = 'sara_admin@gmail.com'"
    )
    await conn.execute(
        "INSERT INTO admins (user_id, created_at) VALUES ($1, CURRENT_TIMESTAMP)", admin_user_id
    )

    print("  Inserting grievances...")
    grievances = [
        ('G026', 2, 1, 15, 'No water supply in West Car Street for the past 5 days.', 'SUBMITTED', dt('2026-01-05 09:12:45')),
        ('G027', 3, 2, 17, 'Frequent power cuts every evening in Rahmath Nagar.', 'IN_PROGRESS', dt('2026-01-08 14:30:22')),
        ('G028', 4, 3, 31, 'Garbage not collected for 10 days near Melapalayam Bazaar.', 'SUBMITTED', dt('2026-01-10 10:45:11')),
        ('G029', 5, 4, 23, 'Large potholes on main road in Pettai Town causing accidents.', 'IN_PROGRESS', dt('2026-01-12 16:20:33')),
        ('G030', 6, 5, 33, 'Poor hygiene and unclean wards in government hospital area.', 'SUBMITTED', dt('2026-01-15 11:55:19')),
        ('G031', 7, 6, 18, 'Broken play equipment and no lights in Perumalpuram park.', 'SUBMITTED', dt('2026-01-18 08:40:50')),
        ('G032', 8, 7, 15, 'Several street lights not working on Nellaiappar High Road.', 'IN_PROGRESS', dt('2026-01-20 13:15:44')),
        ('G033', 9, 8, 43, 'Loud music from functions after 11 PM in Rahmath Nagar South.', 'SUBMITTED', dt('2026-01-22 22:05:01')),
        ('G034', 10, 9, 32, 'Buses overcrowded and skipping stops at Palayamkottai bus stand.', 'IN_PROGRESS', dt('2026-01-25 07:35:28')),
        ('G035', 11, 10, 19, 'Dangerous hanging tree branches over road in TVS Nagar.', 'SUBMITTED', dt('2026-01-27 09:50:17')),
        ('G036', 12, 14, 36, 'Very low drinking water pressure in KTC Nagar East.', 'SUBMITTED', dt('2026-01-29 12:10:55')),
        ('G037', 13, 2, 5, 'Frequent transformer failures near Tirunelveli Junction.', 'IN_PROGRESS', dt('2026-02-01 15:25:40')),
        ('G038', 2, 3, 46, 'Overflowing garbage bins on Melapalayam Bazaar Road.', 'SUBMITTED', dt('2026-02-03 10:30:22')),
        ('G039', 3, 4, 29, 'Road completely damaged near Sankar Nagar entrance.', 'IN_PROGRESS', dt('2026-02-05 17:45:11')),
        ('G040', 4, 11, 39, 'Internet speed very slow and frequent disconnections in Murugankurichi.', 'SUBMITTED', dt('2026-02-07 08:55:33')),
        ('G041', 5, 12, 9, 'Increasing theft incidents near District Court Area at night.', 'SUBMITTED', dt('2026-02-08 19:20:19')),
        ('G042', 6, 4, 20, 'Uneven road surface and potholes on South Bypass Road Vannarpettai.', 'IN_PROGRESS', dt('2026-02-10 11:40:44')),
        ('G043', 7, 3, 51, 'Garbage piles near Melapalayam Junction bus stop not cleared.', 'SUBMITTED', dt('2026-02-11 09:15:08')),
        ('G044', 8, 1, 1, 'No piped water supply in Nalmeippar Nagar for 7 days now.', 'IN_PROGRESS', dt('2026-02-12 14:05:37')),
        ('G045', 9, 7, 16, 'Many street lights burnt out in North Car Street bazaar.', 'SUBMITTED', dt('2026-02-13 16:30:22')),
        ('G046', 10, 6, 27, 'Damaged benches and unclean park in NGO B Colony.', 'SUBMITTED', dt('2026-02-14 10:25:50')),
        ('G047', 11, 2, 40, 'Long unscheduled power cuts in Melapalayam West area.', 'IN_PROGRESS', dt('2026-02-14 18:10:11')),
        ('G048', 12, 15, 34, 'Mosquito menace and stagnant water near Palayamkottai Central.', 'SUBMITTED', dt('2026-02-14 13:55:44')),
        ('G049', 13, 9, 37, 'Irregular and delayed bus service on Kamaraj Salai route.', 'SUBMITTED', dt('2026-02-14 07:40:19')),
        ('G050', 2, 12, 11, 'Suspicious activities and lack of street patrolling in Udayarpatti.', 'IN_PROGRESS', dt('2026-02-14 21:15:33')),
        ('G051', 3, 4, 24, 'Road damage in Narasinganallur causing frequent vehicle breakdowns.', 'SUBMITTED', dt('2026-02-14 09:30:55')),
        ('G052', 4, 3, 42, 'Garbage not lifted for more than a week in Melapalayam Central.', 'IN_PROGRESS', dt('2026-02-14 12:20:08')),
        ('G053', 5, 16, 14, 'Water appears contaminated with bad smell in Theneerkulam New Colony.', 'SUBMITTED', dt('2026-02-14 11:05:22')),
        ('G054', 6, 8, 8, 'Continuous loudspeakers from temple in Kokkirakulam area.', 'SUBMITTED', dt('2026-02-14 20:45:17')),
        ('G055', 7, 10, 13, 'Large fallen tree blocking road in Kamaraj Nagar since yesterday.', 'IN_PROGRESS', dt('2026-02-14 08:50:41')),
    ]
    await conn.executemany(
        "INSERT INTO grievances (grievance_id, user_id, category_id, location_id, complaint_text, status, created_at) VALUES ($1,$2,$3,$4,$5,$6,$7)",
        grievances
    )

    print("  Inserting sentiment analysis...")
    sentiments = [
        ('G026', -0.68, dt('2026-01-05 10:05:00')), ('G027', -0.72, dt('2026-01-08 15:10:00')),
        ('G028', -0.74, dt('2026-01-10 11:20:00')), ('G029', -0.65, dt('2026-01-12 17:05:00')),
        ('G030', -0.69, dt('2026-01-15 12:30:00')), ('G031', -0.52, dt('2026-01-18 09:15:00')),
        ('G032', -0.58, dt('2026-01-20 14:00:00')), ('G033', -0.77, dt('2026-01-23 00:10:00')),
        ('G034', -0.48, dt('2026-01-25 08:20:00')), ('G035', -0.41, dt('2026-01-27 10:35:00')),
        ('G036', -0.63, dt('2026-01-29 13:00:00')), ('G037', -0.71, dt('2026-02-01 16:10:00')),
        ('G038', -0.67, dt('2026-02-03 11:15:00')), ('G039', -0.59, dt('2026-02-05 18:30:00')),
        ('G040', -0.56, dt('2026-02-07 09:40:00')), ('G041', -0.62, dt('2026-02-08 20:05:00')),
        ('G042', -0.54, dt('2026-02-10 12:25:00')), ('G043', -0.66, dt('2026-02-11 10:00:00')),
        ('G044', -0.73, dt('2026-02-12 15:00:00')), ('G045', -0.55, dt('2026-02-13 17:15:00')),
        ('G046', -0.49, dt('2026-02-14 11:10:00')), ('G047', -0.70, dt('2026-02-14 19:00:00')),
        ('G048', -0.68, dt('2026-02-14 14:40:00')), ('G049', -0.45, dt('2026-02-14 08:25:00')),
        ('G050', -0.61, dt('2026-02-14 22:00:00')), ('G051', -0.57, dt('2026-02-14 10:15:00')),
        ('G052', -0.64, dt('2026-02-14 13:05:00')), ('G053', -0.75, dt('2026-02-14 11:50:00')),
        ('G054', -0.60, dt('2026-02-14 21:30:00')), ('G055', -0.46, dt('2026-02-14 09:35:00')),
    ]
    await conn.executemany(
        "INSERT INTO sentiment_analysis (grievance_id, compound_score, analyzed_at) VALUES ($1,$2,$3)",
        sentiments
    )

    print("  Inserting priorities...")
    priorities = [
        ('G026', 'HIGH', dt('2026-01-05 10:20:00')), ('G027', 'HIGH', dt('2026-01-08 15:25:00')),
        ('G028', 'HIGH', dt('2026-01-10 11:35:00')), ('G029', 'HIGH', dt('2026-01-12 17:20:00')),
        ('G030', 'HIGH', dt('2026-01-15 12:45:00')), ('G031', 'MEDIUM', dt('2026-01-18 09:30:00')),
        ('G032', 'MEDIUM', dt('2026-01-20 14:15:00')), ('G033', 'HIGH', dt('2026-01-23 00:25:00')),
        ('G034', 'MEDIUM', dt('2026-01-25 08:35:00')), ('G035', 'HIGH', dt('2026-01-27 10:50:00')),
        ('G036', 'HIGH', dt('2026-01-29 13:15:00')), ('G037', 'CRITICAL', dt('2026-02-01 16:25:00')),
        ('G038', 'HIGH', dt('2026-02-03 11:30:00')), ('G039', 'HIGH', dt('2026-02-05 18:45:00')),
        ('G040', 'MEDIUM', dt('2026-02-07 10:00:00')), ('G041', 'HIGH', dt('2026-02-08 20:20:00')),
        ('G042', 'HIGH', dt('2026-02-10 12:40:00')), ('G043', 'HIGH', dt('2026-02-11 10:15:00')),
        ('G044', 'HIGH', dt('2026-02-12 15:15:00')), ('G045', 'MEDIUM', dt('2026-02-13 17:30:00')),
        ('G046', 'MEDIUM', dt('2026-02-14 11:25:00')), ('G047', 'HIGH', dt('2026-02-14 19:15:00')),
        ('G048', 'HIGH', dt('2026-02-14 15:00:00')), ('G049', 'MEDIUM', dt('2026-02-14 08:40:00')),
        ('G050', 'HIGH', dt('2026-02-14 22:15:00')), ('G051', 'HIGH', dt('2026-02-14 10:30:00')),
        ('G052', 'HIGH', dt('2026-02-14 13:20:00')), ('G053', 'CRITICAL', dt('2026-02-14 12:05:00')),
        ('G054', 'MEDIUM', dt('2026-02-14 21:45:00')), ('G055', 'HIGH', dt('2026-02-14 10:00:00')),
    ]
    await conn.executemany(
        "INSERT INTO priorities (grievance_id, priority_level, calculated_at) VALUES ($1,$2,$3)",
        priorities
    )

    print("  Inserting grievance assignments...")
    assignments = [
        ('G026', 1, 1, dt('2026-01-05 11:00:00')), ('G027', 2, 1, dt('2026-01-08 16:00:00')),
        ('G028', 3, 1, dt('2026-01-10 12:00:00')), ('G029', 4, 1, dt('2026-01-12 18:00:00')),
        ('G030', 5, 1, dt('2026-01-15 13:30:00')), ('G031', 6, 1, dt('2026-01-18 10:00:00')),
        ('G032', 7, 1, dt('2026-01-20 15:00:00')), ('G033', 8, 1, dt('2026-01-23 01:00:00')),
        ('G034', 8, 1, dt('2026-01-25 09:00:00')), ('G035', 10, 1, dt('2026-01-27 11:30:00')),
        ('G036', 1, 1, dt('2026-01-29 14:00:00')), ('G037', 2, 1, dt('2026-02-01 17:00:00')),
        ('G038', 3, 1, dt('2026-02-03 12:00:00')), ('G039', 4, 1, dt('2026-02-05 19:30:00')),
        ('G040', 9, 1, dt('2026-02-07 10:30:00')), ('G041', 10, 1, dt('2026-02-08 21:00:00')),
        ('G042', 4, 1, dt('2026-02-10 13:30:00')), ('G043', 3, 1, dt('2026-02-11 11:00:00')),
        ('G044', 1, 1, dt('2026-02-12 16:00:00')), ('G045', 7, 1, dt('2026-02-13 18:00:00')),
        ('G046', 6, 1, dt('2026-02-14 12:00:00')), ('G047', 2, 1, dt('2026-02-14 20:00:00')),
        ('G048', 14, 1, dt('2026-02-14 15:30:00')), ('G049', 8, 1, dt('2026-02-14 09:00:00')),
        ('G050', 10, 1, dt('2026-02-14 23:00:00')), ('G051', 4, 1, dt('2026-02-14 11:00:00')),
        ('G052', 3, 1, dt('2026-02-14 14:00:00')), ('G053', 1, 1, dt('2026-02-14 12:30:00')),
        ('G054', 8, 1, dt('2026-02-14 22:00:00')), ('G055', 10, 1, dt('2026-02-14 10:30:00')),
    ]
    await conn.executemany(
        "INSERT INTO grievance_assignments (grievance_id, department_id, admin_id, assigned_at) VALUES ($1,$2,$3,$4)",
        assignments
    )

    print("  Inserting peer validations...")
    validations = [
        ('G026', 4, dt('2026-01-06 09:30:00')), ('G026', 7, dt('2026-01-07 10:15:00')),
        ('G028', 5, dt('2026-01-11 12:45:00')), ('G029', 8, dt('2026-01-13 14:20:00')),
        ('G030', 9, dt('2026-01-16 11:00:00')), ('G035', 10, dt('2026-01-28 08:50:00')),
        ('G037', 11, dt('2026-02-02 16:10:00')), ('G041', 12, dt('2026-02-09 19:45:00')),
        ('G043', 13, dt('2026-02-12 10:30:00')), ('G048', 3, dt('2026-02-14 16:00:00')),
        ('G050', 6, dt('2026-02-15 00:15:00')), ('G052', 2, dt('2026-02-15 09:20:00')),
        ('G053', 4, dt('2026-02-15 12:45:00')), ('G055', 5, dt('2026-02-15 11:10:00')),
        ('G027', 8, dt('2026-01-09 15:30:00')),
    ]
    await conn.executemany(
        "INSERT INTO peer_validations (grievance_id, user_id, validated_at) VALUES ($1,$2,$3)",
        validations
    )

    print("  Inserting duplicate grievances...")
    duplicates = [
        ('G026', 'G044', dt('2026-02-13 10:00:00')), ('G027', 'G047', dt('2026-02-14 18:30:00')),
        ('G028', 'G038', dt('2026-02-04 14:20:00')), ('G028', 'G043', dt('2026-02-12 11:15:00')),
        ('G029', 'G042', dt('2026-02-11 13:40:00')), ('G029', 'G051', dt('2026-02-14 10:50:00')),
        ('G048', 'G052', dt('2026-02-14 16:00:00')), ('G053', 'G036', dt('2026-02-14 13:20:00')),
    ]
    await conn.executemany(
        "INSERT INTO duplicate_grievances (parent_grievance_id, child_grievance_id, created_at) VALUES ($1,$2,$3)",
        duplicates
    )

    print("  Inserting feedback...")
    feedbacks = [
        ('G026', 7, 4, 'Water supply restored after complaint, but pressure still low', dt('2026-02-10 09:45:00')),
        ('G027', 4, 5, 'Power cuts fixed quickly - good response from TNEB', dt('2026-02-09 14:20:00')),
        ('G028', 5, 3, 'Garbage cleared but area still dirty - needs regular pickup', dt('2026-02-12 11:30:00')),
        ('G029', 8, 5, 'Potholes filled properly, road safe now - thank you', dt('2026-02-13 16:15:00')),
        ('G035', 10, 5, 'Tree branches trimmed immediately - very satisfied', dt('2026-02-01 10:50:00')),
        ('G037', 11, 4, 'Transformer repaired fast - no more sparks, good job', dt('2026-02-03 17:00:00')),
        ('G041', 12, 3, 'Patrolling increased but theft still a concern', dt('2026-02-12 20:10:00')),
        ('G043', 13, 4, 'Bus stop cleaned, but bins need more frequent emptying', dt('2026-02-13 09:55:00')),
        ('G048', 3, 5, 'Mosquito fogging done - no more bites, excellent work', dt('2026-02-15 14:30:00')),
        ('G050', 6, 4, 'Police increased night patrol - feels safer now', dt('2026-02-15 00:45:00')),
        ('G053', 4, 3, 'Water tested and treated - smell gone, but monitor needed', dt('2026-02-15 12:20:00')),
        ('G055', 5, 5, 'Tree removed quickly - road clear, thank you team', dt('2026-02-15 11:40:00')),
    ]
    await conn.executemany(
        "INSERT INTO feedback (grievance_id, user_id, rating, comments, submitted_at) VALUES ($1,$2,$3,$4,$5)",
        feedbacks
    )

    print("  Inserting notifications...")
    notifications = [
        (2, 'Your grievance G026 (Water Supply) has been assigned to Water Supply Department.', False, dt('2026-01-05 11:05:00')),
        (3, 'Your grievance G027 (Electricity) is now IN_PROGRESS.', False, dt('2026-01-08 16:05:00')),
        (4, 'Your grievance G028 (Garbage) has been marked as duplicate of G026.', False, dt('2026-01-10 12:30:00')),
        (5, 'Grievance G029 (Potholes) you validated has been resolved.', False, dt('2026-01-13 18:00:00')),
        (7, 'Feedback submitted on G026 - thank you for rating!', False, dt('2026-02-10 10:00:00')),
        (8, 'Your grievance G032 (Street Lights) is now IN_PROGRESS.', False, dt('2026-01-20 15:30:00')),
        (9, 'Grievance G033 (Noise) assigned to General Administration.', False, dt('2026-01-23 01:30:00')),
        (10, 'Your grievance G035 (Tree Branches) has been resolved.', False, dt('2026-01-28 09:00:00')),
        (11, 'Grievance G037 (Transformer) marked CRITICAL and assigned.', False, dt('2026-02-01 17:30:00')),
        (12, 'Notification: Mosquito fogging completed in your area (G048).', False, dt('2026-02-15 15:00:00')),
        (13, 'Your grievance G049 (Bus Service) is now IN_PROGRESS.', False, dt('2026-02-14 09:30:00')),
        (2, 'Security concern G050 has been escalated to Traffic & Safety.', False, dt('2026-02-14 23:30:00')),
        (3, 'Grievance G051 (Road Damage) duplicate of G029 - closed.', False, dt('2026-02-14 11:30:00')),
        (4, 'Water quality issue G053 has been assigned and tested.', False, dt('2026-02-14 13:00:00')),
        (5, 'Tree removal completed for G055 - road clear now.', False, dt('2026-02-14 11:00:00')),
        (6, 'Thank you for validating G055 - your help is appreciated.', False, dt('2026-02-15 11:30:00')),
        (7, 'New feedback received on G048 - check details.', False, dt('2026-02-15 15:15:00')),
        (8, 'Grievance G043 status updated to RESOLVED.', False, dt('2026-02-14 12:00:00')),
        (9, 'Notification: Power issue G047 fixed - thank you for reporting.', False, dt('2026-02-15 20:30:00')),
        (10, 'Your feedback on G035 was received - rating 5 stars!', False, dt('2026-02-01 11:00:00')),
    ]
    await conn.executemany(
        "INSERT INTO notifications (user_id, message, is_read, created_at) VALUES ($1,$2,$3,$4)",
        notifications
    )


async def main():
    print("=" * 60)
    print("  SPGRS - Database Setup Script")
    print("=" * 60)
    print()

    await create_database_if_not_exists()

    print(f"\n[2/4] Connecting to '{settings.DB_NAME}'...")
    conn = await asyncpg.connect(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        database=settings.DB_NAME,
    )

    try:
        print("\n[3/4] Dropping existing tables and creating new ones...")
        await conn.execute(DROP_TABLES_SQL)
        print("  -> All tables dropped.")
        await conn.execute(CREATE_TABLES_SQL)
        print("  -> All tables created successfully.")

        print("\n[4/4] Seeding data...")
        await seed_data(conn)
        print("\n  -> All seed data inserted successfully!")

        user_count = await conn.fetchval("SELECT COUNT(*) FROM users")
        grievance_count = await conn.fetchval("SELECT COUNT(*) FROM grievances")
        location_count = await conn.fetchval("SELECT COUNT(*) FROM locations")
        category_count = await conn.fetchval("SELECT COUNT(*) FROM categories")
        dept_count = await conn.fetchval("SELECT COUNT(*) FROM departments")

        print("\n" + "=" * 60)
        print("  DATABASE SETUP COMPLETE")
        print("=" * 60)
        print(f"  Users:       {user_count}")
        print(f"  Locations:   {location_count}")
        print(f"  Categories:  {category_count}")
        print(f"  Departments: {dept_count}")
        print(f"  Grievances:  {grievance_count}")
        print("=" * 60)
        print()
        print("  Admin Login:  sara_admin@gmail.com / admin123")
        print("  Test User:    testing@gmail.com / testing123")
        print()

    except Exception as e:
        print(f"\n  ERROR: {e}")
        raise
    finally:
        await conn.close()


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
