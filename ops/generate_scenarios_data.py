"""Generate 3 distinct realistic retail scenarios for different locations
with distinct leakage characteristics, KPI outcomes, and data profiles.
"""
import zipfile
from pathlib import Path
from datetime import datetime, date, timedelta
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DIR = ROOT / "docs" / "sample_data"
SCENARIOS_DIR = SAMPLE_DIR / "scenarios"
SCENARIOS_DIR.mkdir(parents=True, exist_ok=True)

# Base data
base_prod = pd.read_csv(SAMPLE_DIR / "Product-Master.csv")
base_cust = pd.read_csv(SAMPLE_DIR / "Customers.csv")
base_loc = pd.read_csv(SAMPLE_DIR / "Locations.csv")

def generate_scenario_1_superstore():
    """Scenario 1: Superstore Hub (LOC-005) - Massive Spoilage & Stagnant Overstock"""
    sdir = SCENARIOS_DIR / "scenario1_superstore_spoilage"
    sdir.mkdir(parents=True, exist_ok=True)
    print("Generating Scenario 1: Superstore Hub (High Spoilage & Overstock)...")

    # 1. Locations: LOC-005 highlighted
    locs = base_loc.copy()
    locs.to_csv(sdir / "Locations.csv", index=False, encoding="utf-8-sig")

    # 2. Customers
    base_cust.to_csv(sdir / "Customers.csv", index=False, encoding="utf-8-sig")

    # 3. Product-Master
    base_prod.to_csv(sdir / "Product-Master.csv", index=False, encoding="utf-8-sig")
    prod_meta = base_prod.set_index("product_id").to_dict("index")

    # 4. Inventory-History: High On-Hand (overstocked across 68 products) + Heavy Spoilage
    on_hand_records = []
    waste_records = []
    np.random.seed(101)

    # On Hand dated 2026-11-14
    for pid, pm in prod_meta.items():
        min_s = int(pm.get("min_stock", 50))
        cost = float(pm.get("cost_price", 15.0))
        # 85% of products are heavily overstocked (3x to 6x min stock)
        qty = int(min_s * np.random.uniform(3.5, 6.0)) if np.random.rand() < 0.85 else int(min_s * 1.2)
        val = round(qty * cost, 2)
        on_hand_records.append({
            "date": "2026-11-14",
            "product_id": pid,
            "product_name": pm.get("product_name", pid),
            "category": pm.get("category", "Groceries"),
            "location_id": "LOC-005",
            "quantity_on_hand": qty,
            "cost": cost,
            "stock_value": val,
            "movement_type": "ON_HAND",
            "supplier": pm.get("primary_supplier", "Al Meera Supply")
        })

    # High Spoilage WASTE records (Fresh meats, dairy, produce spoiled due to cold-chain & over-ordering)
    fresh_pids = base_prod[base_prod["category"].isin(["Fresh Meat", "Dairy", "Fresh Produce", "Bakery", "Chilled Foods"])]["product_id"].tolist()
    if not fresh_pids:
        fresh_pids = base_prod["product_id"].tolist()[:30]

    start_d = date(2026, 8, 1)
    end_d = date(2026, 11, 14)
    days = (end_d - start_d).days + 1

    for day_i in range(days):
        cur_d = (start_d + timedelta(days=day_i)).isoformat()
        # Heavy waste: 12-20 items spoiled daily
        n_waste = np.random.randint(12, 20)
        for _ in range(n_waste):
            pid = np.random.choice(fresh_pids)
            pm = prod_meta[pid]
            qty = int(np.random.randint(4, 18))
            cost = float(pm.get("cost_price", 20.0))
            waste_records.append({
                "date": cur_d,
                "product_id": pid,
                "product_name": pm.get("product_name", pid),
                "category": pm.get("category", "Groceries"),
                "location_id": "LOC-005",
                "quantity_on_hand": qty,
                "cost": cost,
                "stock_value": round(qty * cost, 2),
                "movement_type": "WASTE",
                "supplier": pm.get("primary_supplier", "Al Meera Supply")
            })

    inv_df = pd.DataFrame(on_hand_records + waste_records)
    inv_df.to_csv(sdir / "Inventory-History.csv", index=False, encoding="utf-8-sig")

    # 5. Sales Transactions
    sales_records = []
    txn_id = 100000
    for day_i in range(days):
        cur_d = (start_d + timedelta(days=day_i)).isoformat()
        n_sales = np.random.randint(120, 180)
        for _ in range(n_sales):
            txn_id += 1
            pid = np.random.choice(base_prod["product_id"].tolist())
            pm = prod_meta[pid]
            qty = np.random.choice([1, 2, 3, 4], p=[0.5, 0.3, 0.15, 0.05])
            sp = float(pm.get("selling_price", 30.0))
            sales_records.append({
                "transaction_id": f"TXN-S1-{txn_id:06d}",
                "date": cur_d,
                "product_id": pid,
                "product_name": pm.get("product_name", pid),
                "category": pm.get("category", "Groceries"),
                "quantity": qty,
                "selling_price": sp,
                "total_amount": round(sp * qty, 2),
                "location_id": "LOC-005",
                "customer_id": np.random.choice(base_cust["customer_id"].tolist())
            })
    sales_df = pd.DataFrame(sales_records)
    sales_df.to_csv(sdir / "Sales-Transactions.csv", index=False, encoding="utf-8-sig")

    # 6. Returns Data (Mostly Expiry & Spoilage reasons)
    returns_records = []
    ret_id = 50000
    for day_i in range(days):
        cur_d = (start_d + timedelta(days=day_i)).isoformat()
        for _ in range(np.random.randint(3, 8)):
            ret_id += 1
            pid = np.random.choice(fresh_pids)
            pm = prod_meta[pid]
            qty = int(np.random.randint(1, 4))
            sp = float(pm.get("selling_price", 25.0))
            returns_records.append({
                "return_id": f"RET-S1-{ret_id:05d}",
                "return_date": cur_d,
                "transaction_id": f"TXN-S1-{(ret_id+50000):06d}",
                "product_id": pid,
                "product_name": pm.get("product_name", pid),
                "category": pm.get("category", "Groceries"),
                "location_id": "LOC-005",
                "customer_id": np.random.choice(base_cust["customer_id"].tolist()),
                "return_reason": np.random.choice(["Near Expiry", "Spoiled / Temperature Issue", "Defective Packaging"]),
                "quantity": qty,
                "refund_amount": round(sp * qty, 2),
                "quality_issue": "Yes"
            })
    ret_df = pd.DataFrame(returns_records)
    ret_df.to_csv(sdir / "returns_data.csv", index=False, encoding="utf-8-sig")

    # Zip
    zip_path = SCENARIOS_DIR / "Scenario1_Superstore_Hub.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sdir.glob("*.csv"):
            z.write(f, arcname=f.name)
    print(f"-> Scenario 1 ready: {len(inv_df)} inv rows, {len(sales_df)} sales rows. Zip: {zip_path.name}")

def generate_scenario_2_express():
    """Scenario 2: Express Downtown Store (LOC-003) - Severe Stockouts & Lost Revenue"""
    sdir = SCENARIOS_DIR / "scenario2_express_stockouts"
    sdir.mkdir(parents=True, exist_ok=True)
    print("Generating Scenario 2: Express Downtown (High Stockout & Lost Sales)...")

    base_loc.to_csv(sdir / "Locations.csv", index=False, encoding="utf-8-sig")
    base_cust.to_csv(sdir / "Customers.csv", index=False, encoding="utf-8-sig")
    base_prod.to_csv(sdir / "Product-Master.csv", index=False, encoding="utf-8-sig")
    prod_meta = base_prod.set_index("product_id").to_dict("index")

    # Inventory: Very low on hand (58 products have 0 stock or critical understock < 5 units)
    on_hand_records = []
    waste_records = []
    np.random.seed(202)

    for pid, pm in prod_meta.items():
        min_s = int(pm.get("min_stock", 50))
        cost = float(pm.get("cost_price", 15.0))
        # 70% of products are completely stocked out (0 stock) or critically low (1-3 units)
        is_stockout = np.random.rand() < 0.72
        qty = 0 if np.random.rand() < 0.55 and is_stockout else (int(np.random.randint(1, 4)) if is_stockout else int(min_s * 0.8))
        on_hand_records.append({
            "date": "2026-11-14",
            "product_id": pid,
            "product_name": pm.get("product_name", pid),
            "category": pm.get("category", "Groceries"),
            "location_id": "LOC-003",
            "quantity_on_hand": qty,
            "cost": cost,
            "stock_value": round(qty * cost, 2),
            "movement_type": "ON_HAND",
            "supplier": pm.get("primary_supplier", "Al Meera Supply")
        })

    # Minimal waste (almost zero food waste because stock sells out instantly)
    start_d = date(2026, 8, 1)
    end_d = date(2026, 11, 14)
    days = (end_d - start_d).days + 1
    for day_i in range(days):
        if np.random.rand() < 0.2:  # Only waste on 20% of days
            cur_d = (start_d + timedelta(days=day_i)).isoformat()
            pid = np.random.choice(base_prod["product_id"].tolist())
            pm = prod_meta[pid]
            waste_records.append({
                "date": cur_d,
                "product_id": pid,
                "product_name": pm.get("product_name", pid),
                "category": pm.get("category", "Groceries"),
                "location_id": "LOC-003",
                "quantity_on_hand": 1,
                "cost": float(pm.get("cost_price", 10.0)),
                "stock_value": float(pm.get("cost_price", 10.0)),
                "movement_type": "WASTE",
                "supplier": pm.get("primary_supplier", "Al Meera Supply")
            })

    inv_df = pd.DataFrame(on_hand_records + waste_records)
    inv_df.to_csv(sdir / "Inventory-History.csv", index=False, encoding="utf-8-sig")

    # High footfall sales (frequent single-item fast purchases)
    sales_records = []
    txn_id = 200000
    for day_i in range(days):
        cur_d = (start_d + timedelta(days=day_i)).isoformat()
        n_sales = np.random.randint(150, 220)
        for _ in range(n_sales):
            txn_id += 1
            pid = np.random.choice(base_prod["product_id"].tolist())
            pm = prod_meta[pid]
            qty = np.random.choice([1, 2], p=[0.85, 0.15])
            sp = float(pm.get("selling_price", 20.0))
            sales_records.append({
                "transaction_id": f"TXN-S2-{txn_id:06d}",
                "date": cur_d,
                "product_id": pid,
                "product_name": pm.get("product_name", pid),
                "category": pm.get("category", "Groceries"),
                "quantity": qty,
                "selling_price": sp,
                "total_amount": round(sp * qty, 2),
                "location_id": "LOC-003",
                "customer_id": np.random.choice(base_cust["customer_id"].tolist())
            })
    sales_df = pd.DataFrame(sales_records)
    sales_df.to_csv(sdir / "Sales-Transactions.csv", index=False, encoding="utf-8-sig")

    # Returns: Minimal
    ret_records = []
    ret_id = 60000
    for day_i in range(days):
        if np.random.rand() < 0.4:
            cur_d = (start_d + timedelta(days=day_i)).isoformat()
            ret_id += 1
            pid = np.random.choice(base_prod["product_id"].tolist())
            pm = prod_meta[pid]
            ret_records.append({
                "return_id": f"RET-S2-{ret_id:05d}",
                "return_date": cur_d,
                "transaction_id": f"TXN-S2-{(ret_id+60000):06d}",
                "product_id": pid,
                "product_name": pm.get("product_name", pid),
                "category": pm.get("category", "Groceries"),
                "location_id": "LOC-003",
                "customer_id": np.random.choice(base_cust["customer_id"].tolist()),
                "return_reason": "Customer Changed Mind",
                "quantity": 1,
                "refund_amount": float(pm.get("selling_price", 20.0)),
                "quality_issue": "No"
            })
    ret_df = pd.DataFrame(ret_records)
    ret_df.to_csv(sdir / "returns_data.csv", index=False, encoding="utf-8-sig")

    zip_path = SCENARIOS_DIR / "Scenario2_Express_Downtown.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sdir.glob("*.csv"):
            z.write(f, arcname=f.name)
    print(f"-> Scenario 2 ready: {len(inv_df)} inv rows, {len(sales_df)} sales rows. Zip: {zip_path.name}")

def generate_scenario_3_wholesale_online():
    """Scenario 3: Online & Wholesale Hub (LOC-006) - Heavy Discount Leakage & Shipping Returns"""
    sdir = SCENARIOS_DIR / "scenario3_online_wholesale"
    sdir.mkdir(parents=True, exist_ok=True)
    print("Generating Scenario 3: Online & Wholesale (Excessive Discounts & Delivery Returns)...")

    base_loc.to_csv(sdir / "Locations.csv", index=False, encoding="utf-8-sig")
    base_cust.to_csv(sdir / "Customers.csv", index=False, encoding="utf-8-sig")
    base_prod.to_csv(sdir / "Product-Master.csv", index=False, encoding="utf-8-sig")
    prod_meta = base_prod.set_index("product_id").to_dict("index")

    # Inventory: Balanced warehouse stock, high volume
    on_hand_records = []
    waste_records = []
    np.random.seed(303)

    for pid, pm in prod_meta.items():
        min_s = int(pm.get("min_stock", 50))
        cost = float(pm.get("cost_price", 15.0))
        qty = int(min_s * np.random.uniform(2.0, 3.5))
        on_hand_records.append({
            "date": "2026-11-14",
            "product_id": pid,
            "product_name": pm.get("product_name", pid),
            "category": pm.get("category", "Groceries"),
            "location_id": "LOC-006",
            "quantity_on_hand": qty,
            "cost": cost,
            "stock_value": round(qty * cost, 2),
            "movement_type": "ON_HAND",
            "supplier": pm.get("primary_supplier", "Al Meera Supply")
        })

    start_d = date(2026, 8, 1)
    end_d = date(2026, 11, 14)
    days = (end_d - start_d).days + 1

    # Handling waste during packaging / shipping
    for day_i in range(days):
        cur_d = (start_d + timedelta(days=day_i)).isoformat()
        for _ in range(np.random.randint(2, 6)):
            pid = np.random.choice(base_prod["product_id"].tolist())
            pm = prod_meta[pid]
            qty = int(np.random.randint(2, 6))
            cost = float(pm.get("cost_price", 15.0))
            waste_records.append({
                "date": cur_d,
                "product_id": pid,
                "product_name": pm.get("product_name", pid),
                "category": pm.get("category", "Groceries"),
                "location_id": "LOC-006",
                "quantity_on_hand": qty,
                "cost": cost,
                "stock_value": round(qty * cost, 2),
                "movement_type": "WASTE",
                "supplier": pm.get("primary_supplier", "Al Meera Supply")
            })

    inv_df = pd.DataFrame(on_hand_records + waste_records)
    inv_df.to_csv(sdir / "Inventory-History.csv", index=False, encoding="utf-8-sig")

    # Sales with HEAVY DISCOUNTS (15% to 35% discount eating gross profit margin!)
    sales_records = []
    txn_id = 300000
    for day_i in range(days):
        cur_d = (start_d + timedelta(days=day_i)).isoformat()
        n_sales = np.random.randint(110, 160)
        for _ in range(n_sales):
            txn_id += 1
            pid = np.random.choice(base_prod["product_id"].tolist())
            pm = prod_meta[pid]
            qty = int(np.random.randint(2, 8))
            list_sp = float(pm.get("selling_price", 30.0))
            # 65% of orders get heavy coupon discounts (15% to 35%)
            disc_pct = np.random.choice([0.15, 0.20, 0.25, 0.30, 0.35]) if np.random.rand() < 0.65 else 0.0
            actual_sp = round(list_sp * (1.0 - disc_pct), 2)
            tot = round(actual_sp * qty, 2)
            sales_records.append({
                "transaction_id": f"TXN-S3-{txn_id:06d}",
                "date": cur_d,
                "product_id": pid,
                "product_name": pm.get("product_name", pid),
                "category": pm.get("category", "Groceries"),
                "quantity": qty,
                "selling_price": actual_sp,
                "total_amount": tot,
                "location_id": "LOC-006",
                "customer_id": np.random.choice(["CUST-004", "CUST-005"]) # Online / Wholesale clients
            })
    sales_df = pd.DataFrame(sales_records)
    sales_df.to_csv(sdir / "Sales-Transactions.csv", index=False, encoding="utf-8-sig")

    # High returns due to shipping damage, late deliveries, wrong item
    ret_records = []
    ret_id = 70000
    reasons = ["Delivery Delayed / Order Cancelled", "Damaged in Shipping", "Wrong Item Delivered", "Quality Below Standard"]
    for day_i in range(days):
        cur_d = (start_d + timedelta(days=day_i)).isoformat()
        for _ in range(np.random.randint(6, 14)):
            ret_id += 1
            pid = np.random.choice(base_prod["product_id"].tolist())
            pm = prod_meta[pid]
            qty = int(np.random.randint(1, 4))
            sp = float(pm.get("selling_price", 25.0))
            ret_records.append({
                "return_id": f"RET-S3-{ret_id:05d}",
                "return_date": cur_d,
                "transaction_id": f"TXN-S3-{(ret_id+70000):06d}",
                "product_id": pid,
                "product_name": pm.get("product_name", pid),
                "category": pm.get("category", "Groceries"),
                "location_id": "LOC-006",
                "customer_id": np.random.choice(base_cust["customer_id"].tolist()),
                "return_reason": np.random.choice(reasons),
                "quantity": qty,
                "refund_amount": round(sp * qty, 2),
                "quality_issue": "Yes" if "Damaged" in str(reasons) else "No"
            })
    ret_df = pd.DataFrame(ret_records)
    ret_df.to_csv(sdir / "returns_data.csv", index=False, encoding="utf-8-sig")

    zip_path = SCENARIOS_DIR / "Scenario3_Online_Wholesale.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sdir.glob("*.csv"):
            z.write(f, arcname=f.name)
    print(f"-> Scenario 3 ready: {len(inv_df)} inv rows, {len(sales_df)} sales rows. Zip: {zip_path.name}")

def package_master_all():
    master_zip = SAMPLE_DIR / "All_Scenarios_Retail_Package.zip"
    with zipfile.ZipFile(master_zip, "w", zipfile.ZIP_DEFLATED) as z:
        for p in SCENARIOS_DIR.rglob("*.csv"):
            rel = p.relative_to(SCENARIOS_DIR)
            z.write(p, arcname=str(rel))
    print(f"-> Master package created: {master_zip.name} ({master_zip.stat().st_size / 1024:.1f} KB)")

if __name__ == "__main__":
    generate_scenario_1_superstore()
    generate_scenario_2_express()
    generate_scenario_3_wholesale_online()
    package_master_all()
    print("=== All 3 Scenarios Generated Successfully! ===")
