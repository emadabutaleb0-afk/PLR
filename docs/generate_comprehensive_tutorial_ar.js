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
  await new Promise((r) => setTimeout(r, 1000));
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
  await new Promise((r) => setTimeout(r, 2000));

  // 2. Command Center
  console.log("Capturing 02_command_center...");
  await page.screenshot({ path: path.join(OUT_DIR, "02_command_center.png") });

  // 3. Data Health
  console.log("Capturing 03_data_health...");
  await page.goto("http://localhost:3000/data", { waitUntil: "networkidle2" });
  await new Promise((r) => setTimeout(r, 2000));
  await page.screenshot({ path: path.join(OUT_DIR, "03_data_health.png") });

  // 4. Profit Leakage
  console.log("Capturing 04_profit_leakage...");
  await page.goto("http://localhost:3000/leakage", { waitUntil: "networkidle2" });
  await new Promise((r) => setTimeout(r, 2000));
  await page.screenshot({ path: path.join(OUT_DIR, "04_profit_leakage.png") });

  // 5. Decisions
  console.log("Capturing 05_decisions...");
  await page.goto("http://localhost:3000/decisions", { waitUntil: "networkidle2" });
  await new Promise((r) => setTimeout(r, 2000));
  await page.screenshot({ path: path.join(OUT_DIR, "05_decisions.png") });

  // 6. War Room
  console.log("Capturing 06_war_room...");
  await page.goto("http://localhost:3000/war-room", { waitUntil: "networkidle2" });
  await new Promise((r) => setTimeout(r, 2500));
  await page.screenshot({ path: path.join(OUT_DIR, "06_war_room.png") });

  // 7. Open a decision modal in War Room
  console.log("Capturing 07_decision_detail...");
  try {
    const cardBtn = await page.$('ul li button');
    if (cardBtn) {
      await cardBtn.click();
      await new Promise((r) => setTimeout(r, 1200));
      await page.screenshot({ path: path.join(OUT_DIR, "07_decision_detail.png") });
      // close modal with escape
      await page.keyboard.press("Escape");
      await new Promise((r) => setTimeout(r, 500));
    }
  } catch (err) {
    console.log("Could not capture decision detail modal:", err.message);
  }

  // 8. Time Machine
  console.log("Capturing 08_time_machine...");
  await page.goto("http://localhost:3000/time-machine", { waitUntil: "networkidle2" });
  await new Promise((r) => setTimeout(r, 2000));
  await page.screenshot({ path: path.join(OUT_DIR, "08_time_machine.png") });

  console.log("All screenshots captured successfully!");

  // Convert images to base64 for self-contained HTML
  const toBase64 = (file) => {
    const fPath = path.join(OUT_DIR, file);
    if (!fs.existsSync(fPath)) return "";
    return `data:image/png;base64,${fs.readFileSync(fPath).toString("base64")}`;
  };

  const imgLogin = toBase64("01_login.png");
  const imgCommand = toBase64("02_command_center.png");
  const imgData = toBase64("03_data_health.png");
  const imgLeakage = toBase64("04_profit_leakage.png");
  const imgDecisions = toBase64("05_decisions.png");
  const imgWarRoom = toBase64("06_war_room.png");
  const imgDetail = toBase64("07_decision_detail.png");
  const imgTimeMachine = toBase64("08_time_machine.png");

  const htmlContent = `<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<title>دليل الاستخدام التنفيذي والتشغيلي - منصة Business Gate</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800;900&display=swap');
  @page {
    size: A4 portrait;
    margin: 12mm 14mm 14mm 14mm;
    @bottom-center {
      content: "صفحة " counter(page);
      font-family: 'Cairo', sans-serif;
      font-size: 10px;
      color: #94a3b8;
    }
  }
  * { box-sizing: border-box; }
  body {
    font-family: 'Cairo', -apple-system, BlinkMacSystemFont, "Segoe UI", Tahoma, sans-serif;
    color: #1e293b;
    line-height: 1.6;
    margin: 0;
    padding: 0;
    background: #ffffff;
    font-size: 12.5px;
  }
  
  /* الغلاف */
  .cover {
    height: 100%;
    min-height: 980px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    padding: 30px 20px;
    background: radial-gradient(circle at 90% 10%, rgba(99, 102, 241, 0.12), transparent 50%),
                radial-gradient(circle at 10% 90%, rgba(79, 70, 229, 0.08), transparent 50%),
                #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 20px;
    page-break-after: always;
  }
  .cover-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 2px solid #6366f1;
    padding-bottom: 20px;
  }
  .logo-text {
    font-size: 26px;
    font-weight: 900;
    letter-spacing: 2px;
    color: #1e1b4b;
  }
  .badge-tag {
    background: #4f46e5;
    color: #ffffff;
    padding: 6px 16px;
    border-radius: 9999px;
    font-weight: 700;
    font-size: 12px;
  }
  .cover-body {
    margin: auto 0;
    text-align: center;
  }
  .cover-title {
    font-size: 34px;
    font-weight: 900;
    color: #0f172a;
    line-height: 1.35;
    margin-bottom: 16px;
  }
  .cover-title span {
    color: #4f46e5;
  }
  .cover-sub {
    font-size: 17px;
    color: #475569;
    max-width: 680px;
    margin: 0 auto 30px;
    font-weight: 600;
  }
  .cover-pillars {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 16px;
    text-align: right;
    margin-top: 30px;
  }
  .pillar-card {
    background: #f8fafc;
    border: 1px solid #cbd5e1;
    border-radius: 12px;
    padding: 16px;
  }
  .pillar-card h4 {
    margin: 0 0 6px;
    color: #312e81;
    font-size: 14px;
    font-weight: 700;
  }
  .pillar-card p {
    margin: 0;
    color: #64748b;
    font-size: 11.5px;
  }
  .cover-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-top: 1px solid #e2e8f0;
    padding-top: 16px;
    font-size: 11px;
    color: #64748b;
  }
  
  /* الرأس والقسم */
  .header {
    border-bottom: 2px solid #6366f1;
    padding-bottom: 10px;
    margin-bottom: 16px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .header h2 {
    margin: 0;
    font-size: 20px;
    color: #0f172a;
    font-weight: 800;
  }
  .header .badge {
    background: #eef2ff;
    color: #4338ca;
    padding: 3px 10px;
    border-radius: 9999px;
    font-weight: 700;
    font-size: 11px;
  }
  .section {
    margin-bottom: 18px;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 14px;
    background: #ffffff;
    page-break-inside: avoid;
  }
  .section-title {
    font-size: 15px;
    font-weight: 800;
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
    width: 22px;
    height: 22px;
    background: #4f46e5;
    color: #fff;
    border-radius: 50%;
    font-size: 11px;
    font-weight: 700;
  }
  .callout {
    background: #f0fdf4;
    border-right: 4px solid #16a34a;
    padding: 8px 12px;
    border-radius: 6px;
    margin: 8px 0;
    font-size: 11.5px;
    color: #14532d;
  }
  .callout-warn {
    background: #fffbeb;
    border-right: 4px solid #d97706;
    padding: 8px 12px;
    border-radius: 6px;
    margin: 8px 0;
    font-size: 11.5px;
    color: #78350f;
  }
  .callout-indigo {
    background: #eef2ff;
    border-right: 4px solid #4f46e5;
    padding: 8px 12px;
    border-radius: 6px;
    margin: 8px 0;
    font-size: 11.5px;
    color: #312e81;
  }
  .grid-2 {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
  }
  .grid-3 {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 10px;
  }
  .kpi-box {
    background: #f8fafc;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    padding: 10px;
    text-align: right;
  }
  .kpi-label {
    font-size: 11px;
    color: #64748b;
    font-weight: 600;
    margin-bottom: 3px;
  }
  .kpi-val {
    font-size: 16px;
    font-weight: 800;
    color: #0f172a;
  }
  .img-container {
    margin-top: 10px;
    border-radius: 8px;
    overflow: hidden;
    border: 1px solid #cbd5e1;
    box-shadow: 0 4px 6px -1px rgba(0,0,0,0.06);
    background: #fff;
  }
  .img-container img {
    width: 100%;
    display: block;
  }
  .page-break {
    page-break-after: always;
  }
  .key-badge {
    display: inline-block;
    padding: 2px 7px;
    border-radius: 4px;
    font-size: 10.5px;
    font-weight: 700;
  }
  .crit { background: #fee2e2; color: #b91c1c; }
  .high { background: #ffedd5; color: #c2410c; }
  .med  { background: #fef3c7; color: #b45309; }
  .low  { background: #f1f5f9; color: #475569; }
  .opp  { background: #dcfce7; color: #15803d; }
  
  table.guide-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 11.5px;
    margin: 8px 0;
  }
  table.guide-table th {
    background: #f1f5f9;
    color: #334155;
    text-align: right;
    padding: 6px 10px;
    border: 1px solid #cbd5e1;
    font-weight: 700;
  }
  table.guide-table td {
    padding: 6px 10px;
    border: 1px solid #e2e8f0;
    text-align: right;
  }
</style>
</head>
<body>

  <!-- ======================== صفحة الغلاف ======================== -->
  <div class="cover">
    <div class="cover-header">
      <div class="logo-text">BUSINESS GATE</div>
      <div class="badge-tag">دليل الاستخدام والتشغيل التنفيذي v2.0</div>
    </div>
    
    <div class="cover-body">
      <h1 class="cover-title">
        دليل استخدام المنصة وقراءة<br/>
        <span>النتائج والقرارات التجارية</span>
      </h1>
      <p class="cover-sub">
        دليلك الميداني الشامل لكشف تسرّب الأرباح، تشغيل محركات اتخاذ القرارات، رفع البيانات، وإدارة غرفة العمليات لتحقيق أعلى استرداد مالي مدعوم بالأدلة.
      </p>

      <div class="cover-pillars">
        <div class="pillar-card">
          <h4>1. تشغيل النظام والبيانات</h4>
          <p>تسجيل الدخول، ضبط اسم شركتك، رفع جداول البيانات CSV بالسحب والإفلات، وإدارة الصلاحيات.</p>
        </div>
        <div class="pillar-card">
          <h4>2. قراءة كشف التسرّب</h4>
          <p>فهم الخصومات غير المبررة، المخزون الراكد، المرتجعات، وتكاليف توقف الإنتاج بدقة رقمية.</p>
        </div>
        <div class="pillar-card">
          <h4>3. تنفيذ واعتماد القرارات</h4>
          <p>تفسير مقاييس الثقة والأثر المالي (EGP)، خطط العمل، وإدارة دورة حياة القرار في الـ War Room.</p>
        </div>
      </div>
    </div>

    <div class="cover-footer">
      <div>بيانات الدخول الافتراضية: <b>admin / password</b> · الرابط: <b>http://localhost:3000</b></div>
      <div>نظام معزول 100% · لا تغادر أي بيانات شبكتك الداخلية</div>
    </div>
  </div>

  <!-- ======================== صفحة 1: الدخول، التنقل، والمظهر ======================== -->
  <div class="header">
    <h2>الجزء الأول: تسجيل الدخول وهيكل الواجهة (System Shell)</h2>
    <div class="badge">الوصول والمظهر</div>
  </div>

  <div class="section">
    <div class="section-title"><span class="num">1</span> شاشة الدخول وتبديل اللغة</div>
    <p>تفتح المنصة افتراضيًا باللغة العربية مع دعم فوري لاتجاه القراءة من اليمين إلى اليسار (RTL). يمكنك التبديل بضغطة زر بين العربية والإنجليزية من أي شاشة.</p>
    <div class="grid-2">
      <div class="callout-indigo">
        <b>بيانات الاعتماد الافتراضية:</b><br/>
        • البريد / اسم المستخدم: <code dir="ltr">admin</code><br/>
        • كلمة المرور: <code dir="ltr">password</code>
      </div>
      <div class="callout">
        <b>زر التبديل السريع:</b><br/>
        موجود أعلى يسار شاشة الدخول وفي الشريط العلوي للمنصة، يحفظ اختيارك دائمًا على متصفحك.
      </div>
    </div>
    <div class="img-container">
      <img src="${imgLogin}" alt="شاشة تسجيل الدخول" />
    </div>
  </div>

  <div class="section">
    <div class="section-title"><span class="num">2</span> هيكل الواجهة: القائمة الجانبية والشريط العلوي</div>
    <table class="guide-table">
      <thead>
        <tr>
          <th>العنصر</th>
          <th>الوظيفة والاختصار</th>
          <th>طريقة الاستخدام والتفاعل</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><b>لوحة الأوامر السريعة</b></td>
          <td><code dir="ltr">Ctrl + K</code> أو <code dir="ltr">⌘ + K</code></td>
          <td>بحث فوري عن أي منتج، SKU، مورد، فاتورة، أو الانتقال لأي قسم دون فتح القوائم.</td>
        </tr>
        <tr>
          <td><b>مفتاح المظهر السريع</b></td>
          <td>أيقونة الشمس / القمر (الشريط العلوي)</td>
          <td>التبديل الفوري بضغطة واحدة بين الوضع الداكن (Dark) والفاتح (Light) لغرف الاجتماعات والعروض.</td>
        </tr>
        <tr>
          <td><b>القائمة المصغّرة (Rail)</b></td>
          <td>زر الطي أسفل القائمة الجانبية</td>
          <td>طي القائمة لإعطاء مساحة عرض عريضة للرسوم البيانية وجداول البيانات التحليلية.</td>
        </tr>
      </tbody>
    </table>
  </div>

  <div class="page-break"></div>

  <!-- ======================== صفحة 2: صحة البيانات ورفع الجداول ======================== -->
  <div class="header">
    <h2>الجزء الثاني: صحة البيانات ورفع الجداول وتعديل اسم الشركة</h2>
    <div class="badge">سلامة البيانات</div>
  </div>

  <div class="section">
    <div class="section-title"><span class="num">3</span> رفع الجداول وضبط اسم الشركة (Data Health)</div>
    <p>شاشة <b>سلامة البيانات</b> هي نقطة الانطلاق للتأكد من جاهزية وحداثة الأرقام التي تبنى عليها كل القرارات الاستراتيجية.</p>

    <div class="grid-2">
      <div class="kpi-box">
        <div class="kpi-label">تخصيص اسم الشركة المستهدفة</div>
        <p style="margin: 0; font-size: 11.5px; color: #475569;">
          اكتب اسم شركتك في خانة <b>اسم الشركة المستهدفة</b> ثم اضغط <b>حفظ</b> ليتم ربطه فورًا بجميع اللوحات والتقارير الأسبوعية، أو اضغط <b>اكتشاف تلقائي</b> للعودة للاسم المستخرج من ملفات الأصناف.
        </p>
      </div>
      <div class="kpi-box">
        <div class="kpi-label">رفع جداول البيانات (CSV) بالسحب والإفلات</div>
        <p style="margin: 0; font-size: 11.5px; color: #475569;">
          اسحب ملفات الـ CSV مباشرة وأفلتها داخل الصندوق المخطط، أو اضغط <b>تحديد ملفات CSV</b>، ثم اضغط <b>رفع وتحديث البيانات</b> لبدء المعالجة الفورية وبناء التوصيات.
        </p>
      </div>
    </div>

    <div class="img-container">
      <img src="${imgData}" alt="شاشة صحة البيانات" />
    </div>

    <div class="callout-warn" style="margin-top: 10px;">
      <b>ملاحظة فنية:</b> يمكنك أيضًا نسخ الملفات يدويًا إلى المجلد <code dir="ltr">data/private/</code> داخل مجلد المشروع، ثم الضغط على <b>تحديث البيانات</b> في أي وقت.
    </div>
  </div>

  <div class="page-break"></div>

  <!-- ======================== صفحة 3: مركز القيادة التنفيذي ======================== -->
  <div class="header">
    <h2>الجزء الثالث: قراءة مركز القيادة التنفيذي (Command Center)</h2>
    <div class="badge">الرؤية الاستراتيجية</div>
  </div>

  <div class="section">
    <div class="section-title"><span class="num">4</span> تشريح شاشة مركز القيادة</div>
    <p>تم تصميم مركز القيادة للإجابة على سؤال واحد محدد: <b>أين تخسر الشركة أموالها اليوم، ماذا سيحدث تاليًا، وما هو الإجراء التجاري الواجب اتخاذه الآن؟</b></p>

    <div class="grid-3" style="margin-bottom: 12px;">
      <div class="kpi-box">
        <div class="kpi-label">1. السؤال الاستراتيجي</div>
        <div class="kpi-val" style="font-size: 13px; color: #4338ca;">مخصص باسم شركتك</div>
        <p style="margin: 4px 0 0; font-size: 11px; color: #64748b;">يتغير ديناميكيًا حسب الشركة والبيانات المحملة.</p>
      </div>
      <div class="kpi-box">
        <div class="kpi-label">2. المؤشرات المالية الفورية</div>
        <div class="kpi-val" style="font-size: 13px; color: #b91c1c;">أرقام الخسارة والاسترداد</div>
        <p style="margin: 4px 0 0; font-size: 11px; color: #64748b;">توضيح الأرباح المعرضة للضياع والمبالغ القابلة للاسترداد.</p>
      </div>
      <div class="kpi-box">
        <div class="kpi-label">3. إجراءات اليوم ذات الأولوية</div>
        <div class="kpi-val" style="font-size: 13px; color: #15803d;">أعلى عائد متوقع</div>
        <p style="margin: 4px 0 0; font-size: 11px; color: #64748b;">قائمة مرتبة بأهم القرارات المطلوب مراجعتها فورًا.</p>
      </div>
    </div>

    <div class="img-container">
      <img src="${imgCommand}" alt="مركز القيادة التنفيذي" />
    </div>

    <div class="callout" style="margin-top: 10px;">
      <b>التقرير الأسبوعي:</b> اضغط على زر <b>التقرير الأسبوعي (PDF)</b> أعلى اليسار لتنزيل ملخص تنفيذي كامل معد للطباعة ولعرضه على مجلس الإدارة.
    </div>
  </div>

  <div class="page-break"></div>

  <!-- ======================== صفحة 4: كشف تسرّب الأرباح ======================== -->
  <div class="header">
    <h2>الجزء الرابع: تحليل وتفسير تسرّب الأرباح (Profit Leakage)</h2>
    <div class="badge">تشريح الهدر المالي</div>
  </div>

  <div class="section">
    <div class="section-title"><span class="num">5</span> كيف تقرأ مصادر تسرّب الأرباح؟</div>
    <p>يحلل هذا القسم جميع مصادر الهدر المالي على مدار الـ 12 شهرًا السابقة، ويصنفها إلى 4 قنوات رئيسية:</p>

    <table class="guide-table">
      <thead>
        <tr>
          <th>نوع التسرّب</th>
          <th>المعنى التشغيلي</th>
          <th>كيف يتم احتسابه في محرك المنصة؟</th>
          <th>الإجراء التصحيحي التلقائي</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><b style="color: #e11d48;">الخصومات الزائدة (Discount Leakage)</b></td>
          <td>بيع منتجات بخصم أعلى من النطاق المريح بدون زيادة مبيعات تبرره.</td>
          <td>أي خصم يتجاوز 10% (قابل للتعديل) على أصناف ذات طلب مستقر.</td>
          <td>إعادة التسعير، إيقاف التخفيضات العشوائية، وربط الخصم بنفاد المخزون فقط.</td>
        </tr>
        <tr>
          <td><b style="color: #ea580c;">المخزون الراكد والبطيء (Dead & Excess)</b></td>
          <td>أموال مجمدة في بضاعة مخزنة تغطي أكثر من 180 يومًا دون مبيعات كافية.</td>
          <td>قيمة رأس المال المحبوس في الأصناف التي وتيرة مبيعاتها الحالية لا تبرر بقاءها.</td>
          <td>تسييل فوري للأصناف الراكدة ونقل الكميات للفروع ذات الطلب النشط.</td>
        </tr>
        <tr>
          <td><b style="color: #d97706;">تكاليف المرتجعات والعيوب (Return Costs)</b></td>
          <td>خسائر الشحن العكسي، إعادة التغليف، وتلف المنتجات المرتجعة.</td>
          <td>تحليل أسباب الإرجاع (مقاسات غير دقيقة، عيوب خياطة أو طباعة).</td>
          <td>تعديل جدول المقاسات ومحاسبة مصانع وموردي الأصناف المعيبة.</td>
        </tr>
        <tr>
          <td><b style="color: #7c3aed;">توقف الماكينات والإنتاج (Operational Bottlenecks)</b></td>
          <td>ساعات التشغيل الضائعة وإعادة طباعة الأقمشة التالفة.</td>
          <td>ساعات التوقف غير المخطط وتكلفة الهدر لكل ماكينة ومرحلة.</td>
          <td>إعادة جدولة أوامر الشغل والصيانة الوقائية لتقليل الاختناقات.</td>
        </tr>
      </tbody>
    </table>

    <div class="img-container">
      <img src="${imgLeakage}" alt="شاشة تسرّب الأرباح" />
    </div>
  </div>

  <div class="page-break"></div>

  <!-- ======================== صفحة 5: قراءة وتفسير القرارات والتوصيات ======================== -->
  <div class="header">
    <h2>الجزء الخامس: قراءة وتفسير القرارات (Decisions & Plans)</h2>
    <div class="badge">ذكاء اتخاذ القرار</div>
  </div>

  <div class="section">
    <div class="section-title"><span class="num">6</span> كيف تفكك وتفسر بطاقة القرار التجاري؟</div>
    <p>كل توصية في المنصة ليست مجرد تنبيه، بل هي دراسة جدوى مصغرة متكاملة الأركان تتضمن الآتي:</p>

    <div class="grid-2">
      <div class="section" style="margin-bottom:0; background: #f8fafc;">
        <h4 style="margin: 0 0 6px; color: #1e1b4b; font-size: 13px;">عناصر بطاقة القرار الأساسية:</h4>
        <ul style="margin: 0; padding-right: 18px; font-size: 11.5px; color: #334155;">
          <li><b>الأثر المالي المتوقع (EGP):</b> القيمة المالية التقديرية الصافية التي ستدخل خزانة الشركة عند تنفيذ هذا القرار.</li>
          <li><b>درجة الثقة (Confidence %):</b> نسبة دقة القرار المبنية على حجم البيانات التاريخية المتاحة (كلما زادت البيانات اقتربت من 100%).</li>
          <li><b>المشكلة والسبب الجذري:</b> تشخيص دقيق لما حدث مدعومًا بالأرقام.</li>
          <li><b>الإجراء الواجب اتخاذه:</b> خطوة محددة مثل (نقل 50 قطعة من فرع A إلى فرع B).</li>
        </ul>
      </div>

      <div class="section" style="margin-bottom:0; background: #f8fafc;">
        <h4 style="margin: 0 0 6px; color: #1e1b4b; font-size: 13px;">درجات الأهمية والحرج (Urgency):</h4>
        <div style="font-size: 11px; space-y-2;">
          <p style="margin: 3px 0;"><span class="key-badge crit">CRITICAL (حرج)</span> خسارة أرباح فورية ومستمرة؛ يجب اتخاذ القرار اليوم.</p>
          <p style="margin: 3px 0;"><span class="key-badge high">HIGH (مرتفع)</span> مخاطرة نفاد مخزون وشيكة أو تعارض حملة إعلانية.</p>
          <p style="margin: 3px 0;"><span class="key-badge med">MEDIUM (متوسط)</span> فرصة تحسين هامش أو تسريع دوران الصنف.</p>
          <p style="margin: 3px 0;"><span class="key-badge opp">OPPORTUNITY (فرصة)</span> فرصة توسع وطلب صاعد يمكن استغلاله لتحقيق أرباح إضافية.</p>
        </div>
      </div>
    </div>

    <div class="img-container">
      <img src="${imgDecisions}" alt="شاشة خطط القرارات" />
    </div>

    <div class="callout-indigo" style="margin-top: 10px;">
      <b>أنواع خطط القرارات:</b>
      <b>1. أقصى ربح (Max Profit):</b> لأعلى عائد مالي متوقع · 
      <b>2. الخطة المتوازنة (Balanced):</b> تحييد المخاطر والالتزام بحدود السيولة النقدية · 
      <b>3. أقل مخاطرة (Min Risk):</b> قرارات بنسبة ثقة تتجاوز 60% فقط.
    </div>
  </div>

  <div class="page-break"></div>

  <!-- ======================== صفحة 6: غرفة اتخاذ القرارات (War Room) ======================== -->
  <div class="header">
    <h2>الجزء السادس: غرفة القرارات ومسار التنفيذ (War Room)</h2>
    <div class="badge">إدارة ومتابعة التنفيذ</div>
  </div>

  <div class="section">
    <div class="section-title"><span class="num">7</span> دورة حياة القرار التجاري على لوحة كانبان</div>
    <p>تنتقل القرارات عبر مسار عمل محكم يضمن المساءلة وتحقيق النتائج على أرض الواقع:</p>

    <div class="grid-3" style="margin-bottom: 10px;">
      <div class="kpi-box" style="border-top: 3px solid #64748b;">
        <div class="kpi-label">1. مفتوح (Open)</div>
        <p style="margin: 0; font-size: 11px;">توصيات المحرك في انتظار مراجعة المسؤول.</p>
      </div>
      <div class="kpi-box" style="border-top: 3px solid #3b82f6;">
        <div class="kpi-label">2. معتمد (Approved)</div>
        <p style="margin: 0; font-size: 11px;">تم اعتماده وتعيين مسؤول للبدء في تنفيذه.</p>
      </div>
      <div class="kpi-box" style="border-top: 3px solid #10b981;">
        <div class="kpi-label">3. تم القياس (Measured)</div>
        <p style="margin: 0; font-size: 11px;">تم تنفيذ الإجراء وقياس الربح المسترد الفعلي.</p>
      </div>
    </div>

    <div class="img-container">
      <img src="${imgWarRoom}" alt="غرفة القرارات War Room" />
    </div>

    <div class="callout" style="margin-top: 10px;">
      <b>خاصية السحب والإفلات (Drag & Drop):</b>
      يمكنك سحب كرت القرار بالماوس ونقله مباشرة بين الأعمدة لتغيير حالته من "مفتوح" إلى "معتمد" أو "قيد التنفيذ".
    </div>
  </div>

  ${imgDetail ? `
  <div class="section">
    <div class="section-title"><span class="num">8</span> نافذة تفاصيل القرار والاعتماد (Decision Drawer)</div>
    <p>عند الضغط على أي قرار، تفتح نافذة مراجعة تفصيلية توضح خلفية القرار، التقديرات، ومربع الملاحظات:</p>
    <div class="img-container" style="max-height: 250px; overflow: hidden;">
      <img src="${imgDetail}" alt="تفاصيل القرار" />
    </div>
  </div>
  ` : ''}

  <div class="page-break"></div>

  <!-- ======================== صفحة 7: آلة الزمن والمحاكاة التقديرية ======================== -->
  <div class="header">
    <h2>الجزء السابع: آلة الزمن والمحاكاة التقديرية (Time Machine)</h2>
    <div class="badge">المحاكاة وسيناريوهات المستقبل</div>
  </div>

  <div class="section">
    <div class="section-title"><span class="num">9</span> محاكاة السيناريوهات ومقارنة الفترات التاريخية</div>
    <p>تتيح لك شاشة <b>آلة الزمن</b> محاكاة أثر القرارات التجارية قبل تنفيذها على أرض الواقع، وفهم الفارق المالي بين اتخاذ القرار والتأخر فيه.</p>

    <div class="grid-2">
      <div class="callout-indigo">
        <b>محاكاة ماذا لو (What-If Scenarios):</b><br/>
        اختبار أثر زيادة أو خفض أسعار صنف معين بنسبة محددة على الهامش الإجمالي وكميات الطلب المتوقعة.
      </div>
      <div class="callout">
        <b>المقارنة الزمنية (Timeline Drift):</b><br/>
        مقارنة سلوك طلب المقاسات والمبيعات مع نفس الفترة من العام السابق لاكتشاف التحولات في ذوق العملاء مبكرًا.
      </div>
    </div>

    ${imgTimeMachine ? `
    <div class="img-container">
      <img src="${imgTimeMachine}" alt="آلة الزمن" />
    </div>
    ` : ''}
  </div>

  <div class="section">
    <div class="section-title">ملخص القواعد الذهبية للتشغيل اليومي</div>
    <ul style="margin: 0; padding-right: 18px; font-size: 12px; color: #334155;">
      <li><b>1. ابدأ بمركز القيادة:</b> راجع السؤال الاستراتيجي وأهم 3 قرارات ذات الأولوية فور بدء يوم العمل.</li>
      <li><b>2. حداثة البيانات أساس الدقة:</b> تأكد من رفع جداول مبيعات ومخزون الأسبوع بانتظام عبر شاشة صحة البيانات.</li>
      <li><b>3. قرارات الخصومات أولاً:</b> معالجة الخصومات غير المبررة تعيد أرباحًا نقدية مباشرة وسريعة لخزينة الشركة.</li>
      <li><b>4. سجل النتائج الفعلية:</b> بعد تنفيذ الإجراء في الـ War Room، يراقب النظام الأثر الفعلي ليعرض القيمة المحققة (Realized Value).</li>
    </ul>
  </div>

  <div style="text-align: center; font-size: 11px; color: #64748b; margin-top: 30px; border-top: 1px solid #e2e8f0; padding-top: 12px;">
    منصة BUSINESS GATE · جميع الحقوق محفوظة · دليل الاستخدام التنفيذي والتشغيلي باللغة العربية
  </div>

</body>
</html>`;

  const htmlPath = path.join(__dirname, "guide_ar_comprehensive.html");
  fs.writeFileSync(htmlPath, htmlContent, "utf8");
  console.log("Comprehensive HTML guide created:", htmlPath);

  console.log("Generating high-resolution PDF...");
  const pdfPage = await browser.newPage();
  await pdfPage.goto(`file://${htmlPath}`, { waitUntil: "networkidle0" });
  
  const pdfPath = path.join(__dirname, "BusinessGate_User_Guide_AR.pdf");
  await pdfPage.pdf({
    path: pdfPath,
    format: "A4",
    printBackground: true,
    margin: { top: "10mm", bottom: "10mm", left: "10mm", right: "10mm" },
  });

  console.log("PDF created successfully at:", pdfPath);
  await browser.close();
}

run().catch((err) => {
  console.error("Error in comprehensive capture and export:", err);
  process.exit(1);
});
