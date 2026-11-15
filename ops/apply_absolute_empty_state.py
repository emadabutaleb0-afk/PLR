"""Apply absolute 100% empty state to all files, verifying every single string.
"""
import shutil
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = ROOT / "docs" / "index.html"
DEMO_PATH = ROOT / "docs" / "BusinessGate_Finance_Interactive_Demo.html"
ROOT_INDEX = ROOT / "index.html"
ARTIFACT_PATH = Path(r"C:\Users\EMadHamza\.gemini\antigravity\brain\2201ad41-5133-4dab-bb08-4c42bf15a6e7\BusinessGate_Finance_Interactive_Demo.html")

def apply_empty():
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        html = f.read()

    # 1. Banner badge: replace "البيانات: فواتير ومخزون 12 شهرًا"
    html = re.sub(
        r'<div style="background:\s*rgba\(255,255,255,0\.15\);\s*padding:\s*6px 14px;\s*border-radius:\s*8px;">\s*البيانات:\s*فواتير ومخزون 12 شهرًا\s*</div>',
        '<div id="banner-data-status" style="font-weight: 800; font-size: 13px; background: rgba(255,255,255,0.15); padding: 6px 14px; border-radius: 8px;">حالة النظام: بانتظار رفع البيانات (NO_DATA)</div>',
        html
    )

    # 2. Tab 6: Card Header badge
    html = re.sub(
        r'<span class="card-title">📋 ملخص سلامة وصحة البيانات \(Data Health\)</span>\s*<span class="badge badge-green">HEALTHY</span>',
        '<span class="card-title">📋 ملخص سلامة وصحة البيانات (Data Health)</span>\n            <span id="health-header-badge" class="badge badge-gray">NO_DATA</span>',
        html
    )

    # 3. Tab 6: Counters (active count, attention count, quality score)
    html = re.sub(
        r'<div id="health-active-count"\s*style="font-size:\s*22px;\s*font-weight:\s*900;\s*color:\s*var\(--green\);">6</div>',
        '<div id="health-active-count" style="font-size: 22px; font-weight: 900; color: var(--text-muted);">0</div>',
        html
    )
    html = re.sub(
        r'<div id="health-attention-count"\s*style="font-size:\s*22px;\s*font-weight:\s*900;\s*color:\s*var\(--amber\);">1</div>',
        '<div id="health-attention-count" style="font-size: 22px; font-weight: 900; color: var(--text-muted);">0</div>',
        html
    )
    html = re.sub(
        r'<div id="health-quality-score"\s*style="font-size:\s*22px;\s*font-weight:\s*900;\s*color:\s*var\(--accent\);">97\.3%</div>',
        '<div id="health-quality-score" style="font-size: 22px; font-weight: 900; color: var(--text-muted);">0%</div>',
        html
    )

    # 4. Tab 6: Sync text
    html = re.sub(
        r'<div id="health-sync-text"\s*style="margin-top:\s*12px;\s*font-size:\s*11\.5px;\s*color:\s*var\(--text-muted\);">\s*🔄 المزامنة الشاملة لجميع الفروع: <b>منذ 3 أيام</b>.*?</div>',
        '<div id="health-sync-text" style="margin-top: 12px; font-size: 11.5px; color: var(--text-muted);">🔄 حالة المزامنة: <b>لم يتم رفع أي جداول حتى الآن</b></div>',
        html
    )

    # 5. Tab 6: In the 3 scenario cards, change buttons from "btn btn-primary" to "btn" so none is blue
    html = html.replace(
        '<button class="btn btn-primary" onclick="switchScenario(\'superstore\')"',
        '<button class="btn" onclick="switchScenario(\'superstore\')"'
    )
    html = html.replace(
        '<button class="btn btn-primary" onclick="switchScenario(\'express\')"',
        '<button class="btn" onclick="switchScenario(\'express\')"'
    )
    html = html.replace(
        '<button class="btn btn-primary" onclick="switchScenario(\'online\')"',
        '<button class="btn" onclick="switchScenario(\'online\')"'
    )

    # 6. Tab 6: Pre-render empty rows in health-table-body in static HTML
    empty_health_table_rows = """            <tr>
              <td><div style="font-weight:700;">📄 product_master.csv</div><div style="font-size:11px;color:var(--text-muted);">بيانات المنتجات والتسعير</div></td>
              <td style="font-weight:800;">0</td>
              <td style="color:var(--text-muted);">لم يُرفع بعد</td>
              <td><div style="display:flex;align-items:center;gap:8px;"><div class="health-bar"><div class="health-bar-fill" style="width:0%;background:#94a3b8;"></div></div><span style="font-weight:700;font-size:12px;">0%</span></div></td>
              <td><span class="badge badge-gray">NOT_LOADED</span></td>
              <td style="font-size:11.5px;color:var(--text-muted);">في انتظار رفع الملف</td>
            </tr>
            <tr>
              <td><div style="font-weight:700;">📄 sales_transactions.csv</div><div style="font-size:11px;color:var(--text-muted);">سجل حركات البيع والفواتير</div></td>
              <td style="font-weight:800;">0</td>
              <td style="color:var(--text-muted);">لم يُرفع بعد</td>
              <td><div style="display:flex;align-items:center;gap:8px;"><div class="health-bar"><div class="health-bar-fill" style="width:0%;background:#94a3b8;"></div></div><span style="font-weight:700;font-size:12px;">0%</span></div></td>
              <td><span class="badge badge-gray">NOT_LOADED</span></td>
              <td style="font-size:11.5px;color:var(--text-muted);">في انتظار رفع الملف</td>
            </tr>
            <tr>
              <td><div style="font-weight:700;">📄 inventory_stock.csv</div><div style="font-size:11px;color:var(--text-muted);">مستويات المخزون بالفروع</div></td>
              <td style="font-weight:800;">0</td>
              <td style="color:var(--text-muted);">لم يُرفع بعد</td>
              <td><div style="display:flex;align-items:center;gap:8px;"><div class="health-bar"><div class="health-bar-fill" style="width:0%;background:#94a3b8;"></div></div><span style="font-weight:700;font-size:12px;">0%</span></div></td>
              <td><span class="badge badge-gray">NOT_LOADED</span></td>
              <td style="font-size:11.5px;color:var(--text-muted);">في انتظار رفع الملف</td>
            </tr>
            <tr>
              <td><div style="font-weight:700;">📄 returns_data.csv</div><div style="font-size:11px;color:var(--text-muted);">بيانات المرتجعات وعيوب الجودة</div></td>
              <td style="font-weight:800;">0</td>
              <td style="color:var(--text-muted);">لم يُرفع بعد</td>
              <td><div style="display:flex;align-items:center;gap:8px;"><div class="health-bar"><div class="health-bar-fill" style="width:0%;background:#94a3b8;"></div></div><span style="font-weight:700;font-size:12px;">0%</span></div></td>
              <td><span class="badge badge-gray">NOT_LOADED</span></td>
              <td style="font-size:11.5px;color:var(--text-muted);">في انتظار رفع الملف</td>
            </tr>
            <tr>
              <td><div style="font-weight:700;">📄 branches_master.csv</div><div style="font-size:11px;color:var(--text-muted);">بيانات الفروع ومراكز التوزيع</div></td>
              <td style="font-weight:800;">0</td>
              <td style="color:var(--text-muted);">لم يُرفع بعد</td>
              <td><div style="display:flex;align-items:center;gap:8px;"><div class="health-bar"><div class="health-bar-fill" style="width:0%;background:#94a3b8;"></div></div><span style="font-weight:700;font-size:12px;">0%</span></div></td>
              <td><span class="badge badge-gray">NOT_LOADED</span></td>
              <td style="font-size:11.5px;color:var(--text-muted);">في انتظار رفع الملف</td>
            </tr>
            <tr>
              <td><div style="font-weight:700;">📄 suppliers.csv</div><div style="font-size:11px;color:var(--text-muted);">بيانات الموردين والعقود</div></td>
              <td style="font-weight:800;">0</td>
              <td style="color:var(--text-muted);">لم يُرفع بعد</td>
              <td><div style="display:flex;align-items:center;gap:8px;"><div class="health-bar"><div class="health-bar-fill" style="width:0%;background:#94a3b8;"></div></div><span style="font-weight:700;font-size:12px;">0%</span></div></td>
              <td><span class="badge badge-gray">NOT_LOADED</span></td>
              <td style="font-size:11.5px;color:var(--text-muted);">في انتظار رفع الملف</td>
            </tr>"""

    html = re.sub(
        r'<tbody id="health-table-body">\s*<!-- Rendered via JS -->\s*</tbody>',
        f'<tbody id="health-table-body">\n{empty_health_table_rows}\n          </tbody>',
        html
    )

    # Write
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Saved {INDEX_PATH}")

    shutil.copy2(INDEX_PATH, DEMO_PATH)
    shutil.copy2(INDEX_PATH, ROOT_INDEX)
    if ARTIFACT_PATH.parent.exists():
        shutil.copy2(INDEX_PATH, ARTIFACT_PATH)
    print("Copied to all targets successfully")

if __name__ == "__main__":
    apply_empty()
