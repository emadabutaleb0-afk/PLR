"""Synthetic data generator - tests, CI and public demos ONLY. Schema-identical to the 20 company files.
The real application never needs this: it runs on the CSVs in DATA_DIRECTORY."""
from __future__ import annotations
import csv, os
from datetime import date, timedelta
import numpy as np
import pandas as pd
from app.ingestion.specs import FILES, LOAD_ORDER

LOCS = [("LOC001", "Test Store Alex", "Retail Store", "Retail"), ("LOC002", "Test Online", "Online", "Online"), ("LOC003", "Test Wholesale", "Wholesale", "Wholesale")]


def generate(out_dir: str, seed: int = 7, months: int = 30, n_products: int = 10, end: date = date(2026, 9, 30)) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    rng = np.random.default_rng(seed)
    month_starts = pd.date_range(end=pd.Timestamp(end).replace(day=1), periods=months, freq="MS")
    fams = ["Pajamas/Homewear", "T-Shirts", "Sweatshirts", "Kids Sets"]
    pm = pd.DataFrame([dict(Product_ID=f"P{i:03d}", SKU=f"SKU-{i:03d}", Product_Name=f"Test Product {i}", Brand="Leo Moda", Product_Family=fams[i % 4], Gender="Girls", Audience="Kids",
                            Catalog_Season="Summer 2026" if i % 2 else "Autumn 2025", Sizes="4, 6, 8, 10, 12" if i % 3 else "M, L, XL, 2XL", Public_Retail_Price_EGP=300 + 10 * i,
                            Public_Catalog_Source="https://example.test", Verification_Class="Synthetic test") for i in range(1, n_products + 1)])
    loc = pd.DataFrame([dict(Location_ID=a, Location_Name=b, Location_Type=c, Channel=d, Governorate="Alexandria", City="X", Public_Address="-", Source_URL="-", Verification_Class="Synthetic test") for a, b, c, d in LOCS])
    cust = pd.DataFrame([dict(Customer_ID=f"C{i:05d}", Customer_Type="Retail" if i % 4 else "Wholesale", Governorate="Cairo", Age_Band="25-34", Gender="Female", Join_Date="2024-01-15",
                              Acquisition_Channel="Organic", Consent_Status="Opted-in", Data_Class="Synthetic test customer") for i in range(1, 301)])
    sizes_of = lambda s: [x.strip() for x in s.split(",")]
    sales, inv_rows = [], []
    row_id = 0
    # product-location personalities: some surplus (slow), some shortage (fast)
    for pi, p in pm.iterrows():
        for li, (lid, lname, _, ch) in enumerate(LOCS):
            base = {0: 1.2, 1: 2.0, 2: 14.0}[li] * (0.6 + 0.12 * pi)
            slow = (pi + li) % 5 == 0
            stock = 400 if slow else 60
            sold_hist = []
            for mi, ms in enumerate(month_starts):
                season = 1 + 0.35 * np.sin(2 * np.pi * (ms.month - 3) / 12)
                lam = base * season * (0.25 if slow and mi > months - 8 else 1.0) * 30
                q_total = int(rng.poisson(max(lam, 1)))
                demand = q_total
                sold = min(demand, stock + 120)
                n_lines = max(1, min(sold, 8))
                splits = np.array_split(np.full(sold, 1), n_lines) if sold else []
                for ln, part in enumerate(splits):
                    qty = int(len(part))
                    if qty == 0: continue
                    row_id += 1
                    d = ms + timedelta(days=int(rng.integers(0, 27)))
                    lst = float(p.Public_Retail_Price_EGP); disc = float(rng.choice([0, .1, .15, .3])) if ch == "Wholesale" else float(rng.choice([0, .05, .1]))
                    net = lst * qty * (1 - disc); cogs = lst * qty * 0.55; ret = rng.random() < 0.05; qret = ret and rng.random() < 0.4
                    sales.append(dict(Row_ID=row_id, Invoice_ID=f"INV{row_id:07d}", Order_Date=d.date().isoformat(), Month_Key=ms.strftime("%Y-%m"), Location_ID=lid, Location_Name=lname, Channel=ch,
                                      Customer_ID=f"C{int(rng.integers(1, 301)):05d}", Customer_Type="Retail", Customer_Governorate="Cairo", Product_ID=p.Product_ID, SKU=p.SKU, Product_Name=p.Product_Name,
                                      Product_Family=p.Product_Family, Size=rng.choice(sizes_of(p.Sizes)), Quantity=qty, List_Price_EGP=lst, Discount_Pct=disc, Gross_Sales_EGP=lst * qty,
                                      Net_Sales_EGP=round(net, 2), Estimated_COGS_EGP=round(cogs, 2), Gross_Profit_EGP=round(net - cogs, 2), Gross_Margin_Pct=round((net - cogs) / net, 4),
                                      Payment_Method="Cash", Returned="Yes" if ret else "No", Return_Date=(d + timedelta(days=5)).date().isoformat() if ret else "", Return_Reason="Size / fit" if ret else "No return",
                                      Refund_Value_EGP=round(net, 2) if ret else 0, Quality_Related_Return="Yes" if qret else "No", Data_Class="Synthetic test"))
                opening = stock
                received = int(max(0, base * 30 * (3.5 if slow else 1.1) + rng.integers(0, 20)))
                closing = max(0, opening + received - sold)
                so_days = int(rng.integers(3, 12)) if closing == 0 and demand > sold else 0
                sold_hist.append(sold)
                avg90 = max(sum(sold_hist[-3:]) / (30 * min(len(sold_hist), 3)), 0.05)
                inv_rows.append(dict(Snapshot_Month=ms.date().isoformat(), Location_ID=lid, Location_Name=lname, Product_ID=p.Product_ID, SKU=p.SKU, Product_Name=p.Product_Name, Opening_Stock=opening,
                                     Received_Qty=received, Sold_Qty=sold, Returned_Qty=0, Damaged_Qty=0, Closing_Stock=closing, Avg_Daily_Sales_90D=round(avg90, 2), Safety_Stock_Units=10,
                                     Reorder_Point_Units=int(avg90 * 14), Supplier_Lead_Time_Days=7, Days_of_Cover=round(closing / avg90, 1), Stockout_Days_In_Month=so_days, Data_Class="Synthetic test"))
                stock = closing
    sup = pd.DataFrame([dict(Supplier_ID=f"SUP{i:02d}", Supplier_Name=f"Test Supplier {i}", Primary_Category="Fabric", Governorate="Cairo", Payment_Terms_Days=30, Contracted="Yes", Data_Class="Synthetic") for i in range(1, 5)])
    mat = pd.DataFrame([dict(Material_ID=f"M{i:03d}", Material_Name=f"Material {i}", Unit="meter", Material_Category="Fabric", Standard_Lead_Time_Days=10, Data_Class="Synthetic") for i in range(1, 4)])
    bom = pd.DataFrame([dict(Product_ID=p, Product_Name="x", Material_ID=m, Material_Name="x", Required_Per_Unit=1.1, Unit="meter", Data_Class="Synthetic") for p in pm.Product_ID for m in ("M001", "M002")])
    pos = []
    for i in range(1, 241):
        od = date(2024, 1, 1) + timedelta(days=int(rng.integers(0, 900))); prm = od + timedelta(days=14); act = prm + timedelta(days=int(rng.integers(-2, 8))); q = int(rng.integers(500, 3000)); rej = int(q * rng.uniform(0, .06))
        pos.append(dict(PO_ID=f"MPO{i:05d}", Order_Date=od.isoformat(), Supplier_ID=f"SUP{(i % 4) + 1:02d}", Material_ID=f"M00{(i % 3) + 1}", Material_Name="x", Unit="meter", Ordered_Qty=q, Unit_Cost_EGP=round(float(rng.uniform(20, 40)), 2),
                        Promised_Date=prm.isoformat(), Actual_Receipt_Date=act.isoformat(), Accepted_Qty=q - rej, Rejected_Qty=rej, Data_Class="Synthetic"))
    prod, prt, qc, mk, dt, cs = [], [], [], [], [], []
    for i in range(1, 401):
        p = pm.Product_ID.iloc[i % n_products]; sd = date(2024, 1, 1) + timedelta(days=int(rng.integers(0, 1000))); planned = int(rng.integers(500, 2000)); produced = int(planned * rng.uniform(.9, 1)); rj = int(produced * rng.uniform(0, .05))
        delay = int(rng.choice([0, 0, 0, 2, 5]))
        prod.append(dict(Production_Order_ID=f"PO{i:05d}", Product_ID=p, Product_Name="x", Start_Date=sd.isoformat(), Due_Date=(sd + timedelta(days=10)).isoformat(), Completion_Date=(sd + timedelta(days=10 + delay)).isoformat(),
                         Planned_Qty=planned, Produced_Qty=produced, Good_Qty=produced - rj, Rejected_Qty=rj, Line_ID=f"LINE-0{i % 3 + 1}", Efficiency_Pct=round(float(rng.uniform(70, 95)), 1), Delay_Days=delay,
                         Primary_Bottleneck=str(rng.choice(["None", "Sewing", "Printing", "Cutting"])), Overtime_Hours=round(float(rng.uniform(0, 8)), 1), Data_Class="Synthetic"))
        d2 = date(2024, 1, 1) + timedelta(days=int(rng.integers(0, 1000))); pr_q = int(rng.integers(500, 2000)); pr_r = int(pr_q * rng.uniform(0, .05))
        prt.append(dict(Print_Batch_ID=f"PR{i:05d}", Product_ID=p, Product_Name="x", Print_Date=d2.isoformat(), Print_Type="Digital", Machine_ID=f"PR-M0{i % 3 + 1}", Planned_Qty=pr_q, Printed_Qty=pr_q, Good_Qty=pr_q - pr_r,
                        Rejected_Qty=pr_r, Reprint_Qty=int(pr_r / 2), Defect_Type=str(rng.choice(["None", "Ink Smudge", "Color Misalignment"])), Ink_or_Consumable_Cost_EGP=1000.0, Rework_Cost_EGP=float(pr_r * 5), Data_Class="Synthetic"))
    for i in range(1, 1201):
        d3 = date(2024, 1, 1) + timedelta(days=int(rng.integers(0, 1000))); ins = int(rng.integers(20, 80)); rj = int(rng.integers(0, 4))
        qc.append(dict(QC_ID=f"QC{i:06d}", Inspection_Date=d3.isoformat(), Product_ID=pm.Product_ID.iloc[i % n_products], Product_Name="x", Stage=str(rng.choice(["Sewing", "Printing", "Final"])), Inspected_Qty=ins,
                       Passed_Qty=ins - rj, Rejected_Qty=rj, Defect_Type="None" if rj == 0 else str(rng.choice(["Stitch Defect", "Print Cracking"])), Root_Cause="No significant issue" if rj == 0 else "Operator method",
                       Estimated_Loss_EGP=float(rj * 120), Data_Class="Synthetic"))
    for i in range(1, 121):
        s0 = date(2024, 1, 1) + timedelta(days=int(rng.integers(0, 1000))); imp = int(rng.integers(50000, 90000)); clk = int(imp * .02)
        mk.append(dict(Campaign_ID=f"CMP{i:04d}", Campaign_Name=f"Campaign {i}", Product_ID=pm.Product_ID.iloc[i % n_products], Product_Name="x", Platform=str(rng.choice(["Meta", "Google", "TikTok"])), Start_Date=s0.isoformat(),
                       End_Date=(s0 + timedelta(days=14)).isoformat(), Spend_EGP=float(rng.integers(5000, 30000)), Impressions=imp, Clicks=clk, Landing_Page_Sessions=clk, Orders_Attributed=int(clk * .03),
                       Attributed_Revenue_EGP=float(rng.integers(20000, 90000)), Discount_Pct=.1, Data_Class="Synthetic"))
    mk.append(dict(Campaign_ID="CMP9999", Campaign_Name="Live campaign", Product_ID="P001", Product_Name="x", Platform="Meta", Start_Date=(end - timedelta(days=10)).isoformat(), End_Date=(end + timedelta(days=5)).isoformat(),
                   Spend_EGP=20000.0, Impressions=90000, Clicks=2000, Landing_Page_Sessions=2000, Orders_Attributed=60, Attributed_Revenue_EGP=60000.0, Discount_Pct=.1, Data_Class="Synthetic"))
    for i in range(1, 301):
        dt.append(dict(Downtime_ID=f"DT{i:05d}", Date=(date(2024, 1, 1) + timedelta(days=int(rng.integers(0, 1000)))).isoformat(), Machine_ID=str(rng.choice(["PR-M01", "PR-M02", "PR-M03", "SEW-L01", "CUT-01"])),
                       Business_Area="Printing", Downtime_Hours=round(float(rng.uniform(.5, 6)), 1), Reason="Breakdown", Planned=str(rng.choice(["Yes", "No"])), Data_Class="Synthetic"))
    for i in range(1, 901):
        cs.append(dict(Ticket_ID=f"TKT{i:05d}", Open_Date=(date(2024, 1, 1) + timedelta(days=int(rng.integers(0, 1000)))).isoformat(), Channel="WhatsApp", Issue_Type=str(rng.choice(["Return request", "Delivery", "Quality complaint"])),
                       First_Response_Minutes=10.0, Resolution_Hours=5.0, Resolved="Yes", CSAT_1_to_5=float(rng.integers(1, 6)), Data_Class="Synthetic"))
    web = pd.DataFrame([dict(Date=(date(2024, 1, 1) + timedelta(days=i)).isoformat(), Sessions=1000, Users=800, New_User_Pct=.5, Mobile_Pct=.7, Add_To_Cart_Rate=.1, Checkout_Rate=.05, Orders=30, Conversion_Rate=.03, Avg_Page_Load_Sec=3.0, Data_Class="Synthetic") for i in range(900)])
    ops = pd.DataFrame([dict(Month=ms.date().isoformat(), Business_Unit="LEO DESIGN", Primary_KPI="Designs_Completed", Volume=40, Operational_Efficiency_Pct=85, Open_Issues_Count=2, Data_Class="Synthetic") for ms in month_starts])
    bu = pd.DataFrame([dict(Business_Unit="LEO DESIGN", Function="Design", Public_Capacity="n/a", Source_URL="-", Verification_Class="Synthetic")])
    brief = pd.DataFrame([dict(Card_No="01", Title="Exec", Business_Problem="x", Expected_Deliverable="y")])
    dd = pd.DataFrame([dict(Table="Product_Master.csv", Grain="product", Purpose="master", Real_vs_Modeled="Synthetic")])
    data = {"Locations.csv": loc, "Business_Units.csv": bu, "Product_Master.csv": pm, "Customers.csv": cust, "Suppliers.csv": sup, "Materials.csv": mat, "Sales_Transactions.csv": pd.DataFrame(sales),
            "Inventory_History.csv": pd.DataFrame(inv_rows), "Marketing.csv": pd.DataFrame(mk), "Web_Traffic_Daily.csv": web, "Product_BOM.csv": bom, "Purchase_Orders.csv": pd.DataFrame(pos),
            "Production_Orders.csv": pd.DataFrame(prod), "Printing_Batches.csv": pd.DataFrame(prt), "Machine_Downtime.csv": pd.DataFrame(dt), "Quality.csv": pd.DataFrame(qc), "Customer_Service.csv": pd.DataFrame(cs),
            "Group_Operations.csv": ops, "Case_Briefs.csv": brief, "Data_Dictionary.csv": dd}
    for f, df in data.items():
        df[list(FILES[f].cols)].to_csv(os.path.join(out_dir, f), index=False, encoding="utf-8-sig")
    return {f: len(d) for f, d in data.items()}
