"""Update docs/index.html and BusinessGate_Finance_Interactive_Demo.html
with sample data downloads, dynamic health updates, and auto-load demo functionality.
"""
import shutil
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = ROOT / "docs" / "index.html"
DEMO_PATH = ROOT / "docs" / "BusinessGate_Finance_Interactive_Demo.html"
ARTIFACT_PATH = Path(r"C:\Users\EMadHamza\.gemini\antigravity\brain\2201ad41-5133-4dab-bb08-4c42bf15a6e7\BusinessGate_Finance_Interactive_Demo.html")

def patch():
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        html = f.read()

    # Normalize line endings
    html = html.replace("\r\n", "\n")

    # 1. Update Freshness bar in overview with IDs
    html = re.sub(
        r'<div class="freshness-bar">.*?<span style="font-size: 18px;">🕐</span>\s*<div style="flex: 1;">\s*<span style="font-weight: 800; font-size: 12.5px;">[^<]+</span>\s*<span style="font-size: 12px; margin-right: 6px; color: var\(--text-muted\);">.*?</span>\s*</div>\s*<span class="badge badge-green">[^<]+</span>',
        '''<div class="freshness-bar">
        <span style="font-size: 18px;">🕐</span>
        <div style="flex: 1;">
          <span style="font-weight: 800; font-size: 12.5px;">حالة تحديث البيانات:</span>
          <span id="freshness-text" style="font-size: 12px; margin-right: 6px; color: var(--text-muted);">تمت قراءة وتحليل الجداول منذ <b style="color: var(--green);">3 أيام</b> (بيانات حديثة وموثوقة)</span>
        </div>
        <span id="freshness-badge" class="badge badge-green">FRESH · جاهز للقرارات</span>''',
        html,
        flags=re.DOTALL
    )

    # 2. Update Tab 6 Health Summary Card with IDs
    html = re.sub(
        r'<div style="text-align: center; background: var\(--bg-sunken\); border-radius: 10px; padding: 10px;">\s*<div style="font-size: 22px; font-weight: 900; color: var\(--green\);">6</div>\s*<div style="font-size: 11px; color: var\(--text-muted\); font-weight: 700;">جداول نشطة</div>\s*</div>\s*<div style="text-align: center; background: var\(--bg-sunken\); border-radius: 10px; padding: 10px;">\s*<div style="font-size: 22px; font-weight: 900; color: var\(--amber\);">1</div>\s*<div style="font-size: 11px; color: var\(--text-muted\); font-weight: 700;">تحتاج تحديثًا</div>\s*</div>\s*<div style="text-align: center; background: var\(--bg-sunken\); border-radius: 10px; padding: 10px;">\s*<div style="font-size: 22px; font-weight: 900; color: var\(--accent\);">97.3%</div>\s*<div style="font-size: 11px; color: var\(--text-muted\); font-weight: 700;">مؤشر الدقة والجودة</div>\s*</div>',
        '''<div style="text-align: center; background: var(--bg-sunken); border-radius: 10px; padding: 10px;">
                <div id="health-active-count" style="font-size: 22px; font-weight: 900; color: var(--green);">6</div>
                <div style="font-size: 11px; color: var(--text-muted); font-weight: 700;">جداول نشطة</div>
              </div>
              <div style="text-align: center; background: var(--bg-sunken); border-radius: 10px; padding: 10px;">
                <div id="health-attention-count" style="font-size: 22px; font-weight: 900; color: var(--amber);">1</div>
                <div style="font-size: 11px; color: var(--text-muted); font-weight: 700;">تحتاج تحديثًا</div>
              </div>
              <div style="text-align: center; background: var(--bg-sunken); border-radius: 10px; padding: 10px;">
                <div id="health-quality-score" style="font-size: 22px; font-weight: 900; color: var(--accent);">97.3%</div>
                <div style="font-size: 11px; color: var(--text-muted); font-weight: 700;">مؤشر الدقة والجودة</div>
              </div>''',
        html
    )

    html = re.sub(
        r'<div style="margin-top: 12px; font-size: 11.5px; color: var\(--text-muted\);">\s*🔄 المزامنة الشاملة لجميع الفروع: <b>منذ 3 أيام</b>.*?</div>',
        '''<div id="health-sync-text" style="margin-top: 12px; font-size: 11.5px; color: var(--text-muted);">
              🔄 المزامنة الشاملة لجميع الفروع: <b>منذ 3 أيام</b> (جميع الفواتير والمخزون مكتملة الأركان).
            </div>''',
        html
    )

    # 3. Add Sample Download section if not already present
    if "تنزيل نماذج الجداول المحدّثة" not in html:
        sample_card = """      <!-- Sample Data Download Section -->
      <div class="card" style="margin-bottom: 20px; background: linear-gradient(180deg, var(--bg-surface) 0%, var(--bg-sunken) 100%); border: 1px solid var(--accent-soft);">
        <div class="card-header">
          <span class="card-title">📥 تنزيل نماذج الجداول المحدّثة (جاهزة للرفع والتشغيل الفوري)</span>
          <span class="badge badge-green">محدّثة حتى 14 نوفمبر 2026</span>
        </div>
        <p style="font-size: 12px; color: var(--text-muted); margin: 0 0 14px;">
          تم إنشاء وتحديث بيانات الجداول وفق النموذج القياسي لمتاجر التجزئة لتتضمن سجلات حديثة تمامًا (تنتهي في 14 نوفمبر 2026)، وتغطي كافة متطلبات التحقق والمزامنة لحل تنبيه البيانات القديمة.
        </p>

        <div style="display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 14px;">
          <a href="sample_data/Customers.csv" download class="btn" style="text-decoration: none; font-size: 11.5px; padding: 6px 12px;">
            📄 Customers.csv <span style="font-size: 10px; color: var(--text-muted);">(5 عملاء)</span>
          </a>
          <a href="sample_data/Locations.csv" download class="btn" style="text-decoration: none; font-size: 11.5px; padding: 6px 12px;">
            📄 Locations.csv <span style="font-size: 10px; color: var(--text-muted);">(6 فروع)</span>
          </a>
          <a href="sample_data/Product-Master.csv" download class="btn" style="text-decoration: none; font-size: 11.5px; padding: 6px 12px;">
            📄 Product-Master.csv <span style="font-size: 10px; color: var(--text-muted);">(80 صنف)</span>
          </a>
          <a href="sample_data/Inventory-History.csv" download class="btn" style="text-decoration: none; font-size: 11.5px; padding: 6px 12px;">
            📄 Inventory-History.csv <span style="font-size: 10px; color: var(--text-muted);">(أرصدة وهدر حتى 14 نوفمبر)</span>
          </a>
          <a href="sample_data/returns_data.csv" download class="btn" style="text-decoration: none; font-size: 11.5px; padding: 6px 12px;">
            📄 returns_data.csv <span style="font-size: 10px; color: var(--text-muted);">(مرتجعات الأسبوع الأخير)</span>
          </a>
          <a href="sample_data/Sales-Transactions-Sample.csv" download class="btn" style="text-decoration: none; font-size: 11.5px; padding: 6px 12px;">
            📄 Sales-Transactions-Sample.csv <span style="font-size: 10px; color: var(--text-muted);">(24 ألف فاتورة سريعة)</span>
          </a>
        </div>

        <div style="display: flex; gap: 10px; flex-wrap: wrap; align-items: center; border-top: 1px solid var(--border); padding-top: 12px;">
          <a href="sample_data/BusinessGate_Updated_Retail_Samples.zip" download class="btn btn-primary" style="text-decoration: none; font-size: 12px;">
            📦 تحميل الحزمة الكاملة مضغوطة (.ZIP)
          </a>
          <button class="btn" onclick="autoLoadUpdatedSamples()" style="font-size: 12px; background: var(--accent-soft); color: var(--accent); border-color: var(--accent);">
            ⚡ تجربة التحميل والمعالجة التلقائية الفورية في لوحة التحكم
          </button>
        </div>
      </div>\n\n      <!-- File Upload Card -->"""
        html = html.replace("<!-- File Upload Card -->", sample_card)

    # 4. Check autoLoadUpdatedSamples in script
    if "function autoLoadUpdatedSamples()" not in html:
        helpers = """
  // Auto-Load Updated Retail Samples
  function autoLoadUpdatedSamples() {
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

  // Update Health Statistics and Alerts dynamically after processing
  function updateHealthStatsAfterUpload() {
    const hasReturns = uploadedFiles.some(f => f.name.toLowerCase().includes('return') || f.name.toLowerCase().includes('quality'));
    const hasInv = uploadedFiles.some(f => f.name.toLowerCase().includes('inventory') || f.name.toLowerCase().includes('stock'));
    const hasProd = uploadedFiles.some(f => f.name.toLowerCase().includes('product'));
    const hasSales = uploadedFiles.some(f => f.name.toLowerCase().includes('sales') || f.name.toLowerCase().includes('trans'));

    if (hasReturns || uploadedFiles.length >= 3) {
      const retItem = HEALTH_TABLES.find(t => t.name === 'returns_data.csv');
      if (retItem) {
        retItem.rows = 2371;
        retItem.updated = 'اليوم (مُحدّث)';
        retItem.quality = 99.4;
        retItem.status = 'HEALTHY';
        retItem.note = '✅ تم استيعاب بيانات الأسبوع الأخير بنجاح';
      }
    }
    if (hasInv || uploadedFiles.length >= 3) {
      const invItem = HEALTH_TABLES.find(t => t.name === 'inventory_stock.csv');
      if (invItem) {
        invItem.rows = 2882;
        invItem.updated = 'اليوم (مُحدّث)';
        invItem.quality = 99.8;
        invItem.note = '✅ رصيد 14 نوفمبر 2026 مطابق وموثق';
      }
    }
    if (hasProd || uploadedFiles.length >= 3) {
      const prodItem = HEALTH_TABLES.find(t => t.name === 'product_master.csv');
      if (prodItem) {
        prodItem.rows = 80;
        prodItem.updated = 'اليوم (مُحدّث)';
        prodItem.quality = 100;
        prodItem.note = '✅ 80 صنف معتمد ومطابق';
      }
    }
    if (hasSales || uploadedFiles.length >= 3) {
      const salesItem = HEALTH_TABLES.find(t => t.name === 'sales_transactions.csv');
      if (salesItem) {
        salesItem.rows = 294067;
        salesItem.updated = 'اليوم (مُحدّث)';
        salesItem.quality = 99.5;
        salesItem.note = '✅ تغطية مستمرة حتى 14 نوفمبر 2026';
      }
    }

    // Update Counter Badges
    const attEl = document.getElementById('health-attention-count');
    if (attEl) attEl.innerText = '0';
    const scoreEl = document.getElementById('health-quality-score');
    if (scoreEl) scoreEl.innerText = '99.6%';
    const syncEl = document.getElementById('health-sync-text');
    if (syncEl) syncEl.innerHTML = '🔄 المزامنة الشاملة لجميع الفروع: <b style="color:var(--green);">اليوم (مُحدّثة بالكامل)</b>';

    // Update Top Freshness Bar
    const freshText = document.getElementById('freshness-text');
    if (freshText) {
      freshText.innerHTML = 'تمت معالجة وتحديث كافة الجداول المرفوعة بنجاح <b style="color: var(--green);">(بيانات حديثة وموثوقة حتى 14 نوفمبر 2026)</b>';
    }
    const freshBadge = document.getElementById('freshness-badge');
    if (freshBadge) {
      freshBadge.className = 'badge badge-green';
      freshBadge.innerText = 'FRESH · 100% مُحدّث اليوم';
    }

    renderHealthTable();
  }
"""
        html = html.replace("// Initialize all sections", helpers + "\n  // Initialize all sections")

    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Saved {INDEX_PATH}")

    shutil.copy2(INDEX_PATH, DEMO_PATH)
    print(f"Copied to {DEMO_PATH}")

    if ARTIFACT_PATH.parent.exists():
        shutil.copy2(INDEX_PATH, ARTIFACT_PATH)
        print(f"Copied to {ARTIFACT_PATH}")

if __name__ == "__main__":
    patch()
