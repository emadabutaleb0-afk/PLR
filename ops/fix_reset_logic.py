"""Fix resetToEmptyState and switchScenario logic cleanly
"""
import shutil
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = ROOT / "docs" / "index.html"
DEMO_PATH = ROOT / "docs" / "BusinessGate_Finance_Interactive_Demo.html"
ROOT_INDEX = ROOT / "index.html"
ARTIFACT_PATH = Path(r"C:\Users\EMadHamza\.gemini\antigravity\brain\2201ad41-5133-4dab-bb08-4c42bf15a6e7\BusinessGate_Finance_Interactive_Demo.html")

def apply_fix():
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        html = f.read()

    # Target in resetToEmptyState
    old_reset_leak = """    // Reset Leakage Progress Box in Tab 1
    // Update Tab 1 KPI Card borders to indicate active data
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

    new_reset_leak = """    // Reset Tab 1 KPI Card borders and badges to gray/border
    const rCard = document.getElementById('kpi-risk-val')?.closest('.card');
    if (rCard) rCard.style.borderRight = '4px solid var(--border)';
    const rcCard = document.getElementById('kpi-recoverable-val')?.closest('.card');
    if (rcCard) rcCard.style.borderRight = '4px solid var(--border)';
    const soCard = document.getElementById('kpi-stockout-val')?.closest('.card');
    if (soCard) soCard.style.borderRight = '4px solid var(--border)';
    const osCard = document.getElementById('kpi-overstock-val')?.closest('.card');
    if (osCard) osCard.style.borderRight = '4px solid var(--border)';

    const rBadge = rCard?.querySelector('.badge');
    if (rBadge) { rBadge.className = 'badge badge-gray'; rBadge.innerText = 'في الانتظار'; }
    const rcBadge = rcCard?.querySelector('.badge');
    if (rcBadge) { rcBadge.className = 'badge badge-gray'; rcBadge.innerText = 'في الانتظار'; }
    const soBadge = soCard?.querySelector('.badge');
    if (soBadge) { soBadge.className = 'badge badge-gray'; soBadge.innerText = 'في الانتظار'; }
    const osBadge = osCard?.querySelector('.badge');
    if (osBadge) { osBadge.className = 'badge badge-gray'; osBadge.innerText = 'في الانتظار'; }

    const tBadge = document.getElementById('leak-total-badge');
    if (tBadge) { tBadge.className = 'badge badge-gray'; tBadge.innerText = '-- ج.م'; }

    const pBox = document.getElementById('leak-progress-box');"""

    html = html.replace(old_reset_leak, new_reset_leak)

    # In switchScenario, insert border & badge activations properly
    target_switch = """    // 4. Update Progress Bars in Tab 1
    const pBox = document.getElementById('leak-progress-box');"""

    repl_switch = """    // Update Tab 1 KPI Card borders and badges to active colored state
    const rCard = document.getElementById('kpi-risk-val')?.closest('.card');
    if (rCard) rCard.style.borderRight = '4px solid var(--red)';
    const rcCard = document.getElementById('kpi-recoverable-val')?.closest('.card');
    if (rcCard) rcCard.style.borderRight = '4px solid var(--green)';
    const soCard = document.getElementById('kpi-stockout-val')?.closest('.card');
    if (soCard) soCard.style.borderRight = '4px solid var(--amber)';
    const osCard = document.getElementById('kpi-overstock-val')?.closest('.card');
    if (osCard) osCard.style.borderRight = '4px solid var(--accent)';

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

    // 4. Update Progress Bars in Tab 1
    const pBox = document.getElementById('leak-progress-box');"""

    html = html.replace(target_switch, repl_switch)

    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    print("Fixed resetToEmptyState and switchScenario")

    shutil.copy2(INDEX_PATH, DEMO_PATH)
    shutil.copy2(INDEX_PATH, ROOT_INDEX)
    if ARTIFACT_PATH.parent.exists():
        shutil.copy2(INDEX_PATH, ARTIFACT_PATH)
    print("Copied to all targets")

if __name__ == "__main__":
    apply_fix()
