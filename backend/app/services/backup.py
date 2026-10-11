"""Backup and restore for the local SQLite deployment (the Docker/PostgreSQL deployment uses ops/backup.sh and ops/restore.sh).
Uses SQLite's online backup API, so it is safe while the app is running. CLI:
    python -m app.services.backup backup <db_file> <backup_file>
    python -m app.services.backup restore <backup_file> <db_file>     (stop the app first)
"""
from __future__ import annotations
import shutil
import sqlite3
import sys
from pathlib import Path

CRITICAL = ("users", "recommendations", "recommendation_feedback", "action_items", "decision_tracking", "audit_logs")


def _count(path: str, table: str) -> int | None:
    c = sqlite3.connect(path)
    try:
        return c.execute(f'select count(*) from "{table}"').fetchone()[0]
    except sqlite3.OperationalError:
        return None
    finally:
        c.close()


def backup(db_file: str, out_file: str) -> dict:
    Path(out_file).parent.mkdir(parents=True, exist_ok=True)
    src, dst = sqlite3.connect(db_file), sqlite3.connect(out_file)
    try:
        src.backup(dst)
    finally:
        dst.close(); src.close()
    return verify(out_file, db_file)


def verify(backup_file: str, original: str | None = None) -> dict:
    c = sqlite3.connect(backup_file)
    try:
        ok = c.execute("pragma integrity_check").fetchone()[0] == "ok"
    finally:
        c.close()
    counts = {t: _count(backup_file, t) for t in CRITICAL}
    same = None if original is None else all(counts[t] == _count(original, t) for t in CRITICAL)
    return dict(integrity_ok=ok, counts=counts, matches_original=same)


def restore(backup_file: str, db_file: str) -> dict:
    chk = verify(backup_file)
    if not chk["integrity_ok"]:
        raise RuntimeError("The backup file failed its integrity check; nothing was restored.")
    if Path(db_file).exists():                                  # keep the database being replaced, never destroy it silently
        shutil.copy2(db_file, f"{db_file}.before-restore")
    shutil.copy2(backup_file, db_file)
    return verify(db_file, backup_file)


if __name__ == "__main__":
    import json
    cmd, a, b = sys.argv[1:4]
    print(json.dumps(backup(a, b) if cmd == "backup" else restore(a, b), indent=2))
