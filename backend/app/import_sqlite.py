"""Copy every row from a Signature Studio SQLite database into the configured (PostgreSQL) database.

Run inside the API container after migrations have created the schema:
    python -m app.import_sqlite /tmp/signature_studio.db

The SQLite file must be at the same Alembic revision as the target. The target must be empty
(apart from alembic_version); nothing is ever overwritten. Uploaded files are not copied by this
script - copy the uploads folder separately.
"""
import argparse
import sys

from sqlalchemy import create_engine, func, select, text

from app.database import models  # noqa: F401  (registers all tables on Base.metadata)
from app.database.database import Base, engine as target_engine


def _revision(conn) -> str | None:
    return conn.execute(text("SELECT version_num FROM alembic_version")).scalar()


def run(sqlite_path: str) -> int:
    source_engine = create_engine(f"sqlite:///{sqlite_path}")
    tables = Base.metadata.sorted_tables  # parents before children

    with source_engine.connect() as src, target_engine.begin() as dst:
        src_rev, dst_rev = _revision(src), _revision(dst)
        if src_rev != dst_rev:
            print(f"Revision mismatch: SQLite is at {src_rev}, target is at {dst_rev}. "
                  "Run 'alembic upgrade head' against both first.", file=sys.stderr)
            return 1

        non_empty = [t.name for t in tables if dst.execute(select(func.count()).select_from(t)).scalar()]
        if non_empty:
            print(f"Target database is not empty ({', '.join(non_empty)}). Nothing copied.", file=sys.stderr)
            return 1

        for table in tables:
            rows = [dict(r._mapping) for r in src.execute(select(table))]
            if rows:
                dst.execute(table.insert(), rows)
            print(f"  {table.name}: {len(rows)} rows")

        # Inserting explicit ids does not advance PostgreSQL sequences; move them past the copied rows.
        if dst.dialect.name == "postgresql":
            for table in tables:
                pk = list(table.primary_key.columns)
                if len(pk) == 1 and pk[0].autoincrement in (True, "auto") and pk[0].type.python_type is int:
                    dst.execute(text(
                        f"SELECT setval(pg_get_serial_sequence('{table.name}', '{pk[0].name}'), "
                        f"COALESCE((SELECT MAX({pk[0].name}) FROM {table.name}), 0) + 1, false) "
                        f"WHERE pg_get_serial_sequence('{table.name}', '{pk[0].name}') IS NOT NULL"
                    ))
    print("Import complete.")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sqlite_path")
    sys.exit(run(parser.parse_args().sqlite_path))
