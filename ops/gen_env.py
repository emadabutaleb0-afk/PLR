#!/usr/bin/env python3
"""Create a fresh .env with newly generated secrets (never reuse a .env that has been shared).
Usage:  python ops/gen_env.py [--admin-email you@company.com] [--force]
It copies .env.example, replaces SECRET_KEY, BOOTSTRAP_ADMIN_PASSWORD and POSTGRES_PASSWORD with random values, and refuses to overwrite an existing .env unless --force
(the old one is kept as .env.old so nothing is lost). Secrets are written to the file only, never printed."""
import argparse, re, secrets, shutil, string, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def strong_password(n=20) -> str:
    alphabet = string.ascii_letters + string.digits + "-_.!"
    while True:
        p = "".join(secrets.choice(alphabet) for _ in range(n))
        if any(c.islower() for c in p) and any(c.isupper() for c in p) and any(c.isdigit() for c in p):
            return p


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--admin-email")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    env, example = ROOT / ".env", ROOT / ".env.example"
    if env.exists() and not a.force:
        print(".env already exists. Re-run with --force to replace it (the old file is kept as .env.old).")
        return 1
    if env.exists():
        shutil.copy(env, ROOT / ".env.old")
    text = example.read_text(encoding="utf-8")
    repl = {"SECRET_KEY": secrets.token_urlsafe(48), "BOOTSTRAP_ADMIN_PASSWORD": strong_password(), "POSTGRES_PASSWORD": secrets.token_urlsafe(24)}
    if a.admin_email:
        repl["BOOTSTRAP_ADMIN_EMAIL"] = a.admin_email
    for k, v in repl.items():
        text = re.sub(rf"^{k}=.*$", f"{k}={v}", text, flags=re.M)
    env.write_text(text, encoding="utf-8")
    try:
        env.chmod(0o600)
    except OSError:
        pass
    print("Wrote .env with new SECRET_KEY, BOOTSTRAP_ADMIN_PASSWORD and POSTGRES_PASSWORD (open the file to read the admin password).")
    if "ceo@company.local" in text:
        print("Note: BOOTSTRAP_ADMIN_EMAIL is still the placeholder ceo@company.local; production mode refuses to start with it. Use --admin-email.")
    print("An existing Postgres volume keeps its OLD password: remove the volume (docker compose down -v) if you change POSTGRES_PASSWORD on a used database.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
