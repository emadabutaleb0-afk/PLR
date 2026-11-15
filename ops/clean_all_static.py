"""Forensic cleaning of all files:
Zero data, no client name, no pre-selected buttons, clean empty state in pure HTML.
"""
import shutil
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = ROOT / "docs" / "index.html"
DEMO_PATH = ROOT / "docs" / "BusinessGate_Finance_Interactive_Demo.html"
ROOT_INDEX = ROOT / "index.html"
ARTIFACT_PATH = Path(r"C:\Users\EMadHamza\.gemini\antigravity\brain\2201ad41-5133-4dab-bb08-4c42bf15a6e7\BusinessGate_Finance_Interactive_Demo.html")

def clean_all():
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        html = f.read()

    # 1. Clean client name everywhere
    html = html.replace('placeholder="مثال: شركة النصر للملابس الجاهزة"', 'placeholder="اسم المتجر / الفرع (اختياري)"')
    html = html.replace('شركة النصر للملابس الجاهزة', '')

    # 2. Clean Notice banner: remove "البيانات: فواتير ومخزون 12 شهرًا"
    old_banner_badge = """      <div style="background: rgba(255,255,255,0.1); padding: 6px 14px; border-radius: 8px;">
        البيانات: فواتير ومخزون 12 شهرًا
      </div>"""
    new_banner_badge = """      <div id="banner-data-status" style="background: rgba(255,255,255,0.1); padding: 6px 14px; border-radius: 8px;">
        حالة النظام: بانتظار رفع البيانات (NO_DATA)
      </div>"""
    html = html.replace(old_banner_badge, new_banner_badge)

    # 3. Clean Data Health Card in Tab 6
    old_tab6_health = """      <div class="card">
          <div class="card-header">
            <span class="card-title">📋 ملخص سلامة وصحة البيانات (Data Health)</span>
            <span class="badge badge-green">HEALTHY</span>
          </div>
          <div class="grid-3" style="gap: 10px; margin-top: 4px;">
            <div style="text-align: center; background: var(--bg-sunken); border-radius: 10px; padding: 10px;">
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
              </div>
            </div>
            <div id="health-sync-text" style="margin-top: 12px; font-size: 11.5px; color: var(--text-muted);">
              🔄 المزامنة الشاملة لجميع الفروع: <b>منذ 3 أيام</b> (جميع الفواتير والمخزون مكتملة الأركان).
            </div>
          </div>"""

    new_tab6_health = """      <div class="card">
          <div class="card-header">
            <span class="card-title">📋 ملخص سلامة وصحة البيانات (Data Health)</span>
            <span id="health-header-badge" class="badge badge-gray">NO_DATA</span>
          </div>
          <div class="grid-3" style="gap: 10px; margin-top: 4px;">
            <div style="text-align: center; background: var(--bg-sunken); border-radius: 10px; padding: 10px;">
                <div id="health-active-count" style="font-size: 22px; font-weight: 900; color: var(--text-muted);">0</div>
                <div style="font-size: 11px; color: var(--text-muted); font-weight: 700;">جداول نشطة</div>
              </div>
              <div style="text-align: center; background: var(--bg-sunken); border-radius: 10px; padding: 10px;">
                <div id="health-attention-count" style="font-size: 22px; font-weight: 900; color: var(--text-muted);">0</div>
                <div style="font-size: 11px; color: var(--text-muted); font-weight: 700;">تحتاج تحديثًا</div>
              </div>
              <div style="text-align: center; background: var(--bg-sunken); border-radius: 10px; padding: 10px;">
                <div id="health-quality-score" style="font-size: 22px; font-weight: 900; color: var(--text-muted);">0%</div>
                <div style="font-size: 11px; color: var(--text-muted); font-weight: 700;">مؤشر الدقة والجودة</div>
              </div>
            </div>
            <div id="health-sync-text" style="margin-top: 12px; font-size: 11.5px; color: var(--text-muted);">
              🔄 حالة المزامنة: <b>لم يتم رفع أي جداول حتى الآن</b>
            </div>
          </div>"""

    html = html.replace(old_tab6_health, new_tab6_health)

    # 4. In switchScenario, also update banner-data-status
    if "const bStatus = document.getElementById('banner-data-status');" not in html:
        target_switch = "const pName = document.getElementById('current-place-name');"
        repl_switch = """const bStatus = document.getElementById('banner-data-status');
    if (bStatus) bStatus.innerHTML = 'البيانات: تم استيعاب بيانات ' + scen.name;
    const pName = document.getElementById('current-place-name');"""
        html = html.replace(target_switch, repl_switch)

    # In resetToEmptyState, also update banner-data-status
    if "const bStatus = document.getElementById('banner-data-status');\n    if (bStatus) bStatus.innerHTML = 'حالة النظام: بانتظار رفع البيانات (NO_DATA)';" not in html:
        target_reset = "const pName = document.getElementById('current-place-name');"
        repl_reset = """const bStatus = document.getElementById('banner-data-status');
    if (bStatus) bStatus.innerHTML = 'حالة النظام: بانتظار رفع البيانات (NO_DATA)';
    const pName = document.getElementById('current-place-name');"""
        html = html.replace(target_reset, repl_reset)

    # Write out
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Saved cleaned {INDEX_PATH}")

    shutil.copy2(INDEX_PATH, DEMO_PATH)
    shutil.copy2(INDEX_PATH, ROOT_INDEX)
    if ARTIFACT_PATH.parent.exists():
        shutil.copy2(INDEX_PATH, ARTIFACT_PATH)
    print("Copied to all targets successfully")

if __name__ == "__main__":
    clean_all()
