"""V4 phase 5: migrations match the models, backups restore, and the app survives restarts of its own state."""
import os
import sqlite3
import subprocess
import sys
from pathlib import Path
from sqlalchemy import create_engine, inspect

BACKEND = Path(__file__).resolve().parents[2]


def test_alembic_head_matches_the_models(tmp_path):
    """A fresh `alembic upgrade head` must produce every table and column the code expects (catches a forgotten migration)."""
    db = tmp_path / "mig.db"
    r = subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=BACKEND, env={**os.environ, "DATABASE_URL": f"sqlite:///{db}"}, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-800:]
    from app.db.session import Base
    import app.models  # noqa: F401
    insp = inspect(create_engine(f"sqlite:///{db}"))
    have = set(insp.get_table_names())
    missing, cols = [], []
    for name, t in Base.metadata.tables.items():
        if name not in have:
            missing.append(name); continue
        got = {c["name"] for c in insp.get_columns(name)}
        cols += [f"{name}.{c.name}" for c in t.columns if c.name not in got]
    assert not missing and not cols, f"schema drift: missing tables {missing}, missing columns {cols}"


def test_backup_restore_roundtrip(client, ceo, loaded, tmp_path):
    from app.core.config import get_settings
    from app.services import backup as bk
    live = get_settings().database_url.replace("sqlite:///", "")
    out = bk.backup(live, str(tmp_path / "b.db"))
    assert out["integrity_ok"] and out["matches_original"] and out["counts"]["users"] >= 1
    copy = tmp_path / "restored.db"
    copy.write_bytes(b"old")
    res = bk.restore(str(tmp_path / "b.db"), str(copy))
    assert res["integrity_ok"] and res["matches_original"] and (tmp_path / "restored.db.before-restore").exists()


def test_corrupt_backup_is_refused(tmp_path):
    from app.services import backup as bk
    bad = tmp_path / "bad.db"
    bad.write_bytes(b"this is not a database" * 50)
    try:
        bk.restore(str(bad), str(tmp_path / "t.db"))
        raise AssertionError("a corrupt backup must not be restored")
    except (RuntimeError, sqlite3.DatabaseError):
        pass
    assert not (tmp_path / "t.db").exists()
