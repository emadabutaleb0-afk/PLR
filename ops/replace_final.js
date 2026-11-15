const fs = require('fs');

['docs/index.html', 'docs/BusinessGate_Finance_Interactive_Demo.html', 'index.html'].forEach(filePath => {
  let text = fs.readFileSync(filePath, 'utf8');
  // Normalize CRLF to LF
  text = text.replace(/\r\n/g, '\n');

  text = text.replace(
    /<div style="font-weight: 800; font-size: 13px; background: rgba\(255,255,255,0\.15\); padding: 6px 14px; border-radius: 8px;">\s*البيانات:\s*فواتير ومخزون 12 شهرًا\s*<\/div>/g,
    '<div id="banner-data-status" style="font-weight: 800; font-size: 13px; background: rgba(255,255,255,0.15); padding: 6px 14px; border-radius: 8px;">حالة النظام: بانتظار رفع البيانات (NO_DATA)</div>'
  );

  text = text.replace(
    /<div style="margin-top: 12px; font-size: 11\.5px; color: var\(--text-muted\);">\s*🔄 المزامنة الشاملة لجميع الفروع: <b>منذ 3 أيام<\/b>.*?<\/div>/g,
    '<div id="health-sync-text" style="margin-top: 12px; font-size: 11.5px; color: var(--text-muted);">🔄 حالة المزامنة: <b>لم يتم رفع أي جداول حتى الآن</b></div>'
  );

  text = text.replace(/شركة النصر للملابس الجاهزة/g, '');
  text = text.replace(/مثال: شركة النصر/g, 'اسم المتجر / الفرع');

  fs.writeFileSync(filePath, text, 'utf8');
  console.log('Processed', filePath);
});

const brainPath = 'C:/Users/EMadHamza/.gemini/antigravity/brain/2201ad41-5133-4dab-bb08-4c42bf15a6e7/BusinessGate_Finance_Interactive_Demo.html';
if (fs.existsSync(brainPath)) {
  let bText = fs.readFileSync(brainPath, 'utf8').replace(/\r\n/g, '\n');
  bText = bText.replace(
    /<div style="font-weight: 800; font-size: 13px; background: rgba\(255,255,255,0\.15\); padding: 6px 14px; border-radius: 8px;">\s*البيانات:\s*فواتير ومخزون 12 شهرًا\s*<\/div>/g,
    '<div id="banner-data-status" style="font-weight: 800; font-size: 13px; background: rgba(255,255,255,0.15); padding: 6px 14px; border-radius: 8px;">حالة النظام: بانتظار رفع البيانات (NO_DATA)</div>'
  );
  bText = bText.replace(
    /<div style="margin-top: 12px; font-size: 11\.5px; color: var\(--text-muted\);">\s*🔄 المزامنة الشاملة لجميع الفروع: <b>منذ 3 أيام<\/b>.*?<\/div>/g,
    '<div id="health-sync-text" style="margin-top: 12px; font-size: 11.5px; color: var(--text-muted);">🔄 حالة المزامنة: <b>لم يتم رفع أي جداول حتى الآن</b></div>'
  );
  bText = bText.replace(/شركة النصر للملابس الجاهزة/g, '');
  fs.writeFileSync(brainPath, bText, 'utf8');
  console.log('Processed brainPath');
}
