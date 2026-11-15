const fs = require('fs');
const text = fs.readFileSync('docs/index.html', 'utf8');

const forbidden = [
  'شركة النصر',
  'فواتير ومخزون 12 شهرًا',
  'منذ 3 أيام',
  'btn btn-primary" id="btn-scen-superstore"',
  'btn btn-primary" onclick="switchScenario'
];

console.log('=== FORBIDDEN STRINGS (Must all be false) ===');
forbidden.forEach(w => console.log('  ' + w + ' -> ' + text.includes(w)));

const required = [
  'حالة النظام: بانتظار رفع البيانات (NO_DATA)',
  'id="health-header-badge" class="badge badge-gray">NO_DATA',
  'حالة المزامنة: <b>لم يتم رفع أي جداول حتى الآن</b>',
  'id="kpi-risk-val" style="color: var(--text-muted);">-- ج.م',
  'id="health-active-count" style="font-size: 22px; font-weight: 900; color: var(--text-muted);">0'
];

console.log('=== REQUIRED STRINGS (Must all be true) ===');
required.forEach(r => console.log('  ' + r.slice(0, 45) + ' -> ' + text.includes(r)));
