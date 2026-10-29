"""Script to create a clean, portable offline ZIP distribution of Business Gate.
"""
from __future__ import annotations
import os, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ZIP = ROOT / "BusinessGate-Offline-Package.zip"

EXCLUDE_DIRS = {
    ".git", ".github", "__pycache__", ".pytest_cache", ".venv",
    "node_modules", ".next", ".system_generated"
}
EXCLUDE_EXTS = {".pyc", ".pyo", ".log", ".tmp"}

def create_package():
    print(f"Creating portable offline package at: {OUTPUT_ZIP}...")
    total_files = 0
    total_bytes = 0

    with zipfile.ZipFile(OUTPUT_ZIP, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        # Walk directories
        for base_dir in ["backend", "frontend", "data", "ops"]:
            full_base = ROOT / base_dir
            if not full_base.exists():
                continue
            for root, dirs, files in os.walk(full_base):
                dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
                for file in files:
                    if any(file.endswith(ext) for ext in EXCLUDE_EXTS):
                        continue
                    file_path = Path(root) / file
                    arcname = file_path.relative_to(ROOT)
                    zf.write(file_path, arcname)
                    total_files += 1
                    total_bytes += file_path.stat().st_size

        # Root files
        root_files = [
            ".env", ".env.example", ".gitignore", "docker-compose.yml",
            "Start-BusinessGate.bat", "Stop-BusinessGate.bat", "Start-BusinessGate.sh",
            "README_OFFLINE.md", "README.md"
        ]
        for rf in root_files:
            fp = ROOT / rf
            if fp.exists():
                zf.write(fp, rf)
                total_files += 1
                total_bytes += fp.stat().st_size

    zip_size_mb = OUTPUT_ZIP.stat().st_size / (1024 * 1024)
    raw_size_mb = total_bytes / (1024 * 1024)
    print(f"\n[SUCCESS] Package created successfully!")
    print(f" - Output file: {OUTPUT_ZIP.name}")
    print(f" - Files included: {total_files}")
    print(f" - Uncompressed size: {raw_size_mb:.1f} MB")
    print(f" - Compressed ZIP size: {zip_size_mb:.1f} MB")

if __name__ == "__main__":
    create_package()
