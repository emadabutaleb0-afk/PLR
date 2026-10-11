"""Single source of truth for the 20 company CSV files.

Every file declares its table, primary key, typed columns, required columns,
real foreign keys (only relationships that exist in the data) and
business-rule checks used by the validator.
Type codes: s=string i=int f=float d=date yn=Yes/No boolean
"""
from dataclasses import dataclass, field
from typing import Callable
import pandas as pd


@dataclass
class Rule:
    name: str
    check: Callable[[pd.DataFrame], pd.Series]  # True where the row is BAD
    message: str
    severity: str = "reject"  # reject -> quarantine, warn -> load but record


@dataclass
class FileSpec:
    file: str
    table: str
    pk: list[str]
    cols: dict[str, str]
    required: list[str]
    fks: list[tuple[str, str, str]] = field(default_factory=list)  # (col, ref_table, ref_col)
    rules: list[Rule] = field(default_factory=list)
    date_col: str | None = None  # used for staleness
    index: list[str] = field(default_factory=list)


def _n(df, c):
    return pd.to_numeric(df[c], errors="coerce")


def neg(*cols):
    return Rule("negative_quantity", lambda df: pd.concat([(_n(df, c) < 0) for c in cols], axis=1).any(axis=1),
                f"negative value in {', '.join(cols)}")


def rng(col, lo, hi, sev="reject"):
    return Rule(f"{col}_out_of_range", lambda df: (_n(df, col) < lo) | (_n(df, col) > hi),
                f"{col} outside {lo}..{hi}", sev)


def date_order(a, b, sev="reject"):
    return Rule(f"{b}_before_{a}", lambda df: pd.to_datetime(df[b], errors="coerce") < pd.to_datetime(df[a], errors="coerce"),
                f"{b} is earlier than {a}", sev)


def sum_eq(parts, total, tol=0):
    return Rule(f"{total}_mismatch", lambda df: (sum(_n(df, p) for p in parts) - _n(df, total)).abs() > tol,
                f"{' + '.join(parts)} does not equal {total}")


FILES: dict[str, FileSpec] = {}


def reg(s: FileSpec):
    FILES[s.file] = s


reg(FileSpec("Locations.csv", "locations", ["Location_ID"],
             dict(Location_ID="s", Location_Name="s", Location_Type="s", Channel="s", Governorate="s", City="s",
                  Public_Address="s", Source_URL="s", Verification_Class="s"),
             ["Location_ID", "Location_Name"]))
reg(FileSpec("Business_Units.csv", "business_units", ["Business_Unit"],
             dict(Business_Unit="s", Function="s", Public_Capacity="s", Source_URL="s", Verification_Class="s"),
             ["Business_Unit"]))
reg(FileSpec("Product_Master.csv", "product_master", ["Product_ID"],
             dict(Product_ID="s", SKU="s", Product_Name="s", Brand="s", Product_Family="s", Gender="s", Audience="s",
                  Catalog_Season="s", Sizes="s", Public_Retail_Price_EGP="f", Public_Catalog_Source="s",
                  Verification_Class="s"),
             ["Product_ID", "SKU", "Product_Name", "Public_Retail_Price_EGP"],
             rules=[Rule("price_not_positive", lambda df: _n(df, "Public_Retail_Price_EGP") <= 0, "retail price must be > 0")]))
reg(FileSpec("Customers.csv", "customers", ["Customer_ID"],
             dict(Customer_ID="s", Customer_Type="s", Governorate="s", Age_Band="s", Gender="s", Join_Date="d",
                  Acquisition_Channel="s", Consent_Status="s", Data_Class="s"),
             ["Customer_ID"], date_col="Join_Date"))
reg(FileSpec("Suppliers.csv", "suppliers", ["Supplier_ID"],
             dict(Supplier_ID="s", Supplier_Name="s", Primary_Category="s", Governorate="s", Payment_Terms_Days="i",
                  Contracted="yn", Data_Class="s"),
             ["Supplier_ID", "Supplier_Name"], rules=[neg("Payment_Terms_Days")]))
reg(FileSpec("Materials.csv", "materials", ["Material_ID"],
             dict(Material_ID="s", Material_Name="s", Unit="s", Material_Category="s", Standard_Lead_Time_Days="i",
                  Data_Class="s"),
             ["Material_ID", "Material_Name"], rules=[neg("Standard_Lead_Time_Days")]))
reg(FileSpec("Sales_Transactions.csv", "sales_transactions", ["Row_ID"],
             dict(Row_ID="i", Invoice_ID="s", Order_Date="d", Month_Key="s", Location_ID="s", Location_Name="s",
                  Channel="s", Customer_ID="s", Customer_Type="s", Customer_Governorate="s", Product_ID="s", SKU="s",
                  Product_Name="s", Product_Family="s", Size="s", Quantity="i", List_Price_EGP="f", Discount_Pct="f",
                  Gross_Sales_EGP="f", Net_Sales_EGP="f", Estimated_COGS_EGP="f", Gross_Profit_EGP="f",
                  Gross_Margin_Pct="f", Payment_Method="s", Returned="yn", Return_Date="d", Return_Reason="s",
                  Refund_Value_EGP="f", Quality_Related_Return="yn", Data_Class="s"),
             ["Row_ID", "Invoice_ID", "Order_Date", "Location_ID", "Customer_ID", "Product_ID", "Quantity",
              "Net_Sales_EGP"],
             fks=[("Product_ID", "product_master", "Product_ID"), ("Customer_ID", "customers", "Customer_ID"),
                  ("Location_ID", "locations", "Location_ID")],
             rules=[Rule("quantity_not_positive", lambda df: _n(df, "Quantity") <= 0, "Quantity must be > 0"),
                    neg("Net_Sales_EGP", "Gross_Sales_EGP", "Estimated_COGS_EGP", "Refund_Value_EGP"),
                    rng("Discount_Pct", 0, 1), date_order("Order_Date", "Return_Date"),
                    Rule("profit_mismatch", lambda df: (_n(df, "Net_Sales_EGP") - _n(df, "Estimated_COGS_EGP") - _n(df, "Gross_Profit_EGP")).abs() > 1,
                         "Gross_Profit differs from Net_Sales - COGS", "warn")],
             date_col="Order_Date", index=["Order_Date", "Month_Key", "Product_ID", "Location_ID", "Customer_ID"]))
reg(FileSpec("Inventory_History.csv", "inventory_history", ["Snapshot_Month", "Location_ID", "Product_ID"],
             dict(Snapshot_Month="d", Location_ID="s", Location_Name="s", Product_ID="s", SKU="s", Product_Name="s",
                  Opening_Stock="i", Received_Qty="i", Sold_Qty="i", Returned_Qty="i", Damaged_Qty="i",
                  Closing_Stock="i", Avg_Daily_Sales_90D="f", Safety_Stock_Units="i", Reorder_Point_Units="i",
                  Supplier_Lead_Time_Days="i", Days_of_Cover="f", Stockout_Days_In_Month="i", Data_Class="s"),
             ["Snapshot_Month", "Location_ID", "Product_ID", "Closing_Stock"],
             fks=[("Product_ID", "product_master", "Product_ID"), ("Location_ID", "locations", "Location_ID")],
             rules=[neg("Opening_Stock", "Received_Qty", "Sold_Qty", "Returned_Qty", "Damaged_Qty", "Closing_Stock",
                        "Days_of_Cover", "Avg_Daily_Sales_90D"), rng("Stockout_Days_In_Month", 0, 31),
                    Rule("stock_roll_forward", lambda df: (_n(df, "Opening_Stock") + _n(df, "Received_Qty") - _n(df, "Sold_Qty")
                                                           + _n(df, "Returned_Qty") - _n(df, "Damaged_Qty") != _n(df, "Closing_Stock"))
                         & (_n(df, "Closing_Stock") != 0),
                         "Closing_Stock does not reconcile with movements (and is not a zero-floored stockout)", "warn")],
             date_col="Snapshot_Month", index=["Product_ID", "Location_ID", "Snapshot_Month"]))
reg(FileSpec("Marketing.csv", "marketing", ["Campaign_ID"],
             dict(Campaign_ID="s", Campaign_Name="s", Product_ID="s", Product_Name="s", Platform="s", Start_Date="d",
                  End_Date="d", Spend_EGP="f", Impressions="i", Clicks="i", Landing_Page_Sessions="i",
                  Orders_Attributed="i", Attributed_Revenue_EGP="f", Discount_Pct="f", Data_Class="s"),
             ["Campaign_ID", "Product_ID", "Start_Date", "End_Date", "Spend_EGP"],
             fks=[("Product_ID", "product_master", "Product_ID")],
             rules=[neg("Spend_EGP", "Impressions", "Clicks", "Orders_Attributed", "Attributed_Revenue_EGP"),
                    date_order("Start_Date", "End_Date"),
                    Rule("clicks_gt_impressions", lambda df: _n(df, "Clicks") > _n(df, "Impressions"), "Clicks exceed Impressions"),
                    Rule("orders_gt_clicks", lambda df: _n(df, "Orders_Attributed") > _n(df, "Clicks"), "Orders exceed Clicks", "warn")],
             date_col="End_Date", index=["Product_ID", "Start_Date"]))
reg(FileSpec("Web_Traffic_Daily.csv", "web_traffic_daily", ["Date"],
             dict(Date="d", Sessions="i", Users="i", New_User_Pct="f", Mobile_Pct="f", Add_To_Cart_Rate="f",
                  Checkout_Rate="f", Orders="i", Conversion_Rate="f", Avg_Page_Load_Sec="f", Data_Class="s"),
             ["Date", "Sessions"], rules=[neg("Sessions", "Users", "Orders"), rng("Conversion_Rate", 0, 1)],
             date_col="Date"))
reg(FileSpec("Product_BOM.csv", "product_bom", ["Product_ID", "Material_ID"],
             dict(Product_ID="s", Product_Name="s", Material_ID="s", Material_Name="s", Required_Per_Unit="f",
                  Unit="s", Data_Class="s"),
             ["Product_ID", "Material_ID", "Required_Per_Unit"],
             fks=[("Product_ID", "product_master", "Product_ID"), ("Material_ID", "materials", "Material_ID")],
             rules=[Rule("bom_not_positive", lambda df: _n(df, "Required_Per_Unit") <= 0, "Required_Per_Unit must be > 0")]))
reg(FileSpec("Purchase_Orders.csv", "purchase_orders", ["PO_ID"],
             dict(PO_ID="s", Order_Date="d", Supplier_ID="s", Material_ID="s", Material_Name="s", Unit="s",
                  Ordered_Qty="f", Unit_Cost_EGP="f", Promised_Date="d", Actual_Receipt_Date="d", Accepted_Qty="f",
                  Rejected_Qty="f", Data_Class="s"),
             ["PO_ID", "Order_Date", "Supplier_ID", "Material_ID", "Ordered_Qty", "Unit_Cost_EGP"],
             fks=[("Supplier_ID", "suppliers", "Supplier_ID"), ("Material_ID", "materials", "Material_ID")],
             rules=[neg("Ordered_Qty", "Accepted_Qty", "Rejected_Qty"),
                    Rule("cost_not_positive", lambda df: _n(df, "Unit_Cost_EGP") <= 0, "Unit_Cost_EGP must be > 0"),
                    date_order("Order_Date", "Promised_Date"), date_order("Order_Date", "Actual_Receipt_Date"),
                    sum_eq(["Accepted_Qty", "Rejected_Qty"], "Ordered_Qty", 0.5)],
             date_col="Order_Date", index=["Supplier_ID", "Material_ID", "Order_Date"]))
reg(FileSpec("Production_Orders.csv", "production_orders", ["Production_Order_ID"],
             dict(Production_Order_ID="s", Product_ID="s", Product_Name="s", Start_Date="d", Due_Date="d",
                  Completion_Date="d", Planned_Qty="i", Produced_Qty="i", Good_Qty="i", Rejected_Qty="i", Line_ID="s",
                  Efficiency_Pct="f", Delay_Days="i", Primary_Bottleneck="s", Overtime_Hours="f", Data_Class="s"),
             ["Production_Order_ID", "Product_ID", "Start_Date", "Planned_Qty", "Produced_Qty"],
             fks=[("Product_ID", "product_master", "Product_ID")],
             rules=[neg("Planned_Qty", "Produced_Qty", "Good_Qty", "Rejected_Qty", "Delay_Days", "Overtime_Hours"),
                    date_order("Start_Date", "Completion_Date"), rng("Efficiency_Pct", 0, 200),
                    sum_eq(["Good_Qty", "Rejected_Qty"], "Produced_Qty")],
             date_col="Completion_Date", index=["Product_ID", "Start_Date", "Line_ID"]))
reg(FileSpec("Printing_Batches.csv", "printing_batches", ["Print_Batch_ID"],
             dict(Print_Batch_ID="s", Product_ID="s", Product_Name="s", Print_Date="d", Print_Type="s", Machine_ID="s",
                  Planned_Qty="i", Printed_Qty="i", Good_Qty="i", Rejected_Qty="i", Reprint_Qty="i", Defect_Type="s",
                  Ink_or_Consumable_Cost_EGP="f", Rework_Cost_EGP="f", Data_Class="s"),
             ["Print_Batch_ID", "Product_ID", "Print_Date", "Machine_ID"],
             fks=[("Product_ID", "product_master", "Product_ID")],
             rules=[neg("Planned_Qty", "Printed_Qty", "Good_Qty", "Rejected_Qty", "Reprint_Qty",
                        "Ink_or_Consumable_Cost_EGP", "Rework_Cost_EGP"),
                    sum_eq(["Good_Qty", "Rejected_Qty"], "Printed_Qty")],
             date_col="Print_Date", index=["Product_ID", "Print_Date", "Machine_ID"]))
reg(FileSpec("Machine_Downtime.csv", "machine_downtime", ["Downtime_ID"],
             dict(Downtime_ID="s", Date="d", Machine_ID="s", Business_Area="s", Downtime_Hours="f", Reason="s",
                  Planned="yn", Data_Class="s"),
             ["Downtime_ID", "Date", "Machine_ID", "Downtime_Hours"],
             rules=[Rule("downtime_not_positive", lambda df: _n(df, "Downtime_Hours") <= 0, "Downtime_Hours must be > 0"),
                    rng("Downtime_Hours", 0, 744)],
             date_col="Date", index=["Machine_ID", "Date"]))
reg(FileSpec("Quality.csv", "quality", ["QC_ID"],
             dict(QC_ID="s", Inspection_Date="d", Product_ID="s", Product_Name="s", Stage="s", Inspected_Qty="i",
                  Passed_Qty="i", Rejected_Qty="i", Defect_Type="s", Root_Cause="s", Estimated_Loss_EGP="f",
                  Data_Class="s"),
             ["QC_ID", "Inspection_Date", "Product_ID", "Inspected_Qty"],
             fks=[("Product_ID", "product_master", "Product_ID")],
             rules=[neg("Inspected_Qty", "Passed_Qty", "Rejected_Qty", "Estimated_Loss_EGP"),
                    Rule("inspected_not_positive", lambda df: _n(df, "Inspected_Qty") <= 0, "Inspected_Qty must be > 0"),
                    sum_eq(["Passed_Qty", "Rejected_Qty"], "Inspected_Qty")],
             date_col="Inspection_Date", index=["Product_ID", "Inspection_Date"]))
reg(FileSpec("Customer_Service.csv", "customer_service", ["Ticket_ID"],
             dict(Ticket_ID="s", Open_Date="d", Channel="s", Issue_Type="s", First_Response_Minutes="f",
                  Resolution_Hours="f", Resolved="yn", CSAT_1_to_5="f", Data_Class="s"),
             ["Ticket_ID", "Open_Date"], rules=[neg("First_Response_Minutes", "Resolution_Hours"), rng("CSAT_1_to_5", 1, 5)],
             date_col="Open_Date", index=["Open_Date"]))
reg(FileSpec("Group_Operations.csv", "group_operations", ["Month", "Business_Unit"],
             dict(Month="d", Business_Unit="s", Primary_KPI="s", Volume="f", Operational_Efficiency_Pct="f",
                  Open_Issues_Count="i", Data_Class="s"),
             ["Month", "Business_Unit"], rules=[neg("Volume", "Open_Issues_Count"), rng("Operational_Efficiency_Pct", 0, 200)],
             date_col="Month"))
reg(FileSpec("Case_Briefs.csv", "case_briefs", ["Card_No"],
             dict(Card_No="s", Title="s", Business_Problem="s", Expected_Deliverable="s"), ["Card_No", "Title"]))
reg(FileSpec("Data_Dictionary.csv", "data_dictionary", ["Table"],
             dict(Table="s", Grain="s", Purpose="s", Real_vs_Modeled="s"), ["Table"]))

# load order respects real foreign keys
LOAD_ORDER = ["Locations.csv", "Business_Units.csv", "Product_Master.csv", "Customers.csv", "Suppliers.csv",
              "Materials.csv", "Sales_Transactions.csv", "Inventory_History.csv", "Marketing.csv",
              "Web_Traffic_Daily.csv", "Product_BOM.csv", "Purchase_Orders.csv", "Production_Orders.csv",
              "Printing_Batches.csv", "Machine_Downtime.csv", "Quality.csv", "Customer_Service.csv",
              "Group_Operations.csv", "Case_Briefs.csv", "Data_Dictionary.csv"]
assert set(LOAD_ORDER) == set(FILES)

# Documented soft (non-FK) links - validated as warnings, never enforced as DB constraints
SOFT_LINKS = [
    ("Printing_Batches.csv", "Machine_ID", "Machine_Downtime.csv", "Machine_ID",
     "Printing machine IDs should appear in Machine_Downtime (no machine master exists, so this cannot be a database FK)"),
]
