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
('Tamil Nadu','Tirunelveli','TIRUNELVELI ZONE 1','1','Tirunelveli Nagar 1'),
('Tamil Nadu','Tirunelveli','TIRUNELVELI ZONE 1','2','Tirunelveli Street 2'),
('Tamil Nadu','Tirunelveli','TIRUNELVELI ZONE 2','3','Tirunelveli Colony 3'),
('Tamil Nadu','Tirunelveli','TIRUNELVELI ZONE 2','4','Tirunelveli Extension 4'),
('Tamil Nadu','Tirunelveli','TIRUNELVELI ZONE 3','5','Tirunelveli Main Road 5'),

('Tamil Nadu','Madurai','MADURAI ZONE 1','1','Madurai Nagar 6'),
('Tamil Nadu','Madurai','MADURAI ZONE 1','2','Madurai Street 7'),
('Tamil Nadu','Madurai','MADURAI ZONE 2','3','Madurai Colony 8'),
('Tamil Nadu','Madurai','MADURAI ZONE 2','4','Madurai Extension 9'),
('Tamil Nadu','Madurai','MADURAI ZONE 3','5','Madurai Main Road 10'),

('Tamil Nadu','Chennai','CHENNAI ZONE 1','1','Chennai Nagar 11'),
('Tamil Nadu','Chennai','CHENNAI ZONE 1','2','Chennai Street 12'),
('Tamil Nadu','Chennai','CHENNAI ZONE 2','3','Chennai Colony 13'),
('Tamil Nadu','Chennai','CHENNAI ZONE 2','4','Chennai Extension 14'),
('Tamil Nadu','Chennai','CHENNAI ZONE 3','5','Chennai Main Road 15'),

('Tamil Nadu','Coimbatore','COIMBATORE ZONE 1','1','Coimbatore Nagar 16'),
('Tamil Nadu','Coimbatore','COIMBATORE ZONE 1','2','Coimbatore Street 17'),
('Tamil Nadu','Coimbatore','COIMBATORE ZONE 2','3','Coimbatore Colony 18'),
('Tamil Nadu','Coimbatore','COIMBATORE ZONE 2','4','Coimbatore Extension 19'),
('Tamil Nadu','Coimbatore','COIMBATORE ZONE 3','5','Coimbatore Main Road 20'),

('Tamil Nadu','Salem','SALEM ZONE 1','1','Salem Nagar 21'),
('Tamil Nadu','Salem','SALEM ZONE 1','2','Salem Street 22'),
('Tamil Nadu','Salem','SALEM ZONE 2','3','Salem Colony 23'),
('Tamil Nadu','Salem','SALEM ZONE 2','4','Salem Extension 24'),
('Tamil Nadu','Salem','SALEM ZONE 3','5','Salem Main Road 25'),

('Tamil Nadu','Trichy','TRICHY ZONE 1','1','Trichy Nagar 26'),
('Tamil Nadu','Trichy','TRICHY ZONE 1','2','Trichy Street 27'),
('Tamil Nadu','Trichy','TRICHY ZONE 2','3','Trichy Colony 28'),
('Tamil Nadu','Trichy','TRICHY ZONE 2','4','Trichy Extension 29'),
('Tamil Nadu','Trichy','TRICHY ZONE 3','5','Trichy Main Road 30'),

('Tamil Nadu','Erode','ERODE ZONE 1','1','Erode Nagar 31'),
('Tamil Nadu','Erode','ERODE ZONE 1','2','Erode Street 32'),
('Tamil Nadu','Erode','ERODE ZONE 2','3','Erode Colony 33'),
('Tamil Nadu','Erode','ERODE ZONE 2','4','Erode Extension 34'),
('Tamil Nadu','Erode','ERODE ZONE 3','5','Erode Main Road 35'),

('Tamil Nadu','Vellore','VELLORE ZONE 1','1','Vellore Nagar 36'),
('Tamil Nadu','Vellore','VELLORE ZONE 1','2','Vellore Street 37'),
('Tamil Nadu','Vellore','VELLORE ZONE 2','3','Vellore Colony 38'),
('Tamil Nadu','Vellore','VELLORE ZONE 2','4','Vellore Extension 39'),
('Tamil Nadu','Vellore','VELLORE ZONE 3','5','Vellore Main Road 40'),

('Tamil Nadu','Thoothukudi','THOOTHUKUDI ZONE 1','1','Thoothukudi Nagar 41'),
('Tamil Nadu','Thoothukudi','THOOTHUKUDI ZONE 1','2','Thoothukudi Street 42'),
('Tamil Nadu','Thoothukudi','THOOTHUKUDI ZONE 2','3','Thoothukudi Colony 43'),
('Tamil Nadu','Thoothukudi','THOOTHUKUDI ZONE 2','4','Thoothukudi Extension 44'),
('Tamil Nadu','Thoothukudi','THOOTHUKUDI ZONE 3','5','Thoothukudi Main Road 45'),

('Tamil Nadu','Dindigul','DINDIGUL ZONE 1','1','Dindigul Nagar 46'),
('Tamil Nadu','Dindigul','DINDIGUL ZONE 1','2','Dindigul Street 47'),
('Tamil Nadu','Dindigul','DINDIGUL ZONE 2','3','Dindigul Colony 48'),
('Tamil Nadu','Dindigul','DINDIGUL ZONE 2','4','Dindigul Extension 49'),
('Tamil Nadu','Dindigul','DINDIGUL ZONE 3','5','Dindigul Main Road 50'),

('Tamil Nadu','Kanyakumari','KANYAKUMARI ZONE 1','1','Kanyakumari Nagar 51'),
('Tamil Nadu','Kanyakumari','KANYAKUMARI ZONE 1','2','Kanyakumari Street 52'),
('Tamil Nadu','Kanyakumari','KANYAKUMARI ZONE 2','3','Kanyakumari Colony 53'),
('Tamil Nadu','Kanyakumari','KANYAKUMARI ZONE 2','4','Kanyakumari Extension 54'),
('Tamil Nadu','Kanyakumari','KANYAKUMARI ZONE 3','5','Kanyakumari Main Road 55'),

('Tamil Nadu','Karur','KARUR ZONE 1','1','Karur Nagar 56'),
('Tamil Nadu','Karur','KARUR ZONE 1','2','Karur Street 57'),
('Tamil Nadu','Karur','KARUR ZONE 2','3','Karur Colony 58'),
('Tamil Nadu','Karur','KARUR ZONE 2','4','Karur Extension 59'),
('Tamil Nadu','Karur','KARUR ZONE 3','5','Karur Main Road 60'),

('Tamil Nadu','Namakkal','NAMAKKAL ZONE 1','1','Namakkal Nagar 61'),
('Tamil Nadu','Namakkal','NAMAKKAL ZONE 1','2','Namakkal Street 62'),
('Tamil Nadu','Namakkal','NAMAKKAL ZONE 2','3','Namakkal Colony 63'),
('Tamil Nadu','Namakkal','NAMAKKAL ZONE 2','4','Namakkal Extension 64'),
('Tamil Nadu','Namakkal','NAMAKKAL ZONE 3','5','Namakkal Main Road 65'),

('Tamil Nadu','Thanjavur','THANJAVUR ZONE 1','1','Thanjavur Nagar 66'),
('Tamil Nadu','Thanjavur','THANJAVUR ZONE 1','2','Thanjavur Street 67'),
('Tamil Nadu','Thanjavur','THANJAVUR ZONE 2','3','Thanjavur Colony 68'),
('Tamil Nadu','Thanjavur','THANJAVUR ZONE 2','4','Thanjavur Extension 69'),
('Tamil Nadu','Thanjavur','THANJAVUR ZONE 3','5','Thanjavur Main Road 70'),

('Tamil Nadu','Virudhunagar','VIRUDHUNAGAR ZONE 1','1','Virudhunagar Nagar 71'),
('Tamil Nadu','Virudhunagar','VIRUDHUNAGAR ZONE 1','2','Virudhunagar Street 72'),
('Tamil Nadu','Virudhunagar','VIRUDHUNAGAR ZONE 2','3','Virudhunagar Colony 73'),
('Tamil Nadu','Virudhunagar','VIRUDHUNAGAR ZONE 2','4','Virudhunagar Extension 74'),
('Tamil Nadu','Virudhunagar','VIRUDHUNAGAR ZONE 3','5','Virudhunagar Main Road 75'),

('Tamil Nadu','Cuddalore','CUDDALORE ZONE 1','1','Cuddalore Nagar 76'),
('Tamil Nadu','Cuddalore','CUDDALORE ZONE 1','2','Cuddalore Street 77'),
('Tamil Nadu','Cuddalore','CUDDALORE ZONE 2','3','Cuddalore Colony 78'),
('Tamil Nadu','Cuddalore','CUDDALORE ZONE 2','4','Cuddalore Extension 79'),
('Tamil Nadu','Cuddalore','CUDDALORE ZONE 3','5','Cuddalore Main Road 80'),

('Tamil Nadu','Tiruppur','TIRUPPUR ZONE 1','1','Tiruppur Nagar 81'),
('Tamil Nadu','Tiruppur','TIRUPPUR ZONE 1','2','Tiruppur Street 82'),
('Tamil Nadu','Tiruppur','TIRUPPUR ZONE 2','3','Tiruppur Colony 83'),
('Tamil Nadu','Tiruppur','TIRUPPUR ZONE 2','4','Tiruppur Extension 84'),
('Tamil Nadu','Tiruppur','TIRUPPUR ZONE 3','5','Tiruppur Main Road 85'),

('Tamil Nadu','Nagapattinam','NAGAPATTINAM ZONE 1','1','Nagapattinam Nagar 86'),
('Tamil Nadu','Nagapattinam','NAGAPATTINAM ZONE 1','2','Nagapattinam Street 87'),
('Tamil Nadu','Nagapattinam','NAGAPATTINAM ZONE 2','3','Nagapattinam Colony 88'),
('Tamil Nadu','Nagapattinam','NAGAPATTINAM ZONE 2','4','Nagapattinam Extension 89'),
('Tamil Nadu','Nagapattinam','NAGAPATTINAM ZONE 3','5','Nagapattinam Main Road 90'),

('Tamil Nadu','Krishnagiri','KRISHNAGIRI ZONE 1','1','Krishnagiri Nagar 91'),
('Tamil Nadu','Krishnagiri','KRISHNAGIRI ZONE 1','2','Krishnagiri Street 92'),
('Tamil Nadu','Krishnagiri','KRISHNAGIRI ZONE 2','3','Krishnagiri Colony 93'),
('Tamil Nadu','Krishnagiri','KRISHNAGIRI ZONE 2','4','Krishnagiri Extension 94'),
('Tamil Nadu','Krishnagiri','KRISHNAGIRI ZONE 3','5','Krishnagiri Main Road 95'),

('Tamil Nadu','Perambalur','PERAMBALUR ZONE 1','1','Perambalur Nagar 96'),
('Tamil Nadu','Perambalur','PERAMBALUR ZONE 1','2','Perambalur Street 97'),
('Tamil Nadu','Perambalur','PERAMBALUR ZONE 2','3','Perambalur Colony 98'),
('Tamil Nadu','Perambalur','PERAMBALUR ZONE 2','4','Perambalur Extension 99'),
('Tamil Nadu','Perambalur','PERAMBALUR ZONE 3','5','Perambalur Main Road 100'),
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
