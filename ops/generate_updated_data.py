"""Generate refreshed and updated sample data through mid-November 2026 (2026-11-14)
matching the exact retail schemas of the user's ERP / Store tables.
"""
import sys
import shutil
import zipfile
from pathlib import Path
from datetime import datetime, date, timedelta
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
USER_UPLOAD_DIR = Path(r"C:\Users\EMadHamza\.gemini\antigravity\brain\2201ad41-5133-4dab-bb08-4c42bf15a6e7\.user_uploaded")
DOCS_SAMPLE_DIR = ROOT / "docs" / "sample_data"
RAW_DIR = ROOT / "data" / "private" / "raw_uploads"
PRIVATE_DIR = ROOT / "data" / "private"

DOCS_SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
RAW_DIR.mkdir(parents=True, exist_ok=True)

def main():
    print("=== Generating Updated Retail Sample Datasets ===")
    
    # 1. Customers
    cust_src = USER_UPLOAD_DIR / "media_1794741766212_fc6cccf6.csv"
    if not cust_src.exists():
        cust_src = RAW_DIR / "Customers.csv"
    cust_df = pd.read_csv(cust_src)
    cust_out_path = DOCS_SAMPLE_DIR / "Customers.csv"
    cust_df.to_csv(cust_out_path, index=False, encoding="utf-8-sig")
    cust_df.to_csv(RAW_DIR / "Customers.csv", index=False, encoding="utf-8-sig")
    print(f"-> Customers.csv saved: {len(cust_df)} rows")

    # 2. Locations
    loc_src = USER_UPLOAD_DIR / "media_1794741766220_30f51056.csv"
    if not loc_src.exists():
        loc_src = RAW_DIR / "Locations.csv"
    loc_df = pd.read_csv(loc_src)
    loc_out_path = DOCS_SAMPLE_DIR / "Locations.csv"
    loc_df.to_csv(loc_out_path, index=False, encoding="utf-8-sig")
    loc_df.to_csv(RAW_DIR / "Locations.csv", index=False, encoding="utf-8-sig")
    print(f"-> Locations.csv saved: {len(loc_df)} rows")

    # 3. Product-Master
    prod_src = USER_UPLOAD_DIR / "media_1794741766220_72c0f233.csv"
    if not prod_src.exists():
        prod_src = RAW_DIR / "Product-Master.csv"
    prod_df = pd.read_csv(prod_src)
    prod_out_path = DOCS_SAMPLE_DIR / "Product-Master.csv"
    prod_df.to_csv(prod_out_path, index=False, encoding="utf-8-sig")
    prod_df.to_csv(RAW_DIR / "Product-Master.csv", index=False, encoding="utf-8-sig")
    print(f"-> Product-Master.csv saved: {len(prod_df)} rows")

    # 4. Inventory-History
    inv_src = USER_UPLOAD_DIR / "media_1794741766221_fc3a4f16.csv"
    if not inv_src.exists():
        inv_src = RAW_DIR / "Inventory-History.csv"
    inv_raw = pd.read_csv(inv_src)

    # Separate historical waste and on-hand
    hist_waste = inv_raw[inv_raw["movement_type"] == "WASTE"].copy()
    on_hand_raw = inv_raw[inv_raw["movement_type"] == "ON_HAND"].copy()

    # Update ON_HAND date to yesterday (2026-11-14)
    target_on_hand_date = "2026-11-14"
    on_hand_updated = on_hand_raw.copy()
    on_hand_updated["date"] = target_on_hand_date

    # Generate additional WASTE records for 2026-10-18 to 2026-11-14
    start_dt = date(2026, 10, 18)
    end_dt = date(2026, 11, 14)
    delta_days = (end_dt - start_dt).days + 1

    prod_meta = prod_df.set_index("product_id").to_dict("index")
    loc_ids = loc_df["location_id"].unique().tolist()
    
    # Perishable / fresh products have higher waste probability
    fresh_cats = ["Fresh Produce", "Dairy", "Meat & Poultry", "Bakery", "Chilled Foods", "Groceries"]
    perishable_prods = prod_df[prod_df["category"].isin(fresh_cats)]["product_id"].tolist()
    if not perishable_prods:
        perishable_prods = prod_df["product_id"].tolist()

    np.random.seed(42)
    new_waste_records = []
    
    for day_i in range(delta_days):
        cur_d = start_dt + timedelta(days=day_i)
        cur_d_str = cur_d.isoformat()
        # ~18 to 25 waste incidents per day across the 6 locations
        n_incidents = np.random.randint(18, 25)
        for _ in range(n_incidents):
            pid = np.random.choice(perishable_prods)
            pm = prod_meta[pid]
            lid = np.random.choice(loc_ids)
            qty = int(np.random.randint(1, 14))
            cost = float(pm.get("cost_price", 10.0))
            val = round(cost * qty, 2)
            sup = str(pm.get("primary_supplier", "Al Meera Supply"))
            
            new_waste_records.append({
                "date": cur_d_str,
                "product_id": pid,
                "product_name": pm.get("product_name", pid),
                "category": pm.get("category", "Groceries"),
                "location_id": lid,
                "quantity_on_hand": qty,
                "cost": cost,
                "stock_value": val,
                "movement_type": "WASTE",
                "supplier": sup
            })

    new_waste_df = pd.DataFrame(new_waste_records)
    print(f"Generated {len(new_waste_df)} new daily waste records up to {target_on_hand_date}")

    # Combine: ON_HAND snapshot (dated 2026-11-14) first, then all historical + recent waste
    combined_inv = pd.concat([on_hand_updated, hist_waste, new_waste_df], ignore_index=True)
    inv_out_path = DOCS_SAMPLE_DIR / "Inventory-History.csv"
    combined_inv.to_csv(inv_out_path, index=False, encoding="utf-8-sig")
    combined_inv.to_csv(RAW_DIR / "Inventory-History.csv", index=False, encoding="utf-8-sig")
    print(f"-> Inventory-History.csv saved: {len(combined_inv)} rows (Dates: {combined_inv['date'].min()} to {combined_inv['date'].max()})")

    # 5. Sales-Transactions
    sales_src = RAW_DIR / "Sales-Transactions.csv"
    if sales_src.exists():
        sales_raw = pd.read_csv(sales_src)
        print(f"Existing sales transactions: {len(sales_raw)} rows (up to {sales_raw['date'].max()})")
        
        # Generate transactions for 2026-10-18 to 2026-11-14
        cust_ids = cust_df["customer_id"].tolist()
        max_txn_num = int(sales_raw["transaction_id"].str.extract(r'(\d+)')[0].dropna().astype(int).max())
        
        new_sales_records = []
        for day_i in range(delta_days):
            cur_d = start_dt + timedelta(days=day_i)
            cur_d_str = cur_d.isoformat()
            # Generate ~2,400 realistic retail transactions per day
            n_txns = np.random.randint(2300, 2600)
            p_choices = np.random.choice(prod_df["product_id"].tolist(), size=n_txns)
            l_choices = np.random.choice(loc_ids, size=n_txns)
            c_choices = np.random.choice(cust_ids, size=n_txns)
            q_choices = np.random.choice([1, 1, 1, 2, 2, 3, 4, 5], size=n_txns)

            for j in range(n_txns):
                max_txn_num += 1
                pid = p_choices[j]
                pm = prod_meta[pid]
                qty = int(q_choices[j])
                sp = float(pm.get("selling_price", 20.0))
                tot = round(sp * qty, 2)
                
                new_sales_records.append({
                    "transaction_id": f"TXN-{max_txn_num:06d}",
                    "date": cur_d_str,
                    "product_id": pid,
                    "product_name": pm.get("product_name", pid),
                    "category": pm.get("category", "Groceries"),
                    "quantity": qty,
                    "selling_price": sp,
                    "total_amount": tot,
                    "location_id": l_choices[j],
                    "customer_id": c_choices[j]
                })

        new_sales_df = pd.DataFrame(new_sales_records)
        print(f"Generated {len(new_sales_df)} new sales transactions up to {target_on_hand_date}")
        
        full_sales_df = pd.concat([sales_raw, new_sales_df], ignore_index=True)
        full_sales_path = DOCS_SAMPLE_DIR / "Sales-Transactions.csv"
        full_sales_df.to_csv(full_sales_path, index=False, encoding="utf-8-sig")
        full_sales_df.to_csv(RAW_DIR / "Sales-Transactions.csv", index=False, encoding="utf-8-sig")
        print(f"-> Full Sales-Transactions.csv saved: {len(full_sales_df)} rows")

        # Also create a quick-test sample dataset (last 10 days, ~15,000 rows)
        sample_sales_df = full_sales_df[full_sales_df["date"] >= "2026-11-05"].copy()
        sample_sales_path = DOCS_SAMPLE_DIR / "Sales-Transactions-Sample.csv"
        sample_sales_df.to_csv(sample_sales_path, index=False, encoding="utf-8-sig")
        print(f"-> Quick Sample Sales-Transactions-Sample.csv saved: {len(sample_sales_df)} rows")

    # 6. Returns Data (returns_data.csv)
    # This directly fulfills the system's "⚠️ يُنصح برفع جدول الأسبوع الأخير" notification
    print("Generating returns_data.csv (Returns and Quality defects)...")
    returns_records = []
    ret_reasons = [
        ("Near Expiry", "Yes"),
        ("Defective Packaging", "Yes"),
        ("Customer Changed Mind", "No"),
        ("Quality Below Standard", "Yes"),
        ("Wrong Item Delivered", "No"),
        ("Spoiled / Temperature Issue", "Yes")
    ]
    
    # 2,500 return incidents from July 20 to Nov 14, with dense records in the latest week (Nov 8 to 14)
    ret_start = date(2026, 7, 20)
    ret_days = (end_dt - ret_start).days + 1
    ret_id_counter = 1000

    for day_i in range(ret_days):
        cur_d = ret_start + timedelta(days=day_i)
        cur_d_str = cur_d.isoformat()
        # More records in recent days
        n_rets = np.random.randint(22, 35) if cur_d >= date(2026, 11, 8) else np.random.randint(15, 25)
        for _ in range(n_rets):
            ret_id_counter += 1
            pid = np.random.choice(prod_df["product_id"].tolist())
            pm = prod_meta[pid]
            lid = np.random.choice(loc_ids)
            cid = np.random.choice(cust_df["customer_id"].tolist())
            reason_pair = ret_reasons[np.random.randint(0, len(ret_reasons))]
            reason, is_qc = reason_pair
            qty = int(np.random.randint(1, 6))
            sp = float(pm.get("selling_price", 25.0))
            refund = round(sp * qty, 2)
            
            returns_records.append({
                "return_id": f"RET-{ret_id_counter:05d}",
                "return_date": cur_d_str,
                "transaction_id": f"TXN-{(ret_id_counter + 400000):06d}",
                "product_id": pid,
                "product_name": pm.get("product_name", pid),
                "category": pm.get("category", "Groceries"),
                "location_id": lid,
                "customer_id": cid,
                "return_reason": reason,
                "quantity": qty,
                "refund_amount": refund,
                "quality_issue": is_qc
            })

    returns_df = pd.DataFrame(returns_records)
    returns_out_path = DOCS_SAMPLE_DIR / "returns_data.csv"
    returns_df.to_csv(returns_out_path, index=False, encoding="utf-8-sig")
    returns_df.to_csv(RAW_DIR / "returns_data.csv", index=False, encoding="utf-8-sig")
    print(f"-> returns_data.csv saved: {len(returns_df)} rows (Dates up to {returns_df['return_date'].max()})")

    # 7. Package everything into a single downloadable ZIP archive
    zip_path = DOCS_SAMPLE_DIR / "BusinessGate_Updated_Retail_Samples.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(cust_out_path, arcname="Customers.csv")
        z.write(loc_out_path, arcname="Locations.csv")
        z.write(prod_out_path, arcname="Product-Master.csv")
        z.write(inv_out_path, arcname="Inventory-History.csv")
        z.write(returns_out_path, arcname="returns_data.csv")
        if (DOCS_SAMPLE_DIR / "Sales-Transactions-Sample.csv").exists():
            z.write(DOCS_SAMPLE_DIR / "Sales-Transactions-Sample.csv", arcname="Sales-Transactions-Sample.csv")
    print(f"-> ZIP package created: {zip_path.name} ({zip_path.stat().st_size / 1024:.1f} KB)")
    print("=== Generation Complete Successfully! ===")

if __name__ == "__main__":
    main()
