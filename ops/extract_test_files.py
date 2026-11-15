"""Extract all fresh test files into an easily accessible directory
d:/New folder/PLR/TEST_FILES_TO_UPLOAD with detailed guidance.
"""
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST_DIR = ROOT / "TEST_FILES_TO_UPLOAD"
SAMPLE_DIR = ROOT / "docs" / "sample_data"
SCENARIOS_DIR = SAMPLE_DIR / "scenarios"

def extract():
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    
    # 1. Standard Fresh Dataset (up to 14 Nov 2026)
    std_dir = DEST_DIR / "1_STANDARD_RETAIL_DATA"
    std_dir.mkdir(parents=True, exist_ok=True)

    files_map = {
        "Customers.csv": "Customers.csv",
        "Locations.csv": "Locations.csv",
        "Product-Master.csv": "Product-Master.csv",
        "Inventory-History.csv": "Inventory-History.csv",
        "returns_data.csv": "returns_data.csv",
        "Sales-Transactions-Sample.csv": "Sales-Transactions-Sample.csv",
        "Sales-Transactions.csv": "Sales-Transactions-Full.csv"
    }

    for src_name, dst_name in files_map.items():
        src_path = SAMPLE_DIR / src_name
        if src_path.exists():
            shutil.copy2(src_path, std_dir / dst_name)
            print(f"Copied {src_name} -> {dst_name}")

    # Copy ZIP
    if (SAMPLE_DIR / "BusinessGate_Updated_Retail_Samples.zip").exists():
        shutil.copy2(SAMPLE_DIR / "BusinessGate_Updated_Retail_Samples.zip", DEST_DIR / "BusinessGate_Updated_Retail_Samples.zip")

    # 2. Place 1: Superstore Hub (Spoilage & Overstock)
    p1_dir = DEST_DIR / "2_PLACE_1_SUPERSTORE_SPOILAGE"
    p1_dir.mkdir(parents=True, exist_ok=True)
    s1_src = SCENARIOS_DIR / "scenario1_superstore_spoilage"
    if s1_src.exists():
        for f in s1_src.glob("*.csv"):
            shutil.copy2(f, p1_dir / f.name)
        print("Copied Place 1 files")

    # 3. Place 2: Express Downtown (Stockouts & Lost Sales)
    p2_dir = DEST_DIR / "3_PLACE_2_EXPRESS_STOCKOUTS"
    p2_dir.mkdir(parents=True, exist_ok=True)
    s2_src = SCENARIOS_DIR / "scenario2_express_stockouts"
    if s2_src.exists():
        for f in s2_src.glob("*.csv"):
            shutil.copy2(f, p2_dir / f.name)
        print("Copied Place 2 files")

    # 4. Place 3: Online & Wholesale (Discounts & Shipping Returns)
    p3_dir = DEST_DIR / "4_PLACE_3_ONLINE_WHOLESALE"
    p3_dir.mkdir(parents=True, exist_ok=True)
    s3_src = SCENARIOS_DIR / "scenario3_online_wholesale"
    if s3_src.exists():
        for f in s3_src.glob("*.csv"):
            shutil.copy2(f, p3_dir / f.name)
        print("Copied Place 3 files")

    # 5. Write Quick Readme Guide
    readme_content = """========================================================================
BUSINESS GATE - رادار تسرّب الأرباح
دليل ملفات الاختبار وطريقة الرفع التجريبي (Testing Files & Instructions)
========================================================================

📁 الملفات المستخرجة في هذا المجلد:

1_STANDARD_RETAIL_DATA:
------------------------------------------------------------------------
الحزمة القياسية المحدثة لكامل شبكة المتجر حتى تاريخ 14 نوفمبر 2026:
- Customers.csv: بيانات 5 عملاء (تجزئة، جملة، VIP، أونلاين، شركات).
- Locations.csv: بيانات 6 فروع ومراكز توزيع.
- Product-Master.csv: بيانات 80 صنفًا رئيسيًا مع الباركود وتكلفة الشراء وسعر البيع.
- Inventory-History.csv: رصيد المخزون الفعلي (ON_HAND) وسجلات الهدر (WASTE) حتى 14 نوفمبر 2026.
- returns_data.csv: جدول المرتجعات وعيوب الجودة متضمنًا الأسبوع الأخير.
- Sales-Transactions-Sample.csv: عينة 24 ألف فاتورة سريعة وخفيفة للمتصفح.
- Sales-Transactions-Full.csv: سجل الفواتير الشامل (294 ألف فاتورة).

2_PLACE_1_SUPERSTORE_SPOILAGE (المكان 1: هايبرماركت الدوحة الكبرى):
------------------------------------------------------------------------
- الخلل المستهدف: تلف أطعمة مبردة (لحوم وألبان) وركود 68 صنفًا لأكثر من 180 يومًا.
- النتيجة المالية: ربح مهدد 14.85 مليون ج.م · أرباح مستردة 5.42 مليون ج.م.
- القرارات: تصفية عاجلة بخصم تدريجي + غرامات المورد Al Meera + خفض Safety Stock 40%.

3_PLACE_2_EXPRESS_STOCKOUTS (المكان 2: فرع وسط البلد السريع):
------------------------------------------------------------------------
- الخلل المستهدف: نفاد مخزون 58 صنفًا بطلًا ومبيعات ضائعة بسبب الرفوف الفارغة.
- النتيجة المالية: ربح مهدد 9.64 مليون ج.م · أرباح مستردة 4.18 مليون ج.م.
- القرارات: نقل مخزون فوري (Stock Transfer) من المستودع + مضاعفة Reorder Point.

4_PLACE_3_ONLINE_WHOLESALE (المكان 3: مستودع الجملة وقناة الأونلاين):
------------------------------------------------------------------------
- الخلل المستهدف: تآكل الهامش بسبب كوبونات خصم 20% ومرتجعات الشحن والتوصيل.
- النتيجة المالية: ربح مهدد 18.22 مليون ج.م · أرباح مستردة 6.85 مليون ج.م.
- القرارات: إلغاء الخصم على السلع منخفضة الهامش + شرط حد أدنى 300 ج للشحن المجاني.

========================================================================
طريقة التجربة في المتصفح:
1. افتح صفحة النظام (أونلاين: https://emadabutaleb0-afk.github.io/PLR/)
2. النظام يبدأ فارغًا تمامًا (Empty State: No Data).
3. اذهب إلى التبويب السادس (📂 رفع البيانات وصحة الجداول).
4. اسحب أي ملف من الملفات أعلاه وأفلته في المربع واضغط [⚡ بدء معالجة الملفات].
5. فور اكتمال المعالجة ستتحول لوحة التحكم كاملة إلى الحالة النشطة (Fresh & Healthy)!
========================================================================
"""
    with open(DEST_DIR / "README_TEST_GUIDE.txt", "w", encoding="utf-8") as f:
        f.write(readme_content)
    print("Saved README_TEST_GUIDE.txt")
    print(f"-> Extraction complete into: {DEST_DIR}")

if __name__ == "__main__":
    extract()
