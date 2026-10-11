import os, shutil, tempfile
import pandas as pd
from app.ingestion.specs import FILES
from app.validation.validator import read_csv, validate_frame
from app.tests.synth import generate


def _spec(name): return FILES[name]


def test_missing_required_column_gives_friendly_message():
    raw = pd.DataFrame({"Snapshot_Month": ["2026-01-01"], "Location_ID": ["LOC001"]})
    r = validate_frame(_spec("Inventory_History.csv"), raw, {})
    assert r.fatal and "Inventory_History.csv is missing required column" in r.fatal and "Product_ID" in r.fatal
    assert "KeyError" not in r.fatal


def test_bad_rows_are_quarantined_not_crashing():
    d = tempfile.mkdtemp(); generate(d, months=4, n_products=3)
    raw = read_csv(os.path.join(d, "Sales_Transactions.csv"))
    n = len(raw)
    raw.loc[0, "Quantity"] = "-5"                         # impossible quantity
    raw.loc[1, "Order_Date"] = "2026-13-45"               # invalid date
    raw.loc[2, "Product_ID"] = "P999"                     # invalid foreign key
    raw.loc[3, "Row_ID"] = raw.loc[4, "Row_ID"]           # duplicate primary key
    raw.loc[5, "Net_Sales_EGP"] = "abc"                   # not a number
    refs = {"product_master": {f"P{i:03d}" for i in range(1, 4)}, "customers": {f"C{i:05d}" for i in range(1, 301)}, "locations": {"LOC001", "LOC002", "LOC003"}}
    r = validate_frame(_spec("Sales_Transactions.csv"), raw, refs)
    assert r.fatal is None and r.rows_clean == n - 5 and r.rows_rejected == 5
    reasons = " | ".join(q["reason"] for q in r.quarantine)
    for needle in ("Quantity", "not a valid date", "does not exist in product_master", "duplicate primary key", "not a valid number"):
        assert needle in reasons


def test_literal_None_is_a_real_category_not_null():
    d = tempfile.mkdtemp(); generate(d, months=4, n_products=3)
    raw = read_csv(os.path.join(d, "Quality.csv"))
    assert (raw.Defect_Type == "None").any()
    r = validate_frame(_spec("Quality.csv"), raw, {"product_master": {f"P{i:03d}" for i in range(1, 4)}})
    assert (r.clean.Defect_Type == "None").any() and r.clean.Defect_Type.notna().all()


def test_stale_data_flagged():
    d = tempfile.mkdtemp(); generate(d, months=4, n_products=3)
    raw = read_csv(os.path.join(d, "Web_Traffic_Daily.csv"))
    r = validate_frame(_spec("Web_Traffic_Daily.csv"), raw, {}, stale_days=30)
    assert any(i["rule"] == "stale_data" for i in r.issues)


def test_sum_rule_catches_material_mismatch():
    d = tempfile.mkdtemp(); generate(d, months=4, n_products=3)
    raw = read_csv(os.path.join(d, "Purchase_Orders.csv")); raw.loc[0, "Accepted_Qty"] = "1"
    r = validate_frame(_spec("Purchase_Orders.csv"), raw, {"suppliers": {f"SUP0{i}" for i in range(1, 5)}, "materials": {"M001", "M002", "M003"}})
    assert r.rows_rejected >= 1 and any("does not equal" in q["reason"] for q in r.quarantine)


def test_full_import_run(client, ceo, loaded):
    res = loaded["result"]
    assert res["files_processed"] == 20 and res["rows_loaded"] > 10000 and res["rows_rejected"] == 0
    h = client.get("/api/v1/data/health", headers=ceo).json()
    assert h["overall"] in ("HEALTHY", "ATTENTION") and len(h["files"]) == 20 and h["last_refresh"]["status"] == "SUCCESS"
    assert h["freshness"]["data_updated_at"] and h["data_provenance"]["modeled_files"] == []


def test_import_survives_a_broken_file_and_keeps_good_data(client, ceo, loaded, data_dir):
    bad = os.path.join(data_dir, "Quality.csv"); good = open(bad, "rb").read()
    df = pd.read_csv(bad, dtype=str, keep_default_na=False).drop(columns=["Product_ID"]); df.to_csv(bad, index=False)
    try:
        r = client.post("/api/v1/data/import?wait=true", headers=ceo).json()
        assert r["result"]["failed_files"] == ["Quality.csv"] and r["result"]["status"] == "PARTIAL"
        h = client.get("/api/v1/data/health", headers=ceo).json()
        assert "Quality.csv" in h["failed_files"]
        q = next(f for f in h["files"] if f["file"] == "Quality.csv")
        assert "missing required column" in q["message"] and "Product_ID" in q["message"]
    finally:
        open(bad, "wb").write(good)
        client.post("/api/v1/data/import?wait=true", headers=ceo)


def test_validate_endpoint_does_not_load(client, ceo, loaded):
    r = client.post("/api/v1/data/validate?wait=true", headers=ceo)
    assert r.status_code == 202 and r.json()["result"]["mode"] == "validate"
