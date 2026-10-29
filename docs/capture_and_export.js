const puppeteer = require("../frontend/node_modules/puppeteer-core");
const fs = require("fs");
const path = require("path");

const CHROME_PATH = "D:\\New folder\\PLR\\chrome\\win64-156.0.8078.73\\chrome-win64\\chrome.exe";
const OUT_DIR = path.join(__dirname, "screenshots");
if (!fs.existsSync(OUT_DIR)) fs.mkdirSync(OUT_DIR, { recursive: true });

async function run() {
  console.log("Launching Chrome...");
  const browser = await puppeteer.launch({
    executablePath: CHROME_PATH,
    headless: "new",
    args: [
      "--no-sandbox",
      "--disable-setuid-sandbox",
      "--window-size=1440,900"
    ],
    defaultViewport: { width: 1440, height: 900, deviceScaleFactor: 1.5 },
  });

  const page = await browser.newPage();

  // 1. Login Page
  console.log("Capturing 01_login...");
  await page.goto("http://localhost:3000/login", { waitUntil: "networkidle2" });
  await page.evaluate(() => {
    localStorage.setItem("mb_lang", "ar");
  });
  await page.reload({ waitUntil: "networkidle2" });
  await page.screenshot({ path: path.join(OUT_DIR, "01_login.png") });

  // Perform Login
  console.log("Logging in as admin...");
  await page.type('#email', "admin");
  await page.type('#pw', "password");
  await page.evaluate(() => {
    document.querySelector("form").requestSubmit();
  });
  await new Promise((r) => setTimeout(r, 3000));

  // Ensure Arabic language
  await page.evaluate(() => {
    localStorage.setItem("mb_lang", "ar");
  });
  await page.reload({ waitUntil: "networkidle2" });
  await new Promise((r) => setTimeout(r, 1500));

  // 2. Command Center
  console.log("Capturing 02_command_center...");
  await page.screenshot({ path: path.join(OUT_DIR, "02_command_center.png") });

  // 3. Data Health
  console.log("Capturing 03_data_health...");
  await page.goto("http://localhost:3000/data", { waitUntil: "networkidle2" });
  await new Promise((r) => setTimeout(r, 1500));
  await page.screenshot({ path: path.join(OUT_DIR, "03_data_health.png") });

  // 4. Profit Leakage
  console.log("Capturing 04_profit_leakage...");
  await page.goto("http://localhost:3000/leakage", { waitUntil: "networkidle2" });
  await new Promise((r) => setTimeout(r, 1500));
  await page.screenshot({ path: path.join(OUT_DIR, "04_profit_leakage.png") });

  // 5. Decisions
  console.log("Capturing 05_decisions...");
  await page.goto("http://localhost:3000/decisions", { waitUntil: "networkidle2" });
  await new Promise((r) => setTimeout(r, 1500));
  await page.screenshot({ path: path.join(OUT_DIR, "05_decisions.png") });

  // 6. War Room
  console.log("Capturing 06_war_room...");
  await page.goto("http://localhost:3000/war-room", { waitUntil: "networkidle2" });
  await new Promise((r) => setTimeout(r, 1500));
  await page.screenshot({ path: path.join(OUT_DIR, "06_war_room.png") });

  console.log("Screenshots captured successfully!");

  // Convert images to base64 for self-contained HTML
  const toBase64 = (file) => {
    const fPath = path.join(OUT_DIR, file);
    return `data:image/png;base64,${fs.readFileSync(fPath).toString("base64")}`;
  };

  const imgLogin = toBase64("01_login.png");
  const imgCommand = toBase64("02_command_center.png");
  const imgData = toBase64("03_data_health.png");
  const imgLeakage = toBase64("04_profit_leakage.png");
  const imgDecisions = toBase64("05_decisions.png");

  const htmlContent = `<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<title>دليل استخدام منصة Business Gate</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800&display=swap');
  @page {
    size: A4 portrait;
    margin: 15mm 15mm 15mm 15mm;
  }
  * { box-sizing: border-box; }
  body {
    font-family: 'Cairo', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    color: #1e293b;
    line-height: 1.6;
    margin: 0;
    padding: 0;
    background: #ffffff;
    font-size: 13px;
  }
  .header {
    border-bottom: 2px solid #6366f1;
    padding-bottom: 14px;
    margin-bottom: 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .header h1 {
    margin: 0;
    font-size: 24px;
    color: #0f172a;
    font-weight: 800;
  }
  .header .badge {
    background: #eef2ff;
    color: #4338ca;
    padding: 4px 12px;
    border-radius: 9999px;
    font-weight: 700;
    font-size: 12px;
  }
  .section {
    page-break-inside: avoid;
    margin-bottom: 24px;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 16px;
    background: #f8fafc;
  }
  .section-title {
    font-size: 16px;
    font-weight: 700;
    color: #312e81;
    margin-top: 0;
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .num {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 24px;
    height: 24px;
    background: #4f46e5;
    color: #fff;
    border-radius: 50%;
    font-size: 12px;
  }
  .meta-box {
    background: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    padding: 10px 14px;
    margin-bottom: 12px;
    display: flex;
    flex-wrap: wrap;
    gap: 16px;
    font-size: 12px;
  }
  .meta-item b { color: #0f172a; }
  .img-container {
    margin-top: 10px;
    border-radius: 8px;
    overflow: hidden;
    border: 1px solid #cbd5e1;
    box-shadow: 0 4px 6px -1px rgba(0,0,0,0.07);
    background: #fff;
  }
  .img-container img {
    width: 100%;
    display: block;
  }
  .page-break {
    page-break-after: always;
  }
  .footer {
    text-align: center;
    font-size: 11px;
    color: #64748b;
    margin-top: 20px;
  }
</style>
</head>
<body>

  <!-- صفحة 1: المقدمة والدخول ومركز القيادة -->
  <div class="header">
    <div>
      <h1>بوابة الأعمال (Business Gate)</h1>
      <p style="margin: 3px 0 0; color: #64748b; font-size: 12px;">دليل المستخدم التنفيذي لكشف تسرّب الأرباح واتخاذ القرارات التجارية</p>
    </div>
    <div class="badge">النسخة العربية · الإصدار المحدث</div>
  </div>

  <div class="meta-box">
    <div class="meta-item"><b>رابط المنصة:</b> <span dir="ltr">http://localhost:3000</span></div>
    <div class="meta-item"><b>اسم المستخدم:</b> <code dir="ltr" style="background:#e2e8f0; padding:2px 6px; border-radius:4px;">admin</code></div>
    <div class="meta-item"><b>كلمة المرور:</b> <code dir="ltr" style="background:#e2e8f0; padding:2px 6px; border-radius:4px;">password</code></div>
  </div>

  <div class="section">
    <div class="section-title"><span class="num">1</span> شاشة تسجيل الدخول واللغة</div>
    <p style="margin: 0 0 8px;">تفتح المنصة تلقائيًا باللغة العربية مع دعم كامل للاتجاه من اليمين لليسار (RTL). يمكن التبديل بين العربية والإنجليزية في أي وقت من زر اللغة بالشريط العلوي.</p>
    <div class="img-container">
      <img src="${imgLogin}" alt="شاشة الدخول" />
    </div>
  </div>

  <div class="section">
    <div class="section-title"><span class="num">2</span> مركز القيادة التنفيذي (Command Center)</div>
    <p style="margin: 0 0 8px;">يعرض السؤال الاستراتيجي الديناميكي باسم الشركة المستهدفة المكتشفة تلقائيًا من البيانات، مع مؤشرات الربح المعرض للخطر، والأرباح القابلة للاسترداد، وأهم القرارات الفورية.</p>
    <div class="img-container">
      <img src="${imgCommand}" alt="مركز القيادة" />
    </div>
  </div>

  <div class="page-break"></div>

  <!-- صفحة 2: صحة البيانات وتسرّب الأرباح والقرارات -->
  <div class="section">
    <div class="section-title"><span class="num">3</span> صحة البيانات ورفع الجداول وتعديل اسم الشركة</div>
    <p style="margin: 0 0 8px;">
      <b>اسم الشركة المستهدفة:</b> يمكنك كتابة اسم شركتك في الخانة المخصصة واضغط <b>حفظ</b> ليتم تحديثه فوريًا، أو الضغط على <b>اكتشاف تلقائي</b> للعودة للاسم المستخرج من ملفات المنتجات.<br/>
      <b>رفع الجداول:</b> اضغط على <b>تحديد ملفات CSV</b> ثم <b>رفع وتحديث البيانات</b> لتحديث الحسابات مباشرة من المتصفح، أو انسخ الملفات إلى <code dir="ltr">data/private/</code>.
    </p>
    <div class="img-container">
      <img src="${imgData}" alt="صحة البيانات ورفع الجداول" />
    </div>
  </div>

  <div class="section">
    <div class="section-title"><span class="num">4</span> لوحة كشف تسرّب الأرباح (Profit Leakage)</div>
    <p style="margin: 0 0 8px;">تحليل شامل لجميع مصادر تسرب الأرباح خلال آخر 12 شهرًا: الخصومات الزائدة عن النطاق المريح، تكلفة البضائع الراكدة، تكاليف المرتجعات، وتوقف الماكينات.</p>
    <div class="img-container">
      <img src="${imgLeakage}" alt="تسرّب الأرباح" />
    </div>
  </div>

  <div class="section">
    <div class="section-title"><span class="num">5</span> محرك القرارات واسترداد الأرباح (Decisions)</div>
    <p style="margin: 0 0 8px;">توصيات عملية مرقمة ومدرجة حسب الأثر المالي المتوقع (بالجنيه المصري) مع مستوى الثقة، وإمكانية المراجعة والاعتماد المباشر.</p>
    <div class="img-container">
      <img src="${imgDecisions}" alt="شاشة القرارات" />
    </div>
  </div>

  <div class="footer">
    تم إنشاء هذا الدليل آليًا لمنصة Business Gate · جميع العمليات تتم محليًا 100% داخل بيئة العمل
  </div>

</body>
</html>`;

  const htmlPath = path.join(__dirname, "guide_ar.html");
  fs.writeFileSync(htmlPath, htmlContent, "utf8");
  console.log("HTML guide created:", htmlPath);

  console.log("Generating PDF from HTML...");
  const pdfPage = await browser.newPage();
  await pdfPage.goto(`file://${htmlPath}`, { waitUntil: "networkidle0" });
  const pdfPath = path.join(__dirname, "BusinessGate_User_Guide_AR.pdf");
  await pdfPage.pdf({
    path: pdfPath,
    format: "A4",
    printBackground: true,
    margin: { top: "12mm", bottom: "12mm", left: "12mm", right: "12mm" },
  });

  console.log("PDF created successfully at:", pdfPath);
  await browser.close();
}

run().catch((err) => {
  console.error("Error in capture and export:", err);
  process.exit(1);
});
