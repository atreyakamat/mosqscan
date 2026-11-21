"""Pytest fixtures for Vectora AI backend tests."""
from __future__ import annotations

import io
import os
import tempfile
from typing import Generator

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.core.security import create_access_token, hash_password
from app.db.base import Base
from app.db.models import User, UserRole
from app.db.session import get_db
from app.main import app

# Test database
TEST_DB_FILE = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
TEST_DB_URL = f"sqlite:///{TEST_DB_FILE.name}"
test_engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)
    try:
        os.unlink(TEST_DB_FILE.name)
    except OSError:
        pass


@pytest.fixture(autouse=True)
def clean_rate_limits():
    """Clear rate limiting state before every test to ensure isolation."""
    from app.core.rate_limit import rate_limiter
    client = rate_limiter.get_client()
    if client is not None:
        try:
            for key in client.scan_iter("rl:*"):
                client.delete(key)
        except Exception:
            pass
    from app.core.rate_limit import _in_memory_store, _mem_lock
    with _mem_lock:
        _in_memory_store.clear()
    yield



@pytest.fixture
def db_session() -> Generator:
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session) -> Generator[TestClient, None, None]:
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db_session) -> dict:
    user = db_session.query(User).filter(User.email == "user1@example.com").first()
    if not user:
        user = User(
            email="user1@example.com",
            username="user1",
            hashed_password=hash_password("Password123!"),
            role=UserRole.user,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
    token = create_access_token({"sub": user.id})
    return {"user": user, "token": token, "headers": {"Authorization": f"Bearer {token}"}}


@pytest.fixture
def second_user(db_session) -> dict:
    user = db_session.query(User).filter(User.email == "user2@example.com").first()
    if not user:
        user = User(
            email="user2@example.com",
            username="user2",
            hashed_password=hash_password("Password123!"),
            role=UserRole.user,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
    token = create_access_token({"sub": user.id})
    return {"user": user, "token": token, "headers": {"Authorization": f"Bearer {token}"}}


@pytest.fixture
def admin_user(db_session) -> dict:
    user = db_session.query(User).filter(User.email == "admin@example.com").first()
    if not user:
        user = User(
            email="admin@example.com",
            username="adminuser",
            hashed_password=hash_password("AdminPassword123!"),
            role=UserRole.admin,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
    token = create_access_token({"sub": user.id})
    return {"user": user, "token": token, "headers": {"Authorization": f"Bearer {token}"}}



def create_test_image(width=224, height=224, fmt="JPEG") -> bytes:
    """Generate a valid test image byte stream."""
    img = Image.new("RGB", (width, height), color=(128, 128, 128))
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


def create_test_video(frames: int, fps: int = 100) -> bytes:
    """Generate a test MP4 video byte stream of exact frames and fps."""
    tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
    tmp_path = tmp.name
    tmp.close()

    try:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(tmp_path, fourcc, float(fps), (64, 64))
        for i in range(frames):
            frame = np.full((64, 64, 3), (i % 256), dtype=np.uint8)
            writer.write(frame)
        writer.release()

        with open(tmp_path, "rb") as f:
            data = f.read()
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    return data
