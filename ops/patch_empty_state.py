"""Update docs/index.html to start in an Empty State (No Data) by default,
allowing user to upload files or pick scenarios to populate and compute results.
"""
import shutil
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = ROOT / "docs" / "index.html"
DEMO_PATH = ROOT / "docs" / "BusinessGate_Finance_Interactive_Demo.html"
ROOT_INDEX = ROOT / "index.html"
ARTIFACT_PATH = Path(r"C:\Users\EMadHamza\.gemini\antigravity\brain\2201ad41-5133-4dab-bb08-4c42bf15a6e7\BusinessGate_Finance_Interactive_Demo.html")

def patch():
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        html = f.read()

    html = html.replace("\r\n", "\n")

    # 1. Update Header to add a "Reset to Empty State" button
    if "resetToEmptyState()" not in html:
        old_hdr_btns = """        <button class="btn" onclick="toggleTheme()" title="تبديل الوضع الليلي / النهاري">🌓 المظهر</button>
        <button class="btn btn-primary" onclick="window.print()">🖨️ طباعة تقرير</button>"""
        new_hdr_btns = """        <button class="btn" onclick="resetToEmptyState()" title="إعادة تعيين النظام لحالة البداية بدون بيانات">🗑️ حالة الصفر</button>
        <button class="btn" onclick="toggleTheme()" title="تبديل الوضع الليلي / النهاري">🌓 المظهر</button>
        <button class="btn btn-primary" onclick="window.print()">🖨️ طباعة تقرير</button>"""
        html = html.replace(old_hdr_btns, new_hdr_btns)
        print("-> Added Reset to Empty button in header")

    # 2. Update Freshness bar in HTML to have default Empty state text
    old_fresh_bar = re.search(r'<div class="freshness-bar">.*?</div>\s*<div class="grid-4"', html, re.DOTALL)
    if old_fresh_bar:
        new_fresh_bar = """<div class="freshness-bar" id="freshness-container" style="border-right: 4px solid var(--border);">
        <span style="font-size: 20px;" id="freshness-icon">📁</span>
        <div style="flex: 1;">
          <span style="font-weight: 800; font-size: 12.5px;">حالة تحديث البيانات:</span>
          <span id="freshness-text" style="font-size: 12px; margin-right: 6px; color: var(--text-muted);">لا توجد بيانات مرفوعة بعد · يُرجى رفع جداول البيانات لبدء فحص المؤشرات وكشف التسرّب.</span>
        </div>
        <span id="freshness-badge" class="badge badge-gray">NO_DATA · في انتظار الجداول</span>
        <span id="freshness-sub" style="font-size: 11px; color: var(--text-muted);">النظام في وضع البداية الفارغ</span>
      </div>\n\n      <div class="grid-4" """
        html = html.replace(old_fresh_bar.group(0), new_fresh_bar)
        print("-> Freshness Bar initialized to Empty state")

    # 3. Update Scenario Bar Banner to indicate Waiting for Upload
    old_scen_banner = re.search(r'<div id="scenario-summary-banner".*?</div>\s*</div>', html, re.DOTALL)
    if old_scen_banner:
        new_scen_banner = """<div id="scenario-summary-banner" style="margin-top: 10px; padding: 8px 12px; background: var(--bg-surface); border-radius: 8px; font-size: 12px; border: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 6px;">
        <span>📍 <b>المكان والفرع:</b> <span id="current-place-name" style="color: var(--text-muted); font-weight: 800;">لم يتم اختيار فرع بعد (في انتظار رفع البيانات)</span></span>
        <span>⚠️ <b>الخلل المالي المستهدف:</b> <span id="current-place-issue" style="color: var(--text-muted); font-weight: 700;">ارفع ملفات CSV من تبويب رفع البيانات أو اختر فرعًا أدناه</span></span>
      </div>\n    </div>"""
        html = html.replace(old_scen_banner.group(0), new_scen_banner)
        print("-> Scenario Bar Banner set to initial waiting state")

    # 4. Make INITIAL_EMPTY_STATE in JS
    empty_state_js = """
  // ==================== EMPTY STATE & DATA CONTROL ====================
  let isDataLoaded = false;

  const INITIAL_HEALTH_TABLES = [
    { name: "product_master.csv", nameAr: "بيانات المنتجات والتسعير", rows: 0, updated: "لم يُرفع بعد", quality: 0, status: "NOT_LOADED", note: "في انتظار رفع الملف" },
    { name: "sales_transactions.csv", nameAr: "سجل حركات البيع والفواتير", rows: 0, updated: "لم يُرفع بعد", quality: 0, status: "NOT_LOADED", note: "في انتظار رفع الملف" },
    { name: "inventory_stock.csv", nameAr: "مستويات المخزون بالفروع والمستودعات", rows: 0, updated: "لم يُرفع بعد", quality: 0, status: "NOT_LOADED", note: "في انتظار رفع الملف" },
    { name: "returns_data.csv", nameAr: "بيانات المرتجعات وعيوب الجودة", rows: 0, updated: "لم يُرفع بعد", quality: 0, status: "NOT_LOADED", note: "في انتظار رفع الملف" },
    { name: "branches_master.csv", nameAr: "بيانات الفروع ومراكز التوزيع", rows: 0, updated: "لم يُرفع بعد", quality: 0, status: "NOT_LOADED", note: "في انتظار رفع الملف" },
    { name: "suppliers.csv", nameAr: "بيانات الموردين والعقود", rows: 0, updated: "لم يُرفع بعد", quality: 0, status: "NOT_LOADED", note: "في انتظار رفع الملف" }
  ];

  let HEALTH_TABLES = JSON.parse(JSON.stringify(INITIAL_HEALTH_TABLES));

  function resetToEmptyState() {
    isDataLoaded = false;
    currentScenarioKey = null;
    DECISIONS = [];
    realizedTotal = 0;
    uploadedFiles = [];
    HEALTH_TABLES = JSON.parse(JSON.stringify(INITIAL_HEALTH_TABLES));

    // Reset Scenario Buttons
    ['superstore', 'express', 'online'].forEach(k => {
      const btn = document.getElementById(`btn-scen-${k}`);
      if (btn) btn.className = 'btn';
    });

    // Reset Top Banner
    const pName = document.getElementById('current-place-name');
    if (pName) {
      pName.innerText = 'لم يتم اختيار فرع بعد (في انتظار رفع البيانات)';
      pName.style.color = 'var(--text-muted)';
    }
    const pIssue = document.getElementById('current-place-issue');
    if (pIssue) {
      pIssue.innerText = 'ارفع ملفات CSV من تبويب رفع البيانات أو اختر فرعًا أدناه';
      pIssue.style.color = 'var(--text-muted)';
    }

    // Reset Freshness Bar
    const fContainer = document.getElementById('freshness-container');
    if (fContainer) fContainer.style.borderRight = '4px solid var(--border)';
    const fIcon = document.getElementById('freshness-icon');
    if (fIcon) fIcon.innerText = '📁';
    const fBadge = document.getElementById('freshness-badge');
    if (fBadge) {
      fBadge.className = 'badge badge-gray';
      fBadge.innerText = 'NO_DATA · في انتظار الجداول';
    }
    const fText = document.getElementById('freshness-text');
    if (fText) {
      fText.innerHTML = 'لا توجد بيانات مرفوعة بعد · يُرجى رفع جداول البيانات لبدء فحص المؤشرات وكشف التسرّب.';
    }
    const fSub = document.getElementById('freshness-sub');
    if (fSub) fSub.innerText = 'النظام في وضع البداية الفارغ';

    // Reset KPIs in Tab 1
    const rVal = document.getElementById('kpi-risk-val');
    if (rVal) rVal.innerText = '-- ج.م';
    const rSub = document.getElementById('kpi-risk-sub');
    if (rSub) rSub.innerText = 'في انتظار رفع البيانات';

    const rcVal = document.getElementById('kpi-recoverable-val');
    if (rcVal) rcVal.innerText = '-- ج.م';
    const rcSub = document.getElementById('kpi-rec-sub');
    if (rcSub) rcSub.innerText = 'في انتظار التحليل';

    const soVal = document.getElementById('kpi-stockout-val');
    if (soVal) soVal.innerText = '0 صنف';
    const soSub = document.getElementById('kpi-stockout-sub');
    if (soSub) soSub.innerText = 'لا توجد بيانات';

    const osVal = document.getElementById('kpi-overstock-val');
    if (osVal) osVal.innerText = '0 صنف';
    const osSub = document.getElementById('kpi-overstock-sub');
    if (osSub) osSub.innerText = 'لا توجد بيانات';

    // Reset Leakage Progress Box in Tab 1
    const pBox = document.getElementById('leak-progress-box');
    if (pBox) {
      pBox.innerHTML = '<div style="text-align: center; padding: 25px; color: var(--text-muted); font-size: 12px;">📊 في انتظار رفع البيانات لاحتساب مسارات ونسب التسرّب.</div>';
    }

    // Reset Top 3 decisions in Tab 1
    const ccBox = document.getElementById('command-decisions');
    if (ccBox) {
      ccBox.innerHTML = `
        <div style="text-align:center; padding: 25px 15px; background: var(--bg-sunken); border-radius: 12px; border: 1px dashed var(--border);">
          <div style="font-size: 26px; margin-bottom: 6px;">📂</div>
          <div style="font-weight: 800; font-size: 13px; margin-bottom: 4px;">لا توجد قرارات تجارية مقترحة حتى الآن</div>
          <div style="font-size: 11.5px; color: var(--text-muted); margin-bottom: 12px;">يتطلب النظام استيراد جداول المبيعات والمخزون والمرتجعات لكشف التسرّب وتوليد التوصيات.</div>
          <button class="btn btn-primary" onclick="switchTab('tab-data', document.querySelectorAll('.nav-tab')[5])" style="font-size: 11.5px; padding: 5px 12px;">
            📂 الانتقال لتبويب رفع البيانات ←
          </button>
        </div>
      `;
    }

    // Reset Decisions list in Tab 3
    const dBox = document.getElementById('decisions-list');
    if (dBox) {
      dBox.innerHTML = `
        <div style="text-align: center; padding: 35px; background: var(--bg-sunken); border-radius: 12px; color: var(--text-muted); font-size: 12.5px;">
          ⚡ محرك القرارات في وضع الاستعداد. ارفع جداول المتجر لبدء استخراج التوصيات ذات العائد المالي المباشر.
        </div>
      `;
    }

    // Reset Leakage Table in Tab 2
    const tBody = document.getElementById('leakage-table-body');
    if (tBody) {
      tBody.innerHTML = '<tr><td colspan="5" style="text-align: center; padding: 30px; color: var(--text-muted); font-size: 12px;">📁 لا توجد سجلات تسرّب مسجلة حاليًا. قم برفع جداول البيانات أولاً.</td></tr>';
    }

    // Reset Tab 6 Health Summary Counters
    const activeEl = document.getElementById('health-active-count');
    if (activeEl) activeEl.innerText = '0';
    const attEl = document.getElementById('health-attention-count');
    if (attEl) attEl.innerText = '0';
    const scoreEl = document.getElementById('health-quality-score');
    if (scoreEl) scoreEl.innerText = '0%';
    const syncEl = document.getElementById('health-sync-text');
    if (syncEl) syncEl.innerHTML = '🔄 حالة المزامنة: <b>لم يتم رفع أي جداول حتى الآن</b>';
    const hBadge = document.getElementById('health-header-badge');
    if (hBadge) {
      hBadge.className = 'badge badge-gray';
      hBadge.innerText = 'NO_DATA';
    }

    // Reset CFO Simulator
    const simRes = document.getElementById('sim-profit-result');
    if (simRes) simRes.innerText = '+0 ج.م';
    const simLift = document.getElementById('sim-margin-lift');
    if (simLift) simLift.innerText = '+0.0%';

    // Re-render
    renderKanban();
    renderHealthTable();
    clearFiles();
  }
"""

    # Check if resetToEmptyState is in JS
    if "function resetToEmptyState()" not in html:
        # Insert before switchScenario
        html = html.replace("// Scenario Switcher Function", empty_state_js + "\n  // Scenario Switcher Function")
        print("-> resetToEmptyState function added")

    # In switchScenario, set isDataLoaded = true and activate visuals
    old_switch_scen = """  function switchScenario(key) {
    if (!SCENARIOS[key]) return;
    currentScenarioKey = key;"""
    new_switch_scen = """  function switchScenario(key) {
    if (!SCENARIOS[key]) return;
    isDataLoaded = true;
    currentScenarioKey = key;

    // Update Freshness Bar to Fresh
    const fContainer = document.getElementById('freshness-container');
    if (fContainer) fContainer.style.borderRight = '4px solid var(--green)';
    const fIcon = document.getElementById('freshness-icon');
    if (fIcon) fIcon.innerText = '🕐';
    const fBadge = document.getElementById('freshness-badge');
    if (fBadge) {
      fBadge.className = 'badge badge-green';
      fBadge.innerText = 'FRESH · جاهز للقرارات';
    }
    const fText = document.getElementById('freshness-text');
    if (fText) {
      fText.innerHTML = 'تم استيعاب وتحليل بيانات الفرع بنجاح <b style="color:var(--green);">(بيانات حديثة وموثوقة حتى 14 نوفمبر 2026)</b>';
    }
    const fSub = document.getElementById('freshness-sub');
    if (fSub) fSub.innerText = 'المزامنة مكتملة وشاملة';

    // Update Health Table Counters
    const activeEl = document.getElementById('health-active-count');
    if (activeEl) activeEl.innerText = '6';
    const attEl = document.getElementById('health-attention-count');
    if (attEl) attEl.innerText = '0';
    const scoreEl = document.getElementById('health-quality-score');
    if (scoreEl) scoreEl.innerText = '99.6%';
    const syncEl = document.getElementById('health-sync-text');
    if (syncEl) syncEl.innerHTML = '🔄 المزامنة الشاملة لجميع الفروع: <b style="color:var(--green);">اليوم (مُحدّثة بالكامل)</b>';
    const hBadge = document.getElementById('health-header-badge');
    if (hBadge) {
      hBadge.className = 'badge badge-green';
      hBadge.innerText = 'HEALTHY';
    }"""
    if old_switch_scen in html:
        html = html.replace(old_switch_scen, new_switch_scen)
        print("-> switchScenario enhanced with visual activation")

    # Update renderHealthTable to handle NOT_LOADED status
    old_render_health = """    tbody.innerHTML = HEALTH_TABLES.map(t => {
      const badgeClass = t.status === 'HEALTHY' ? 'badge-green' : (t.status === 'ATTENTION' ? 'badge-amber' : 'badge-red');
      const barColor = t.quality >= 98 ? '#10b981' : (t.quality >= 95 ? '#f59e0b' : '#ef4444');"""
    new_render_health = """    tbody.innerHTML = HEALTH_TABLES.map(t => {
      const badgeClass = t.status === 'HEALTHY' ? 'badge-green' : (t.status === 'ATTENTION' ? 'badge-amber' : (t.status === 'NOT_LOADED' ? 'badge-gray' : 'badge-red'));
      const barColor = t.status === 'NOT_LOADED' ? '#94a3b8' : (t.quality >= 98 ? '#10b981' : (t.quality >= 95 ? '#f59e0b' : '#ef4444'));"""
    if old_render_health in html:
        html = html.replace(old_render_health, new_render_health)
        print("-> renderHealthTable updated to handle NOT_LOADED")

    # In initialization: Call resetToEmptyState() so it begins completely empty
    old_init = """  // Initialize all sections
  renderDecisions();
  updateSim();
  renderHealthTable();
  loadCompanyName();"""
    new_init = """  // Initialize all sections in Empty State
  loadCompanyName();
  resetToEmptyState();"""
    if old_init in html:
        html = html.replace(old_init, new_init)
        print("-> Initialization updated to begin in Empty State!")
    else:
        print("WARN: old_init not matched, checking...")

    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Saved {INDEX_PATH}")

    shutil.copy2(INDEX_PATH, DEMO_PATH)
    shutil.copy2(INDEX_PATH, ROOT_INDEX)
    if ARTIFACT_PATH.parent.exists():
        shutil.copy2(INDEX_PATH, ARTIFACT_PATH)
    print("Copied to all targets successfully")

if __name__ == "__main__":
    patch()
