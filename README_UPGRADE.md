# MerchBrain upgrade notes
- Brand: El Sharnouby logo (frontend/public/brand/logo.png, favicon app/icon.png), dark sidebar, gold accent, new login.
- New pages: Command Center (home), Profit Leakage, Channel Allocation, Discount Intelligence, Supply Readiness (EN + AR).
- New backend: app/intelligence/{leakage,materials,allocation,discount,command}.py, app/api/commercial.py, tests in app/tests/test_commercial.py (57 backend tests pass).
- Run: ./run.sh (or run-windows.bat). First start imports the CSVs automatically; use "Refresh data" after changing files.
- Round 2: What-if Scenarios page, weekly PDF report (button on the Command Center), validation-gated advertising/website signals in the demand forecast (62 backend tests pass).
- Round 3: Customer Intelligence, downtime-vs-delay panel, "How numbers are calculated" page, Demo Story (63 backend tests pass).
