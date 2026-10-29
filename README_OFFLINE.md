# Business Gate — Standalone Offline Package

**Business Gate** is a fully on-premise, offline Commercial Decision & Profit Intelligence platform.
This package contains everything needed to run the system without an active internet connection.

---

## 🚀 Quick Start (Windows)

1. **Extract the ZIP file** to any folder on your computer.
2. **Double-click `Start-BusinessGate.bat`**:
   - Automatically initializes the backend API and frontend interface.
   - Automatically opens your web browser to `http://localhost:3000`.
3. **Sign in** with the administrative credentials:
   - **Email:** `ceo@company.local`
   - **Password:** `change-this-first-password`
4. **When you are done:**
   - Double-click **`Stop-BusinessGate.bat`** to shut down both services cleanly.

---

## 🍎 Quick Start (macOS / Linux)

1. Open your Terminal inside the extracted folder.
2. Grant execution permissions and run:
   ```bash
   chmod +x Start-BusinessGate.sh
   ./Start-BusinessGate.sh
   ```
3. Open `http://localhost:3000` in your browser.

---

## 🐳 Optional: Run via Docker (Zero Dependencies)

If Docker Desktop is installed, you can run the entire stack with a single command:
```bash
docker compose up -d
```
Then navigate to `http://localhost:3000`.

---

## 📂 Package Contents

- **`backend/`**: FastAPI REST API engine, statistical models, and the local SQLite database (`merchbrain.db`) preloaded with all 230,614 transactions and 80 products.
- **`frontend/`**: Modern Next.js user interface with the Royal Indigo & Obsidian theme.
- **`data/private/`**: The complete offline dataset tables (Sales, Inventory, Master Products, Locations, Quality, Suppliers, Customers).
- **`Start-BusinessGate.bat` / `Stop-BusinessGate.bat`**: One-click launchers for Windows.
- **`Start-BusinessGate.sh`**: One-click launcher for macOS/Linux.

---

## 🔒 Security & Offline Guarantee

- **Zero Cloud Calls:** No telemetry, tracking, external CDNs, or remote API calls are made.
- **Data Privacy:** All business records and calculated recommendations remain strictly on your local disk.
