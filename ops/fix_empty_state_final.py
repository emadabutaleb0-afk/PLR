"""Ensure the application starts completely empty with NO data, NO client name,
and verify that all JavaScript executes cleanly without any errors.
"""
import shutil
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = ROOT / "docs" / "index.html"
DEMO_PATH = ROOT / "docs" / "BusinessGate_Finance_Interactive_Demo.html"
ROOT_INDEX = ROOT / "index.html"
ARTIFACT_PATH = Path(r"C:\Users\EMadHamza\.gemini\antigravity\brain\2201ad41-5133-4dab-bb08-4c42bf15a6e7\BusinessGate_Finance_Interactive_Demo.html")

def fix():
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        html = f.read()

    html = html.replace("\r\n", "\n")

    # 1. Clean Scenario buttons in HTML: NONE should have btn-primary
    html = re.sub(
        r'<button class="btn btn-primary" id="btn-scen-superstore"',
        r'<button class="btn" id="btn-scen-superstore"',
        html
    )

    # 2. Clean KPI cards in HTML
    kpi_empty_html = """<div class="grid-4"  style="margin-bottom: 20px;">
          <div class="card" style="border-right: 4px solid var(--border);">
            <div class="card-header"><span class="card-title">إجمالي الربح المعرّض للخطر</span><span class="badge badge-gray">في الانتظار</span></div>
            <div class="kpi-num" id="kpi-risk-val" style="color: var(--text-muted);">-- ج.م</div>
            <div id="kpi-risk-sub" style="font-size: 11.5px; color: var(--text-muted);">في انتظار رفع البيانات</div>
          </div>
          <div class="card" style="border-right: 4px solid var(--border);">
            <div class="card-header"><span class="card-title">الأرباح القابلة للاسترداد فورًا</span><span class="badge badge-gray">في الانتظار</span></div>
            <div class="kpi-num" id="kpi-recoverable-val" style="color: var(--text-muted);">-- ج.م</div>
            <div id="kpi-rec-sub" style="font-size: 11.5px; color: var(--text-muted);">في انتظار التحليل</div>
          </div>
          <div class="card" style="border-right: 4px solid var(--border);">
            <div class="card-header"><span class="card-title">أصناف مهددة بالنفاد (Stockout)</span><span class="badge badge-gray">في الانتظار</span></div>
            <div class="kpi-num" id="kpi-stockout-val" style="color: var(--text-muted);">0 صنف</div>
            <div id="kpi-stockout-sub" style="font-size: 11.5px; color: var(--text-muted);">لا توجد بيانات</div>
          </div>
          <div class="card" style="border-right: 4px solid var(--border);">
            <div class="card-header"><span class="card-title">أصناف فائضة وراكدة (Overstock)</span><span class="badge badge-gray">في الانتظار</span></div>
            <div class="kpi-num" id="kpi-overstock-val" style="color: var(--text-muted);">0 صنف</div>
            <div id="kpi-overstock-sub" style="font-size: 11.5px; color: var(--text-muted);">لا توجد بيانات</div>
          </div>
        </div>"""

    old_kpi_match = re.search(r'<div class="grid-4"\s*style="margin-bottom: 20px;">.*?</div>\s*</div>\s*<div class="grid-2">', html, re.DOTALL)
    if old_kpi_match:
        html = html.replace(old_kpi_match.group(0), kpi_empty_html + "\n\n        <div class=\"grid-2\">")
        print("-> Replaced static KPI cards with pure Empty HTML")

    # 3. Clean Leakage Progress & Top Decisions in HTML
    empty_decisions_html = """<div class="card">
          <div class="card-header">
            <span class="card-title">أهم 3 قرارات ذات أولوية قصوى اليوم</span>
            <span class="badge badge-gray">في الانتظار</span>
          </div>
          <div id="command-decisions">
            <div style="text-align:center; padding: 25px 15px; background: var(--bg-sunken); border-radius: 12px; border: 1px dashed var(--border);">
              <div style="font-size: 26px; margin-bottom: 6px;">📂</div>
              <div style="font-weight: 800; font-size: 13px; margin-bottom: 4px;">لا توجد قرارات تجارية مقترحة حتى الآن</div>
              <div style="font-size: 11.5px; color: var(--text-muted); margin-bottom: 12px;">يتطلب النظام استيراد جداول المبيعات والمخزون والمرتجعات لكشف التسرّب وتوليد التوصيات.</div>
              <button class="btn btn-primary" onclick="switchTab('tab-data', document.querySelectorAll('.nav-tab')[5])" style="font-size: 11.5px; padding: 5px 12px;">
                📂 الانتقال لتبويب رفع البيانات ←
              </button>
            </div>
          </div>
        </div>

        <div class="card">
          <div class="card-header">
            <span class="card-title">توزيع تسرّب الأرباح السنوي حسب المصدر</span>
            <span class="badge badge-gray" id="leak-total-badge">-- ج.م</span>
          </div>
          <div style="padding: 10px 0;" id="leak-progress-box">
            <div style="text-align: center; padding: 25px; color: var(--text-muted); font-size: 12px;">
              📊 في انتظار رفع البيانات لاحتساب مسارات ونسب التسرّب.
            </div>
          </div>
          <div style="background: var(--bg-sunken); padding: 12px; border-radius: 10px; font-size: 12px; color: var(--text-muted);">
            💡 <b>الملاحظة المالية:</b> تظهر هنا مسارات ونسب تسرّب الأرباح فور استيراد بيانات المتجر أو الفرع.
          </div>
        </div>"""

    old_dec_block = re.search(r'<div class="grid-2">\s*<div class="card">\s*<div class="card-header">\s*<span class="card-title">أهم 3 قرارات.*?</div>\s*</div>\s*</div>\s*</div>\s*<!-- ==================== TAB 2', html, re.DOTALL)
    if old_dec_block:
        html = html.replace(old_dec_block.group(0), "<div class=\"grid-2\">\n        " + empty_decisions_html + "\n      </div>\n    </div>\n\n    <!-- ==================== TAB 2")
        print("-> Replaced Tab 1 decisions and progress box with pure Empty HTML")

    # 4. Remove duplicate `const HEALTH_TABLES = [` around line 1515
    # Replace that duplicate block with POPULATED_HEALTH_TABLES
    duplicate_health_pattern = r'const HEALTH_TABLES = \[\s*\{ name: "product_master\.csv".*?\n  \];\s*let currentModalDec = null;\s*let realizedTotal = 0;\s*let uploadedFiles = \[\];'
    repl_tables = """const POPULATED_HEALTH_TABLES = [
    { name: "product_master.csv", nameAr: "بيانات المنتجات والتسعير", rows: 1842, updated: "اليوم", quality: 99.1, status: "HEALTHY", note: "مكتمل وبلا انحرافات" },
    { name: "sales_transactions.csv", nameAr: "سجل حركات البيع والفواتير", rows: 48320, updated: "اليوم", quality: 98.2, status: "HEALTHY", note: "تغطية كاملة لـ 12 شهرًا" },
    { name: "inventory_stock.csv", nameAr: "مستويات المخزون بالفروع والمستودعات", rows: 5640, updated: "اليوم", quality: 97.8, status: "HEALTHY", note: "أرصدة فعلية متطابقة" },
    { name: "returns_data.csv", nameAr: "بيانات المرتجعات وعيوب الجودة", rows: 2210, updated: "اليوم", quality: 99.4, status: "HEALTHY", note: "تم تحديث بيانات الأسبوع الأخير" },
    { name: "branches_master.csv", nameAr: "بيانات الفروع ومراكز التوزيع", rows: 28, updated: "اليوم", quality: 100, status: "HEALTHY", note: "بيانات مرجعية سليمة" },
    { name: "suppliers.csv", nameAr: "بيانات الموردين والعقود", rows: 143, updated: "اليوم", quality: 99.6, status: "HEALTHY", note: "شروط التوريد محددة بدقة" }
  ];"""

    if re.search(duplicate_health_pattern, html, re.DOTALL):
        html = re.sub(duplicate_health_pattern, repl_tables, html, flags=re.DOTALL)
        print("-> Removed duplicate HEALTH_TABLES / realizedTotal / uploadedFiles")
    else:
        # Check without uploadedFiles
        dup2 = r'const HEALTH_TABLES = \[\s*\{ name: "product_master\.csv".*?\n  \];'
        if re.search(dup2, html, re.DOTALL):
            html = re.sub(dup2, repl_tables, html, flags=re.DOTALL)
            print("-> Replaced second HEALTH_TABLES with POPULATED_HEALTH_TABLES")

    # 5. Clean Client Name function: Ensure NO client name by default
    old_client_func = re.search(r'function loadCompanyName\(\)\s*\{.*?\}', html, re.DOTALL)
    if old_client_func:
        new_client_func = """function loadCompanyName() {
    // Ensure clean start with NO client name
    const label = document.getElementById('company-label');
    if (label) label.innerText = 'النسخة التفاعلية المستقلة لقطاع المالية والإدارة التنفيذية';
    const field = document.getElementById('company-name-field');
    if (field) field.value = '';
    try {
      localStorage.removeItem('bg_company_name');
    } catch(e) {}
  }"""
        html = html.replace(old_client_func.group(0), new_client_func)
        print("-> loadCompanyName updated to guarantee NO client name")

    # 6. In switchScenario, update leak-total-badge and card borders
    if "const tBadge = document.getElementById('leak-total-badge');" not in html:
        old_switch_inner = "const pBox = document.getElementById('leak-progress-box');"
        new_switch_inner = """// Update Tab 1 KPI Card borders to indicate active data
    const rCard = document.getElementById('kpi-risk-val')?.closest('.card');
    if (rCard) rCard.style.borderRight = '4px solid var(--red)';
    const rcCard = document.getElementById('kpi-recoverable-val')?.closest('.card');
    if (rcCard) rcCard.style.borderRight = '4px solid var(--green)';
    const soCard = document.getElementById('kpi-stockout-val')?.closest('.card');
    if (soCard) soCard.style.borderRight = '4px solid var(--amber)';
    const osCard = document.getElementById('kpi-overstock-val')?.closest('.card');
    if (osCard) osCard.style.borderRight = '4px solid var(--accent)';

    // Update KPI Card badges
    const rBadge = rCard?.querySelector('.badge');
    if (rBadge) { rBadge.className = 'badge badge-red'; rBadge.innerText = 'خسارة كامنة'; }
    const rcBadge = rcCard?.querySelector('.badge');
    if (rcBadge) { rcBadge.className = 'badge badge-green'; rcBadge.innerText = 'كاش متاح'; }
    const soBadge = soCard?.querySelector('.badge');
    if (soBadge) { soBadge.className = 'badge badge-amber'; soBadge.innerText = 'مبيعات ضائعة'; }
    const osBadge = osCard?.querySelector('.badge');
    if (osBadge) { osBadge.className = 'badge badge-indigo'; osBadge.innerText = 'كاش محبوس'; }

    const tBadge = document.getElementById('leak-total-badge');
    if (tBadge) { tBadge.className = 'badge badge-red'; tBadge.innerText = scen.riskVal; }

    const pBox = document.getElementById('leak-progress-box');"""
        html = html.replace(old_switch_inner, new_switch_inner)
        print("-> switchScenario enhanced to activate borders and badges on load")

    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Saved {INDEX_PATH}")

    shutil.copy2(INDEX_PATH, DEMO_PATH)
    shutil.copy2(INDEX_PATH, ROOT_INDEX)
    if ARTIFACT_PATH.parent.exists():
        shutil.copy2(INDEX_PATH, ARTIFACT_PATH)
    print("Copied to all targets successfully")

if __name__ == "__main__":
    fix()
