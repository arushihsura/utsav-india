import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
import jwt

from app import create_app
from database import get_db, now_iso
from auth import issue_app_jwt


MOCK_FESTIVALS = [
    {
        "id": 1,
        "name": "Diwali",
        "date": "2026-11-08",
        "description": "Festival of Lights celebrating victory of light over darkness.",
        "month": 11,
        "day": 8,
        "religion": "hindu",
        "states": ["All India"],
        "national_holiday": True,
        "restricted_holiday": False,
        "type": "festival",
        "local_names": {"hi": "दिवाली", "ta": "தீபாவளி"},
        "also_known_as": ["Deepavali"],
        "source": "https://indian-festival-api.vercel.app/api/festivals",
    },
    {
        "id": 2,
        "name": "Holi",
        "date": "2026-03-04",
        "description": "Festival of Colors celebrating spring and harvest.",
        "month": 3,
        "day": 4,
        "religion": "hindu",
        "states": ["All India"],
        "national_holiday": True,
        "restricted_holiday": False,
        "type": "festival",
        "local_names": {"hi": "होली"},
        "also_known_as": ["Dol Jatra"],
        "source": "https://indian-festival-api.vercel.app/api/festivals",
    },
]


MOCK_WEATHER_MUMBAI = {
    "city": "Mumbai",
    "coordinates": {"latitude": 19.0760, "longitude": 72.8777},
    "current": {
        "time": "2026-10-28T12:00",
        "temperature_c": 31.5,
        "weather_code": 0,
        "weather_text": "Clear sky",
    },
    "forecast": [
        {
            "date": "2026-10-28",
            "temp_max_c": 33.0,
            "temp_min_c": 24.0,
            "precipitation_probability": 10,
            "weather_code": 0,
            "weather_text": "Clear sky",
        },
        {
            "date": "2026-10-29",
            "temp_max_c": 32.5,
            "temp_min_c": 24.5,
            "precipitation_probability": 75,
            "weather_code": 61,
            "weather_text": "Slight rain",
        },
        {
            "date": "2026-10-30",
            "temp_max_c": 30.0,
            "temp_min_c": 23.0,
            "precipitation_probability": 45,
            "weather_code": 2,
            "weather_text": "Partly cloudy",
        },
    ],
    "source": "Open-Meteo Forecast API (https://api.open-meteo.com/v1/forecast)",
}


@pytest.fixture
def app():
    db_fd, db_path = tempfile.mkstemp()
    test_config = {
        "TESTING": True,
        "DATABASE_PATH": db_path,
        "SECRET_KEY": "test-secret",
        "JWT_SECRET": "test-jwt-secret-key-12345",
        "JWT_EXP_MINUTES": 60,
        "GOOGLE_CLIENT_ID": "test-client-id.apps.googleusercontent.com",
    }
    application = create_app(test_config)

    yield application

    os.close(db_fd)
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def user_factory(app):
    def _create_user(google_sub="google-user-1", email="user1@example.com", name="Arun Sharma"):
        with app.app_context():
            db = get_db()
            now = now_iso()
            cursor = db.execute(
                """
                INSERT INTO users (google_sub, email, name, picture, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (google_sub, email, name, "https://example.com/pic.jpg", now, now),
            )
            db.commit()
            user_id = cursor.lastrowid
            row = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
            user = dict(row)
            token, expires_at = issue_app_jwt(user)
            return {"user": user, "token": token, "auth_header": {"Authorization": f"Bearer {token}"}}

    return _create_user


@pytest.fixture
def user_a(user_factory):
    return user_factory(google_sub="sub-user-a", email="user_a@example.com", name="Aarav Mehta")


@pytest.fixture
def user_b(user_factory):
    return user_factory(google_sub="sub-user-b", email="user_b@example.com", name="Diya Patel")
