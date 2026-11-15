const fs = require('fs');

['docs/index.html', 'docs/BusinessGate_Finance_Interactive_Demo.html', 'index.html'].forEach(filePath => {
  let text = fs.readFileSync(filePath, 'utf8');
  text = text.replace(
    /<div style="margin-top: 12px; font-size: 11\.5px; color: var\(--text-muted\);">\s*🔄 المزامنة الشاملة لجميع الفروع: <b>منذ 3 أيام<\/b> \(جميع الفواتير والمخزون مكتملة الأركان\)\.\s*<\/div>/g,
    '<div id="health-sync-text" style="margin-top: 12px; font-size: 11.5px; color: var(--text-muted);">🔄 حالة المزامنة: <b>لم يتم رفع أي جداول حتى الآن</b></div>'
  );
  fs.writeFileSync(filePath, text, 'utf8');
  console.log('Fixed health sync text in', filePath);
});

const brainPath = 'C:/Users/EMadHamza/.gemini/antigravity/brain/2201ad41-5133-4dab-bb08-4c42bf15a6e7/BusinessGate_Finance_Interactive_Demo.html';
if (fs.existsSync(brainPath)) {
  let bText = fs.readFileSync(brainPath, 'utf8');
  bText = bText.replace(
    /<div style="margin-top: 12px; font-size: 11\.5px; color: var\(--text-muted\);">\s*🔄 المزامنة الشاملة لجميع الفروع: <b>منذ 3 أيام<\/b> \(جميع الفواتير والمخزون مكتملة الأركان\)\.\s*<\/div>/g,
    '<div id="health-sync-text" style="margin-top: 12px; font-size: 11.5px; color: var(--text-muted);">🔄 حالة المزامنة: <b>لم يتم رفع أي جداول حتى الآن</b></div>'
  );
  fs.writeFileSync(brainPath, bText, 'utf8');
  console.log('Fixed health sync text in brainPath');
}
