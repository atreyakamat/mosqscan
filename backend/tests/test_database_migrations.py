"""Database migration tests using Alembic."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ALEMBIC_INI = REPO_ROOT / "backend" / "alembic.ini"


def test_alembic_migrations_run_to_head_on_fresh_db():
    """Verify that Alembic runs migrations to head cleanly on a new database."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
        tmp_db_path = tmp_db.name

    old_db_url = os.environ.get("DATABASE_URL")
    try:
        tmp_db_url = f"sqlite:///{tmp_db_path}"
        os.environ["DATABASE_URL"] = tmp_db_url

        alembic_cfg = Config(str(ALEMBIC_INI))
        alembic_cfg.set_main_option("sqlalchemy.url", tmp_db_url)

        # Run migration upgrade to head
        command.upgrade(alembic_cfg, "head")

        # Inspect tables created
        engine = create_engine(tmp_db_url)
        inspector = inspect(engine)
        table_names = set(inspector.get_table_names())

        expected_tables = {
            "users",
            "refresh_tokens",
            "password_reset_tokens",
            "submissions",
            "media_files",
            "identification_results",
            "processing_jobs",
            "model_versions",
            "audit_events",
            "alembic_version",
        }

        assert expected_tables.issubset(table_names), (
            f"Missing migrated tables: {expected_tables - table_names}"
        )

    finally:
        if old_db_url is not None:
            os.environ["DATABASE_URL"] = old_db_url
        else:
            os.environ.pop("DATABASE_URL", None)
        try:
            os.unlink(tmp_db_path)
        except OSError:
            pass
