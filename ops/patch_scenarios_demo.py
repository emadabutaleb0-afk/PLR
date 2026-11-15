"""Patch docs/index.html to support dynamic multi-location scenarios,
downloadable scenario packages, and distinct leakage & decision outcomes.
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

    # 1. Add Scenario Bar right inside <main> before Tab 1
    scenario_bar_html = """    <!-- Scenario Switcher Bar (Multi-Place & Results) -->
    <div class="card" style="margin-bottom: 20px; background: linear-gradient(135deg, var(--bg-surface) 0%, var(--bg-sunken) 100%); border: 1.5px solid var(--accent); padding: 14px 18px;">
      <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px;">
        <div style="display: flex; align-items: center; gap: 10px;">
          <span style="font-size: 24px;">🏢</span>
          <div>
            <div style="font-weight: 900; font-size: 13.5px; color: var(--text-main);">محاكي أماكن وفروع العمل (Multi-Location & Scenario Switcher):</div>
            <div style="font-size: 11.5px; color: var(--text-muted);">اضغط لتغيير مكان الفرع واختبار نتائج مالية وقنوات تسرّب وقرارات مختلفة تمامًا:</div>
          </div>
        </div>
        <div style="display: flex; gap: 8px; flex-wrap: wrap;" id="scenario-btn-group">
          <button class="btn btn-primary" id="btn-scen-superstore" onclick="switchScenario('superstore')">
            🏬 المكان 1: هايبرماركت الدوحة الكبرى <span style="font-size: 10px; opacity: 0.9;">(تلف وركود)</span>
          </button>
          <button class="btn" id="btn-scen-express" onclick="switchScenario('express')">
            ⚡ المكان 2: فرع وسط البلد السريع <span style="font-size: 10px; opacity: 0.9;">(نفاد ومبيعات ضائعة)</span>
          </button>
          <button class="btn" id="btn-scen-online" onclick="switchScenario('online')">
            🌐 المكان 3: مستودع الجملة والأونلاين <span style="font-size: 10px; opacity: 0.9;">(خصومات ومرتجعات)</span>
          </button>
        </div>
      </div>
      <div id="scenario-summary-banner" style="margin-top: 10px; padding: 8px 12px; background: var(--bg-surface); border-radius: 8px; font-size: 12px; border: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 6px;">
        <span>📍 <b>المكان الحالي:</b> <span id="current-place-name" style="color: var(--accent); font-weight: 800;">هايبرماركت الدوحة الكبرى (LOC-005)</span></span>
        <span>⚠️ <b>الخلل المالي المستهدف:</b> <span id="current-place-issue" style="color: var(--red); font-weight: 700;">هدر وتلف أطعمة طازجة وركود مخزون لأكثر من 180 يوم</span></span>
      </div>
    </div>\n\n    <!-- ==================== TAB 1: COMMAND CENTER ==================== -->"""

    if "<!-- Scenario Switcher Bar" not in html:
        html = html.replace("<!-- ==================== TAB 1: COMMAND CENTER ==================== -->", scenario_bar_html)
        print("-> Scenario Switcher Bar added to main")

    # 2. Tag KPI elements with IDs in Tab 1
    # Replace the 4 KPI cards with ID-tagged cards
    old_kpi_block = re.search(r'<div class="grid-4" style="margin-bottom: 20px;">.*?</div>\s*</div>\s*<div class="grid-2">', html, re.DOTALL)
    if old_kpi_block:
        new_kpi_block = """<div class="grid-4" style="margin-bottom: 20px;">
          <div class="card" style="border-right: 4px solid var(--red);">
            <div class="card-header"><span class="card-title">إجمالي الربح المعرّض للخطر</span><span class="badge badge-red">خسارة كامنة</span></div>
            <div class="kpi-num" id="kpi-risk-val" style="color: var(--red);">14,850,200 ج.م</div>
            <div id="kpi-risk-sub" style="font-size: 11.5px; color: var(--text-muted);">أرباح مهددة في الفروع بسبب التلف والركود</div>
          </div>
          <div class="card" style="border-right: 4px solid var(--green);">
            <div class="card-header"><span class="card-title">الأرباح القابلة للاسترداد فورًا</span><span class="badge badge-green">كاش متاح</span></div>
            <div class="kpi-num" id="kpi-recoverable-val" style="color: var(--green);">5,420,000 ج.م</div>
            <div id="kpi-rec-sub" style="font-size: 11.5px; color: var(--text-muted);">عائد نقدي مباشر من تنفيذ توصيات الرادار</div>
          </div>
          <div class="card" style="border-right: 4px solid var(--amber);">
            <div class="card-header"><span class="card-title">أصناف مهددة بالنفاد (Stockout)</span><span class="badge badge-amber">مبيعات ضائعة</span></div>
            <div class="kpi-num" id="kpi-stockout-val" style="color: var(--amber);">12 صنف</div>
            <div id="kpi-stockout-sub" style="font-size: 11.5px; color: var(--text-muted);">نقص محدود في فروع معينة</div>
          </div>
          <div class="card" style="border-right: 4px solid var(--accent);">
            <div class="card-header"><span class="card-title">أصناف فائضة وراكدة (Overstock)</span><span class="badge badge-indigo">كاش محبوس</span></div>
            <div class="kpi-num" id="kpi-overstock-val" style="color: var(--accent);">68 صنف</div>
            <div id="kpi-overstock-sub" style="font-size: 11.5px; color: var(--text-muted);">تغطي أكثر من 180 يومًا بدون دوران كافٍ</div>
          </div>
        </div>

        <div class="grid-2">"""
        html = html.replace(old_kpi_block.group(0), new_kpi_block)
        print("-> Tab 1 KPI cards updated with IDs")

    # 3. Tag Progress bars in Tab 1 with an ID container
    old_leak_container = re.search(r'<div style="margin: 16px 0;">\s*<div class="leak-row">.*?</div>\s*</div>\s*<div style="background: var\(--bg-sunken\);', html, re.DOTALL)
    if old_leak_container:
        new_leak_container = """<div id="leak-progress-box" style="margin: 16px 0;">
              <!-- Rendered dynamically -->
            </div>
          </div>
          <div style="background: var(--bg-sunken);"""
        html = html.replace(old_leak_container.group(0), new_leak_container)
        print("-> Tab 1 Leak progress box tagged")

    # 4. Tag Tab 2 Leakage table body
    old_tab2_table = re.search(r'<table style="width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 10px;">.*?<tbody>.*?</tbody>\s*</table>', html, re.DOTALL)
    if old_tab2_table:
        new_tab2_table = """<table style="width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 10px;">
          <thead>
            <tr style="background: var(--bg-sunken); border-bottom: 2px solid var(--border); text-align: right;">
              <th style="padding: 10px;">نوع التسرّب</th>
              <th style="padding: 10px;">القيمة المقدرة</th>
              <th style="padding: 10px;">نسبة المساهمة</th>
              <th style="padding: 10px;">السبب الجذري</th>
              <th style="padding: 10px;">الإجراء المالي الموصى به</th>
            </tr>
          </thead>
          <tbody id="leakage-table-body">
            <!-- Rendered dynamically by scenario -->
          </tbody>
        </table>"""
        html = html.replace(old_tab2_table.group(0), new_tab2_table)
        print("-> Tab 2 Leakage table body tagged")

    # 5. Add Scenario Download Section to Tab 6
    scenario_downloads_card = """      <!-- Scenario Datasets Download Card -->
      <div class="card" style="margin-bottom: 20px; border-right: 4px solid var(--accent);">
        <div class="card-header">
          <span class="card-title">🏢 نماذج بيانات الفروع والأماكن المختلفة (3 Scenarios Packages)</span>
          <span class="badge badge-indigo">بيانات جاهزة للتجربة</span>
        </div>
        <p style="font-size: 12px; color: var(--text-muted); margin: 0 0 16px;">
          تم إعداد 3 مجموعات بيانات مستقلة تمثل 3 فروع بطبيعة تشغيل ونتائج تسرب مختلفة كليًا، لتجربة كيفية اختلاف تحليلات الرادار والقرارات عند رفع ملفات كل مكان:
        </p>

        <div class="grid-3" style="gap: 14px;">
          <!-- Scenario 1 -->
          <div style="background: var(--bg-sunken); border: 1px solid var(--border); border-radius: 12px; padding: 14px;">
            <div style="font-weight: 800; font-size: 13px; color: var(--red); margin-bottom: 4px;">🏬 المكان 1: هايبرماركت الدوحة الكبرى</div>
            <div style="font-size: 11px; color: var(--text-muted); margin-bottom: 10px;">طبيعة الهدر: <b>تلف أطعمة مبردة + ركود 68 صنف</b></div>
            <div style="font-size: 11px; margin-bottom: 12px;">
              • الخطر المالي: <b>14.85 مليون ج.م</b><br>
              • الأرباح المستردة: <b>5.42 مليون ج.م</b>
            </div>
            <div style="display: flex; flex-direction: column; gap: 6px;">
              <a href="sample_data/scenarios/Scenario1_Superstore_Hub.zip" download class="btn" style="text-align: center; text-decoration: none; font-size: 11px; padding: 6px;">
                📦 تنزيل ملفات الفرع (.ZIP)
              </a>
              <button class="btn btn-primary" onclick="switchScenario('superstore')" style="font-size: 11px; padding: 6px;">
                ⚡ عرض وتطبيق نتائج هذا الفرع
              </button>
            </div>
          </div>

          <!-- Scenario 2 -->
          <div style="background: var(--bg-sunken); border: 1px solid var(--border); border-radius: 12px; padding: 14px;">
            <div style="font-weight: 800; font-size: 13px; color: var(--amber); margin-bottom: 4px;">⚡ المكان 2: فرع وسط البلد السريع</div>
            <div style="font-size: 11px; color: var(--text-muted); margin-bottom: 10px;">طبيعة الهدر: <b>نفاد مخزون 58 صنف + مبيعات ضائعة</b></div>
            <div style="font-size: 11px; margin-bottom: 12px;">
              • الخطر المالي: <b>9.64 مليون ج.م</b><br>
              • الأرباح المستردة: <b>4.18 مليون ج.م</b>
            </div>
            <div style="display: flex; flex-direction: column; gap: 6px;">
              <a href="sample_data/scenarios/Scenario2_Express_Downtown.zip" download class="btn" style="text-align: center; text-decoration: none; font-size: 11px; padding: 6px;">
                📦 تنزيل ملفات الفرع (.ZIP)
              </a>
              <button class="btn btn-primary" onclick="switchScenario('express')" style="font-size: 11px; padding: 6px;">
                ⚡ عرض وتطبيق نتائج هذا الفرع
              </button>
            </div>
          </div>

          <!-- Scenario 3 -->
          <div style="background: var(--bg-sunken); border: 1px solid var(--border); border-radius: 12px; padding: 14px;">
            <div style="font-weight: 800; font-size: 13px; color: var(--accent); margin-bottom: 4px;">🌐 المكان 3: مستودع الجملة والأونلاين</div>
            <div style="font-size: 11px; color: var(--text-muted); margin-bottom: 10px;">طبيعة الهدر: <b>خصومات وكوبونات مفرطة + مرتجعات شحن</b></div>
            <div style="font-size: 11px; margin-bottom: 12px;">
              • الخطر المالي: <b>18.22 مليون ج.م</b><br>
              • الأرباح المستردة: <b>6.85 مليون ج.م</b>
            </div>
            <div style="display: flex; flex-direction: column; gap: 6px;">
              <a href="sample_data/scenarios/Scenario3_Online_Wholesale.zip" download class="btn" style="text-align: center; text-decoration: none; font-size: 11px; padding: 6px;">
                📦 تنزيل ملفات الفرع (.ZIP)
              </a>
              <button class="btn btn-primary" onclick="switchScenario('online')" style="font-size: 11px; padding: 6px;">
                ⚡ عرض وتطبيق نتائج هذا الفرع
              </button>
            </div>
          </div>
        </div>

        <div style="margin-top: 14px; padding-top: 12px; border-top: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
          <a href="sample_data/All_Scenarios_Retail_Package.zip" download class="btn btn-primary" style="text-decoration: none; font-size: 12px;">
            📦 تنزيل حزمة كافة الفروع مجتمعة (All_Scenarios_Retail_Package.zip)
          </a>
          <span style="font-size: 11px; color: var(--text-muted);">
            💡 يمكنك فك الضغط وسحب أي ملف CSV وإسقاطه في منطقة الرفع أدناه لاختبار المعالجة الذاتية فورًا.
          </span>
        </div>
      </div>\n\n      <!-- Sample Data Download Section -->"""

    if "<!-- Scenario Datasets Download Card -->" not in html:
        html = html.replace("<!-- Sample Data Download Section -->", scenario_downloads_card)
        print("-> Tab 6 Scenario Datasets download card added")

    # 6. Replace JavaScript Scenario Data & Engine
    scenario_js_code = """
  // ==================== MULTI-LOCATION SCENARIOS DATA ====================
  const SCENARIOS = {
    superstore: {
      name: "هايبرماركت الدوحة الكبرى (LOC-005)",
      issue: "هدر وتلف أطعمة طازجة وركود مخزون لأكثر من 180 يوم",
      riskVal: "14,850,200 ج.م",
      riskSub: "أرباح مهددة في الفرع بسبب التلف والركود الحاد",
      recVal: "5,420,000 ج.م",
      recSub: "عائد نقدي مباشر من تصفية الركود ومعالجة الهدر",
      stockoutVal: "12 صنف",
      stockoutSub: "نقص طفيف محصور في أصناف تكميلية",
      overstockVal: "68 صنف",
      overstockSub: "مخزون محبوس يكفي أكثر من 180 يومًا بدون دوران",
      simProfit: 1350000,
      simMargin: "+3.2%",
      leakRows: [
        { label: "هدر وتلف الأغذية الطازجة (Spoilage & Expiry)", val: "3,850,000 ج.م (71%)", pct: 71, color: "#ef4444" },
        { label: "خسائر المخزون الراكد وتكلفة التخزين (Overstock)", val: "1,420,000 ج.م (26%)", pct: 26, color: "#6366f1" },
        { label: "مبيعات ضائعة من النفاد (Stockouts)", val: "150,000 ج.م (3%)", pct: 3, color: "#f59e0b" }
      ],
      tableRows: [
        { type: "تلف وهدر الأغذية الطازجة", val: "3,850,000 ج.م", pct: "71%", reason: "تراكم بضائع اللحوم والألبان قبل 7 أيام من الصلاحية دون بيع", action: "تصفية عاجلة وخصم تدريجي تلقائي", badge: "badge-red" },
        { type: "مخزون راكد غير متحرك", val: "1,420,000 ج.م", pct: "26%", reason: "طلب كميات تفوق الطاقة الاستيعابية الشهرية للمتجر", action: "تخفيض حدود الأمان بنسبة 40%", badge: "badge-indigo" },
        { type: "مبيعات ضائعة من النفاد", val: "150,000 ج.م", pct: "3%", reason: "تأخر إعادة الطلب في 12 صنف تكميلي", action: "إعادة ضبط التوريد الدوري", badge: "badge-green" }
      ],
      decisions: [
        {
          id: "sup-clearance",
          title: "تفعيل تصفية عاجلة وخصم تدريجي على لحوم وألبان قبل انتهاء الصلاحية بـ 7 أيام",
          urgency: "HIGH",
          area: "المخزون والتسعير",
          problem: "رصد 480 قطعة لحوم وألبان معرضة للتلف التام خلال أسبوع في هايبرماركت الدوحة.",
          why: "عدم بيع هذه البضاعة سيحول قيمتها بالكامل إلى خسارة إعدام صافية (Waste).",
          action: "تطبيق خصم تصفية متدرج 20% يبدأ اليوم لاسترداد تكلفة الشراء كاملة وكاش فوري.",
          value_egp: 480000,
          confidence: 0.94,
          status: "open"
        },
        {
          id: "sup-vendor-sla",
          title: "تفعيل بند استرجاع التالف وتعديل شروط التوريد مع المورد Al Meera Supply",
          urgency: "HIGH",
          area: "الموردين والعقود",
          problem: "ارتفاع نسبة عيوب التبريد والتلف في استلامات الألبان الواردة من المورد الأخير.",
          why: "العقد يتضمن حق الاسترجاع بنسبة 100% خلال 48 ساعة من رصد عيب التبريد.",
          action: "خصم قيمة التالف من مستحقات الفاتورة القادمة للمورد فورًا وتوثيق الخلل.",
          value_egp: 320000,
          confidence: 0.89,
          status: "open"
        },
        {
          id: "sup-safety-cut",
          title: "خفض حدود الأمان (Safety Stock) لأصناف الأغذية المبردة بنسبة 40%",
          urgency: "MEDIUM",
          area: "الميرشاندايزينج",
          problem: "الفرع يطلب 5 أضعاف حجم المبيعات اليومية مما يتسبب في انتهاء صلاحيتها في المستودع.",
          why: "تقليل حد الأمان يحافظ على دوران سريع للبضائع وطزاجة مستمرة في العرض.",
          action: "تعديل محددات نظام الشراء التلقائي لخفض التوريد الفائض بنسبة 40%.",
          value_egp: 290000,
          confidence: 0.85,
          status: "open"
        }
      ]
    },

    express: {
      name: "فرع وسط البلد السريع (LOC-003)",
      issue: "نفاد مخزون 58 صنف ومبيعات ضائعة يوميًا مع انعدام التلف",
      riskVal: "9,640,000 ج.م",
      riskSub: "أرباح مهددة بالضياع بسبب الرفوف الفارغة ونفاد الأصناف البطلة",
      recVal: "4,180,000 ج.م",
      recSub: "أرباح نقدية مستردة فور تحويل البضائع وتعديل التوريد",
      stockoutVal: "58 صنف",
      stockoutSub: "أصناف بطلة (Best Sellers) تنفد خلال ساعتين من الذروة",
      overstockVal: "6 أصناف",
      overstockSub: "مساحة الفرع صغيرة والمخزون يدور بسرعة فائقة",
      simProfit: 1120000,
      simMargin: "+2.7%",
      leakRows: [
        { label: "مبيعات وأرباح ضائعة من الرفوف الفارغة (Stockouts)", val: "3,150,000 ج.م (75%)", pct: 75, color: "#f59e0b" },
        { label: "تكلفة شحن وتوريد طارئ سريع (Emergency Freight)", val: "780,000 ج.م (19%)", pct: 19, color: "#6366f1" },
        { label: "هدر جودة وتلفيات مناولة (Spoilage)", val: "250,000 ج.م (6%)", pct: 6, color: "#10b981" }
      ],
      tableRows: [
        { type: "مبيعات ضائعة من نفاد المخزون", val: "3,150,000 ج.م", pct: "75%", reason: "الطلب يتجاوز المعروض بـ 3 أضعاف بسبب موقع الفرع بوسط البلد", action: "تحويل مخزون فوري من المستودع المركزي", badge: "badge-amber" },
        { type: "تكلفة شحن وتوريد طارئ", val: "780,000 ج.م", pct: "19%", reason: "طلب بضائع بنظام النقل الفردي المستعجل لتعويض الرفوف", action: "جدولة نقل يومي صباحي منتظم", badge: "badge-indigo" },
        { type: "تلفيات مناولة وسقوط", val: "250,000 ج.م", pct: "6%", reason: "ازدحام التخزين في المساحة الضيقة داخل الفرع", action: "تنظيم ممرات التخزين الخلفية", badge: "badge-green" }
      ],
      decisions: [
        {
          id: "exp-transfer",
          title: "نقل وتحويل مخزون فوري (Stock Transfer) من المستودع إلى فرع وسط البلد",
          urgency: "HIGH",
          area: "اللوجستيات والمخزون",
          problem: "فرع وسط البلد نفد لديه صنف Beef Steak والمخبوزات بينما المستودع به فائض 200 يوم.",
          why: "العملاء يبحثون عن الصنف ويغادرون بدون شراء لعدم توفره على الرف.",
          action: "إصدار أمر نقل فوري لـ 80 وحدة من المستودع المركزي لحماية مبيعات اليوم والغد.",
          value_egp: 410000,
          confidence: 0.95,
          status: "open"
        },
        {
          id: "exp-reorder-point",
          title: "مضاعفة نقطة إعادة الطلب (Reorder Point) للمخبوزات والمشروبات سريعة البيع",
          urgency: "HIGH",
          area: "الميرشاندايزينج",
          problem: "نقطة إعادة الطلب الحالية مضبوطة على 30 وحدة، وتنفد في ساعة الذروة الصباحية.",
          why: "رفع حد إعادة الطلب إلى 80 وحدة يضمن وجود مخزون أمان مستمر طوال النهار.",
          action: "تحديث متغير Reorder Point في نظام الـ ERP ليعمل تلقائيًا عند وصول الرصيد لـ 80.",
          value_egp: 350000,
          confidence: 0.91,
          status: "open"
        },
        {
          id: "exp-daily-dock",
          title: "جدولة توريد صباحي ومسائي منتظم بدلاً من مرتين أسبوعيًا لتفادي نفاد الذروة",
          urgency: "MEDIUM",
          area: "عمليات التوريد",
          problem: "التوريد مرتين أسبوعيًا لا يستوعب وتيرة المبيعات السريعة لموقع وسط البلد.",
          why: "تجزئة شحنات التوريد تناسب مساحة الفرع المحدودة وتمنع نفاد المساء بالكامل.",
          action: "اعتماد مسار شاحنة التوزيع الصباحية لتمر بفرع وسط البلد يوميًا الساعة 7 صباحًا.",
          value_egp: 280000,
          confidence: 0.88,
          status: "open"
        }
      ]
    },

    online: {
      name: "مستودع الجملة وقناة الأونلاين (LOC-006)",
      issue: "تآكل الهامش بالخصومات الزائدة (67%) ومرتجعات الشحن",
      riskVal: "18,220,000 ج.م",
      riskSub: "أرباح مهددة بسبب تآكل الهامش من الكوبونات ومرتجعات التوصيل",
      recVal: "6,850,000 ج.م",
      recSub: "عائد نقدي مباشر من حوكمة الخصومات وحماية تكلفة الشحن",
      stockoutVal: "18 صنف",
      stockoutSub: "نفاد متقطع في الأجهزة والأصناف المميزة",
      overstockVal: "52 صنف",
      overstockSub: "مخزون جملة مكدس لبعض الماركات غير الرائجة",
      simProfit: 1680000,
      simMargin: "+3.9%",
      leakRows: [
        { label: "تآكل الأرباح بسبب الخصومات والكوبونات المفرطة (Discount Leak)", val: "4,620,000 ج.م (67%)", pct: 67, color: "#ef4444" },
        { label: "تكلفة مرتجعات الشحن وإلغاء الأوردرات (Shipping Returns)", val: "1,580,000 ج.م (23%)", pct: 23, color: "#6366f1" },
        { label: "تلفيات التعبئة وسوء مناولة التوصيل (Handling Damage)", val: "650,000 ج.م (10%)", pct: 10, color: "#f59e0b" }
      ],
      tableRows: [
        { type: "تآكل الأرباح بالخصومات المفرطة", val: "4,620,000 ج.م", pct: "67%", reason: "تطبيق كوبونات خصم 20% على أصناف هامشها الأصلي 12% فقط", action: "إلغاء الخصم ووضع سقف خصم لا يتجاوز 5%", badge: "badge-red" },
        { type: "تكاليف مرتجعات وإلغاء الشحن", val: "1,580,000 ج.م", pct: "23%", reason: "تأخر التوصيل لبعض المناطق مما يدفع العميل لرفض الاستلام", action: "تحسين مواعيد التوصيل والتأكيد الهاتفي", badge: "badge-indigo" },
        { type: "تلفيات كراتين الشحن والتعبئة", val: "650,000 ج.م", pct: "10%", reason: "استخدام كراتين شحن ضعيفة لا تحمي السلع الزجاجية والمبردة", action: "ترقية مواد التغليف واعتماد عوازل حرارية", badge: "badge-amber" }
      ],
      decisions: [
        {
          id: "onl-discount-cap",
          title: "إلغاء كود الخصم 20% على المنتجات التي يقل هامشها عن 15% لحماية الأرباح",
          urgency: "HIGH",
          area: "التسعير والخصومات",
          problem: "حملة التسويق تمنح خصم 20% لعملاء الأونلاين مما يحول مبيعات السلع المربحة إلى خسارة.",
          why: "الخصم يحرق الأرباح دون رفع حجم الطلب (Margin Bleed).",
          action: "استبعاد قائمة الأصناف ذات الهامش المنخفض من كود الخصم وتحديد حد أقصى 5% فقط.",
          value_egp: 620000,
          confidence: 0.96,
          status: "open"
        },
        {
          id: "onl-min-order",
          title: "فرض حد أدنى للطلب (Min Order Value 300 EGP) لحماية هوامش التوصيل المجاني",
          urgency: "HIGH",
          area: "التسعير واللوجستيات",
          problem: "خروج شحنات أونلاين مجانية بقيمة 60 جنيه تكلف الشركة 45 جنيه مصاريف شحن.",
          why: "اشتراط حد أدنى يضمن تغطية مصاريف الشحن وتحقيق ربح تشغيلي من كل رحلة سيارة.",
          action: "برمجة بوابة المتجر الإلكتروني لطلب 300 ج.م كحد أدنى للاستفادة من التوصيل المجاني.",
          value_egp: 450000,
          confidence: 0.92,
          status: "open"
        },
        {
          id: "onl-pack-audit",
          title: "تدقيق جودة التغليف قبل خروج الأوردرات لتقليص مرتجعات الشحن بنسبة 35%",
          urgency: "MEDIUM",
          area: "العمليات والجودة",
          problem: "15% من المرتجعات سببها وصول العبوات مسحوقة أو تسريب السوائل أثناء التوصيل.",
          why: "استخدام أشرطة لاصقة مقواة وحواجز فلينية يمنع التلف أثناء حركة سيارات التوصيل.",
          action: "إلزام محطة التعبئة بمطابقة بروتوكول التغليف الآمن قبل تسليم الشحنة للسائق.",
          value_egp: 310000,
          confidence: 0.87,
          status: "open"
        }
      ]
    }
  };

  let currentScenarioKey = 'superstore';
  let DECISIONS = SCENARIOS.superstore.decisions;

  // Scenario Switcher Function
  function switchScenario(key) {
    if (!SCENARIOS[key]) return;
    currentScenarioKey = key;
    const scen = SCENARIOS[key];
    DECISIONS = scen.decisions;

    // 1. Update Buttons State
    ['superstore', 'express', 'online'].forEach(k => {
      const btn = document.getElementById(`btn-scen-${k}`);
      if (btn) {
        btn.className = (k === key) ? 'btn btn-primary' : 'btn';
      }
    });

    // 2. Update Banner
    const pName = document.getElementById('current-place-name');
    if (pName) pName.innerText = scen.name;
    const pIssue = document.getElementById('current-place-issue');
    if (pIssue) pIssue.innerText = scen.issue;

    // 3. Update KPIs in Tab 1
    const rVal = document.getElementById('kpi-risk-val');
    if (rVal) rVal.innerText = scen.riskVal;
    const rSub = document.getElementById('kpi-risk-sub');
    if (rSub) rSub.innerText = scen.riskSub;

    const rcVal = document.getElementById('kpi-recoverable-val');
    if (rcVal) rcVal.innerText = scen.recVal;
    const rcSub = document.getElementById('kpi-rec-sub');
    if (rcSub) rcSub.innerText = scen.recSub;

    const soVal = document.getElementById('kpi-stockout-val');
    if (soVal) soVal.innerText = scen.stockoutVal;
    const soSub = document.getElementById('kpi-stockout-sub');
    if (soSub) soSub.innerText = scen.stockoutSub;

    const osVal = document.getElementById('kpi-overstock-val');
    if (osVal) osVal.innerText = scen.overstockVal;
    const osSub = document.getElementById('kpi-overstock-sub');
    if (osSub) osSub.innerText = scen.overstockSub;

    // 4. Update Progress Bars in Tab 1
    const pBox = document.getElementById('leak-progress-box');
    if (pBox) {
      pBox.innerHTML = scen.leakRows.map(r => `
        <div class="leak-row">
          <div class="leak-info"><span>${r.label}</span><span>${r.val}</span></div>
          <div class="progress-track"><div class="progress-fill" style="width: ${r.pct}%; background: ${r.color};"></div></div>
        </div>
      `).join('');
    }

    // 5. Update Leakage Table in Tab 2
    const tBody = document.getElementById('leakage-table-body');
    if (tBody) {
      tBody.innerHTML = scen.tableRows.map(tr => `
        <tr style="border-bottom: 1px solid var(--border);">
          <td style="padding: 10px; font-weight: 700;">${tr.type}</td>
          <td style="padding: 10px; font-weight: 800;">${tr.val}</td>
          <td style="padding: 10px;">${tr.pct}</td>
          <td style="padding: 10px; color: var(--text-muted);">${tr.reason}</td>
          <td style="padding: 10px;"><span class="badge ${tr.badge}">${tr.action}</span></td>
        </tr>
      `).join('');
    }

    // 6. Update CFO Simulator default preview
    const simRes = document.getElementById('sim-profit-result');
    if (simRes) simRes.innerText = '+' + scen.simProfit.toLocaleString() + ' ج.م';
    const simLift = document.getElementById('sim-margin-lift');
    if (simLift) simLift.innerText = scen.simMargin;

    // 7. Re-render Decisions and Kanban
    realizedTotal = 0;
    renderDecisions();
    renderKanban();
  }
"""

    # Replace DECISIONS declaration in html
    if "const DECISIONS = [" in html:
        old_dec_block = re.search(r'const DECISIONS = \[.*?\];\s*const HEALTH_TABLES =', html, re.DOTALL)
        if old_dec_block:
            html = html.replace(old_dec_block.group(0), scenario_js_code + "\n  const HEALTH_TABLES =")
            print("-> Replaced DECISIONS with full SCENARIOS engine in JS")

    # Update autoLoadUpdatedSamples to be scenario-aware
    old_autoload = re.search(r'function autoLoadUpdatedSamples\(\)\s*\{.*?\}', html, re.DOTALL)
    if old_autoload:
        new_autoload = """function autoLoadUpdatedSamples() {
    uploadedFiles = [
      { name: 'Product-Master.csv', size: 7433, status: 'pending' },
      { name: 'Locations.csv', size: 526, status: 'pending' },
      { name: 'Customers.csv', size: 374, status: 'pending' },
      { name: 'Inventory-History.csv', size: 262864, status: 'pending' },
      { name: 'returns_data.csv', size: 274117, status: 'pending' },
      { name: 'Sales-Transactions-Sample.csv', size: 2113930, status: 'pending' }
    ];
    renderFileList();
    processFiles();
  }

  // Auto-detect scenario if specific scenario file uploaded
  function detectScenarioFromFiles() {
    const names = uploadedFiles.map(f => f.name.toLowerCase()).join(' ');
    if (names.includes('s2') || names.includes('express')) {
      switchScenario('express');
    } else if (names.includes('s3') || names.includes('online') || names.includes('wholesale')) {
      switchScenario('online');
    } else if (names.includes('s1') || names.includes('superstore')) {
      switchScenario('superstore');
    }
  }"""
        html = html.replace(old_autoload.group(0), new_autoload)
        print("-> autoLoadUpdatedSamples and detectScenarioFromFiles updated")

    # Ensure detectScenarioFromFiles is called on file processing completion
    if "updateHealthStatsAfterUpload();" in html:
        html = html.replace("updateHealthStatsAfterUpload();", "updateHealthStatsAfterUpload();\n        detectScenarioFromFiles();")
        print("-> detectScenarioFromFiles hooked into processing completion")

    # Hook switchScenario into initialization
    if "loadCompanyName();" in html and "switchScenario('superstore');" not in html:
        html = html.replace("loadCompanyName();", "loadCompanyName();\n  switchScenario('superstore');")
        print("-> switchScenario initialized on load")

    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Saved {INDEX_PATH}")

    shutil.copy2(INDEX_PATH, DEMO_PATH)
    print(f"Copied to {DEMO_PATH}")

    shutil.copy2(INDEX_PATH, ROOT_INDEX)
    print(f"Copied to {ROOT_INDEX}")

    if ARTIFACT_PATH.parent.exists():
        shutil.copy2(INDEX_PATH, ARTIFACT_PATH)
        print(f"Copied to {ARTIFACT_PATH}")

    # Copy scenarios dir to root/sample_data/scenarios too
    root_scenarios = ROOT / "sample_data" / "scenarios"
    root_scenarios.mkdir(parents=True, exist_ok=True)
    for p in (ROOT / "docs" / "sample_data" / "scenarios").glob("*"):
        if p.is_dir():
            shutil.copytree(p, root_scenarios / p.name, dirs_exist_ok=True)
        else:
            shutil.copy2(p, root_scenarios / p.name)
    shutil.copy2(ROOT / "docs" / "sample_data" / "All_Scenarios_Retail_Package.zip", ROOT / "sample_data" / "All_Scenarios_Retail_Package.zip")
    print("Copied scenarios to root sample_data")

if __name__ == "__main__":
    patch()
