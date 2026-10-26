"""The Alembic migration must produce the same schema as the models."""
import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect

from app.database.database import Base
from tests.conftest import TEST_DATABASE_URL, reset_database

BACKEND = Path(__file__).resolve().parents[1]


def test_alembic_upgrade_matches_models():
    """Run every migration on an empty PostgreSQL test database and compare with the models."""
    engine = create_engine(TEST_DATABASE_URL)
    reset_database(engine)
    try:
        env = {**os.environ, "DATABASE_URL": TEST_DATABASE_URL}
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"], cwd=BACKEND, env=env, capture_output=True, text=True
        )
        assert result.returncode == 0, result.stderr

        inspector = inspect(engine)
        tables = set(inspector.get_table_names()) - {"alembic_version"}
        assert tables == set(Base.metadata.tables)
        for name, table in Base.metadata.tables.items():
            migrated_cols = {c["name"] for c in inspector.get_columns(name)}
            assert migrated_cols == set(table.columns.keys()), name
        # The "only one" rules are partial unique indexes in PostgreSQL.
        indexes = {i["name"]: i for t in ("banners", "signature_templates") for i in inspector.get_indexes(t)}
        assert indexes["uq_banners_single_published"]["unique"]
        assert indexes["uq_signature_templates_single_active"]["unique"]
    finally:
        engine.dispose()
        reset_database(engine)
        engine.dispose()
