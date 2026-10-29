const puppeteer = require("../frontend/node_modules/puppeteer-core");
const fs = require("fs");
const path = require("path");

const CHROME_PATH = "D:\\New folder\\PLR\\chrome\\win64-156.0.8078.73\\chrome-win64\\chrome.exe";
const OUT_DIR = path.join(__dirname, "screenshots");

async function exportPitchPdf() {
  console.log("Preparing Executive Proposal Pitch PDF...");

  const toBase64 = (file) => {
    const fPath = path.join(OUT_DIR, file);
    if (!fs.existsSync(fPath)) return "";
    return `data:image/png;base64,${fs.readFileSync(fPath).toString("base64")}`;
  };

  const imgCommand = toBase64("02_command_center.png");
  const imgLeakage = toBase64("04_profit_leakage.png");
  const imgDecisions = toBase64("05_decisions.png");
  const imgWarRoom = toBase64("06_war_room.png");

  const htmlContent = `<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<title>Executive Proposal Pitch - رادار تسرّب الأرباح</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800;900&display=swap');
  @page {
    size: A4 portrait;
    margin: 10mm 14mm 12mm 14mm;
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
    color: #0f172a;
    line-height: 1.6;
    margin: 0;
    padding: 0;
    background: #ffffff;
    font-size: 12px;
  }

  /* الغلاف التنفيذي الفخم */
  .cover {
    min-height: 980px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    padding: 40px 30px;
    background: radial-gradient(circle at 90% 10%, rgba(99, 102, 241, 0.16), transparent 50%),
                radial-gradient(circle at 10% 90%, rgba(16, 185, 129, 0.12), transparent 50%),
                #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 20px;
    page-break-after: always;
  }
  .cover-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 2px solid #4f46e5;
    padding-bottom: 16px;
  }
  .brand-logo {
    font-size: 24px;
    font-weight: 900;
    letter-spacing: 1.5px;
    color: #1e1b4b;
  }
  .badge-tag {
    background: #1e1b4b;
    color: #a5b4fc;
    padding: 6px 16px;
    border-radius: 9999px;
    font-weight: 700;
    font-size: 11.5px;
  }
  .cover-body {
    margin: auto 0;
    text-align: center;
  }
  .pitch-badge {
    display: inline-block;
    background: #eef2ff;
    color: #4338ca;
    padding: 5px 16px;
    border-radius: 9999px;
    font-size: 12.5px;
    font-weight: 800;
    margin-bottom: 18px;
    border: 1px solid #c7d2fe;
  }
  .cover-title {
    font-size: 32px;
    font-weight: 900;
    color: #0f172a;
    line-height: 1.35;
    margin: 0 0 16px;
  }
  .cover-title span {
    color: #4f46e5;
  }
  .cover-sub {
    font-size: 15.5px;
    color: #334155;
    max-width: 660px;
    margin: 0 auto 28px;
    font-weight: 600;
    line-height: 1.6;
  }
  .cover-formula {
    background: #f8fafc;
    border: 2px dashed #6366f1;
    border-radius: 14px;
    padding: 18px 24px;
    max-width: 620px;
    margin: 0 auto;
    font-size: 14px;
    color: #1e1b4b;
    font-weight: 800;
  }
  .cover-formula span {
    color: #16a34a;
  }
  .cover-pillars {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 14px;
    text-align: right;
    margin-top: 32px;
  }
  .pillar-card {
    background: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 12px;
    padding: 14px;
    box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
  }
  .pillar-card h4 {
    margin: 0 0 6px;
    color: #312e81;
    font-size: 12.5px;
    font-weight: 800;
  }
  .pillar-card p {
    margin: 0;
    color: #64748b;
    font-size: 11px;
    line-height: 1.5;
  }
  .cover-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-top: 1px solid #e2e8f0;
    padding-top: 14px;
    font-size: 11px;
    color: #64748b;
  }

  /* تنسيقات الصفحات الداخلية */
  .header {
    border-bottom: 2px solid #4f46e5;
    padding-bottom: 8px;
    margin-bottom: 14px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .header h2 {
    margin: 0;
    font-size: 18px;
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
    margin-bottom: 14px;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 12px 14px;
    background: #ffffff;
    page-break-inside: avoid;
  }
  .section-title {
    font-size: 14px;
    font-weight: 800;
    color: #1e1b4b;
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
  .callout-green {
    background: #f0fdf4;
    border-right: 4px solid #16a34a;
    padding: 10px 14px;
    border-radius: 6px;
    margin: 8px 0;
    font-size: 11.5px;
    color: #14532d;
    line-height: 1.6;
  }
  .callout-indigo {
    background: #eef2ff;
    border-right: 4px solid #4f46e5;
    padding: 10px 14px;
    border-radius: 6px;
    margin: 8px 0;
    font-size: 11.5px;
    color: #312e81;
    line-height: 1.6;
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
  .kpi-card {
    background: #f8fafc;
    border: 1px solid #cbd5e1;
    border-radius: 10px;
    padding: 10px 12px;
    text-align: right;
  }
  .kpi-title {
    font-size: 11px;
    color: #64748b;
    font-weight: 700;
    margin-bottom: 3px;
  }
  .kpi-value {
    font-size: 16px;
    font-weight: 900;
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
  table.guide-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 11.5px;
    margin: 8px 0;
  }
  table.guide-table th {
    background: #f1f5f9;
    color: #1e293b;
    text-align: right;
    padding: 7px 10px;
    border: 1px solid #cbd5e1;
    font-weight: 800;
  }
  table.guide-table td {
    padding: 7px 10px;
    border: 1px solid #e2e8f0;
    text-align: right;
    vertical-align: top;
  }
</style>
</head>
<body>

  <!-- ======================== صفحة الغلاف ======================== -->
  <div class="cover">
    <div class="cover-header">
      <div class="brand-logo">BUSINESS GATE · PROFIT RADAR</div>
      <div class="badge-tag">EXECUTIVE PROPOSAL PITCH</div>
    </div>

    <div class="cover-body">
      <div class="pitch-badge">عرض استراتيجي ومالي لمجالس الإدارات والرؤساء التنفيذيين (CEO · CFO · Board)</div>
      
      <h1 class="cover-title">
        عرض القيمة المالية:<br/>
        <span>رادار تسرّب الأرباح (Profit Leakage Radar)</span>
      </h1>

      <p class="cover-sub">
        كيف نساعد شركتكم على استرداد مئات الآلاف من الجنيهات المفقودة وزيادة صافي الأرباح فورًا<br/>
        <b>دون إنفاق جنيه إضافي في التسويق والإعلانات، ودون المساس بالتكاليف أو جودة المنتجات.</b>
      </p>

      <div class="cover-formula">
        المعادلة المالية الاستراتيجية:<br/>
        صافي ربح إضافي = <span>استرداد الكاش المحبوس والهدر الخفي</span> داخل فواتيركم ومخزونكم الحالي!
      </div>

      <div class="cover-pillars">
        <div class="pillar-card">
          <h4>صفر تكلفة تسويق إضافية</h4>
          <p>لا نطلب زيادة ميزانيات الإعلانات، بل نوقف ضياع المبيعات الناتجة عن نفاد المقاسات وسوء التوزيع.</p>
        </div>
        <div class="pillar-card">
          <h4>صفر خفض تكاليف أو جودة</h4>
          <p>لا نوصي بتقليص الرواتب أو رداءة الخامات، بل نوقف الهدر في الخصومات العشوائية والأصناف الراكدة.</p>
        </div>
        <div class="pillar-card">
          <h4>أثر نقدي مباشر وسريع</h4>
          <p>قرارات تجارية محددة بالأرقام ومعدل الثقة الإحصائية (Confidence) تترجم إلى أرباح خلال 30 إلى 60 يومًا.</p>
        </div>
      </div>
    </div>

    <div class="cover-footer">
      <div>الجهة المقدمة: فريق استشارات استرداد الأرباح والذكاء التجاري</div>
      <div>نظام تحليلي معزول 100% · متوافق تمامًا مع سرية وخصوصية البيانات</div>
    </div>
  </div>

  <!-- ======================== صفحة 1: الفخ التقليدي مقابل رادار الأرباح ======================== -->
  <div class="header">
    <h2>1. الفخ المالي التقليدي: لماذا تفشل محاولات زيادة الأرباح المعتادة؟</h2>
    <div class="badge">المعضلة والحل</div>
  </div>

  <div class="section">
    <div class="section-title"><span class="num">1</span> الفخ الذي تسقط فيه معظم الشركات عند الرغبة في زيادة الأرباح</div>
    <p>عندما تسعى أي شركة لتعظيم أرباحها، تقع الإدارة عادة في فخ أحد خيارين كلاهما باهظ الثمن ومحفوف بالمخاطر:</p>

    <div class="grid-2">
      <div class="kpi-card" style="border-top: 3px solid #ef4444;">
        <div class="kpi-title" style="color: #b91c1c;">المسار الأول: زيادة ميزانية التسويق والإعلانات</div>
        <p style="margin: 0; font-size: 11px; color: #475569;">
          • تكلفة الاستحواذ على العملاء (CAC) ترتفع باستمرار عبر جميع المنصات.<br/>
          • تصرف ميزانيات ضخمة على إعلانات لمنتجات غير متوفرة أو أوشكت على النفاد في الفروع!<br/>
          • النتيجة: زيادة إيرادات ظاهرية يقابلها تآكل الهوامش وانخفاض العائد (ROAS).
        </p>
      </div>
      <div class="kpi-card" style="border-top: 3px solid #f59e0b;">
        <div class="kpi-title" style="color: #b45309;">المسار الثاني: خفض التكاليف وضغط النفقات</div>
        <p style="margin: 0; font-size: 11px; color: #475569;">
          • تقليل جودة المواد الخام يؤدي لزيادة شكاوى العملاء ومعدلات المرتجعات.<br/>
          • تقليص العمالة أو الصيانة يسبب توقف الماكينات واختناق خطوط الإنتاج.<br/>
          • النتيجة: الإضرار بسمعة العلامة التجارية وتراجع رضا العملاء على المدى الطويل.
        </p>
      </div>
    </div>

    <div class="callout-green">
      <b>الحل الحقيقي (رادار تسرّب الأرباح):</b><br/>
      <b>"الأرباح ليست مفقودة في السوق الخارجي... بل محبوسة ومُهدرة داخل العمليات القائمة بالفعل!"</b><br/>
      تحليل بيانات مبيعاتكم ومخزونكم يثبت أن شركتكم تمتلك كل المقومات لتحقيق هوامش أرباح قياسية فور إيقاف الهدر الخفي في التسعير، الخصومات، وحركات المخزون.
    </div>

    <table class="guide-table">
      <thead>
        <tr>
          <th>وجه المقارنة</th>
          <th>المسار التقليدي (التسويق)</th>
          <th>المسار التقشفي (خفض التكاليف)</th>
          <th>مسار رادار تسرّب الأرباح</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><b>التكلفة الإضافية</b></td>
          <td>مرتفعة جدًا وتدفق نقدي خارج للمنصات</td>
          <td>تكلفة خفية على السمعة والجودة</td>
          <td><b>صفر تكلفة إضافية (Zero Extra Cost)</b></td>
        </tr>
        <tr>
          <td><b>أثر الربحية</b></td>
          <td>تآكل الهوامش ومخاطرة استنزاف</td>
          <td>زيادة المرتجعات وتراجع ولاء العملاء</td>
          <td><b>أرباح صافية تتدفق للخزينة بنسبة 100%</b></td>
        </tr>
        <tr>
          <td><b>سرعة المردود</b></td>
          <td>غير مضمونة وتعتمد على خوارزميات المنصات</td>
          <td>بطيئة وتسبب صدمات داخلية</td>
          <td><b>نتائج قابلة للقياس خلال 30 إلى 60 يومًا</b></td>
        </tr>
      </tbody>
    </table>
  </div>

  <div class="page-break"></div>

  <!-- ======================== صفحة 2: مصادر تسرّب الأرباح الأربعة ======================== -->
  <div class="header">
    <h2>2. أين تتسرب أموال شركتكم اليوم؟ (تشريح الهدر الربحي)</h2>
    <div class="badge">الفجوات الخفية</div>
  </div>

  <div class="section">
    <div class="section-title"><span class="num">2</span> مصادر التسرّب الأربعة الكبرى التي يرصدها الرادار</div>
    <p>يقوم محرك الرادار بمسح 100% من فواتير المبيعات وحركات المخزون ليكشف الفجوات التالية بدقة متناهية:</p>

    <div class="grid-2">
      <div class="section" style="margin-bottom:0; background: #fff1f2; border-color: #fecdd3;">
        <h4 style="margin: 0 0 4px; color: #9f1239; font-size: 12.5px;">1. الخصومات الزائدة غير المبررة (Discount Leakage)</h4>
        <p style="margin: 0; font-size: 11px; color: #4c0519;">
          <b>الحقيقة الرقمية الصادمة:</b> أثبتت التحليلات أن تقديم خصومات تتجاوز 10% إلى 20% على أصناف ذات طلب مستقر <b>لم يرفع حجم المبيعات مطلقًا!</b><br/>
          الشركة ببساطة تقدم أرباحها هدية لعميل كان سيشتري بالسعر الكامل. الرادار يحدد الأصناف التي يجب إيقاف الخصم عليها لحماية الهامش فورًا.
        </p>
      </div>

      <div class="section" style="margin-bottom:0; background: #fff7ed; border-color: #fed7aa;">
        <h4 style="margin: 0 0 4px; color: #9a3412; font-size: 12.5px;">2. المخزون الراكد مقابل المبيعات الضائعة (Trapped Cash)</h4>
        <p style="margin: 0; font-size: 11px; color: #431407;">
          <b>مفارقة المخزون:</b> فرع يخسر مبيعات يوميًا لنفاد المقاسات لديه، بينما فرع آخر أو مستودع يمتلك 150 قطعة راكدة من نفس الصنف تكفي 200 يوم!<br/>
          الرادار يوجه لنقل البضاعة المحبوسة فورًا إلى الفروع النشطة دون الحاجة لإنتاج أو شراء قطعة جديدة واحدة.
        </p>
      </div>
    </div>

    <div class="grid-2" style="margin-top: 10px;">
      <div class="section" style="margin-bottom:0; background: #fefce8; border-color: #fef08a;">
        <h4 style="margin: 0 0 4px; color: #854d0e; font-size: 12.5px;">3. تكاليف المرتجعات واختلال المقاسات (Returns & Fit)</h4>
        <p style="margin: 0; font-size: 11px; color: #422006;">
          المرتجع ليس مجرد بيعة ملغاة؛ إنه تكلفة شحن عكسي وتجميد بضاعة وهدر تغليف.<br/>
          الرادار يحلل إشارات المقاسات التي يتكرر إرجاعها ويربطها بتعديل جدول المقاسات ومحاسبة مصانع وموردي الأقمشة المعيبة.
        </p>
      </div>

      <div class="section" style="margin-bottom:0; background: #f5f3ff; border-color: #ddd6fe;">
        <h4 style="margin: 0 0 4px; color: #5b21b6; font-size: 12.5px;">4. تعارض الحملات الإعلانية مع المخزون (Collisions)</h4>
        <p style="margin: 0; font-size: 11px; color: #2e1065;">
          إطلاق حملات تسويقية ممولة على منتجات لا يتوفر منها سوى مقاسات محدودة يمثل هدرًا كاملًا للميزانية.<br/>
          الرادار يمنع الصرف الإعلاني على الأصناف شحيحة المخزون ويوجهه حصرًا للأصناف عالية الهامش والوفرة.
        </p>
      </div>
    </div>

    <div class="img-container">
      <img src="${imgLeakage}" alt="لوحة كشف تسرّب الأرباح" />
    </div>
  </div>

  <div class="page-break"></div>

  <!-- ======================== صفحة 3: كيف يحول الرادار الهدر إلى كاش؟ ======================== -->
  <div class="header">
    <h2>3. كيف يحوّل الرادار هذا الهدر إلى أرباح نقدية؟ (آلية العمل)</h2>
    <div class="badge">محرك القرارات</div>
  </div>

  <div class="section">
    <div class="section-title"><span class="num">3</span> قرارات تجارية جاهزة للتنفيذ مدعومة بثلاثة أركان صارمة</div>
    <p>نحن لا نكتفي بالتقارير النظرية والرسوم البيانية التقليدية، بل نقدم <b>قرارات وتوصيات تشغيلية محددة</b> تتضمن:</p>

    <div class="grid-3" style="margin-bottom: 10px;">
      <div class="kpi-card">
        <div class="kpi-title">الأثر المالي المتوقع بالجنيه (EGP)</div>
        <p style="margin: 0; font-size: 11px; color: #475569;">كل قرار مصحوب برقم دقيق لصافي العائد المتوقع عند تنفيذه (مثل: استرداد 140,000 ج.م).</p>
      </div>
      <div class="kpi-card">
        <div class="kpi-title">درجة الثقة الإحصائية (Confidence %)</div>
        <p style="margin: 0; font-size: 11px; color: #475569;">نسبة دقة مبنية على حجم وتاريخ البيانات تضمن عدم اتخاذ خطوات تخمينية أو غير مؤكدة.</p>
      </div>
      <div class="kpi-card">
        <div class="kpi-title">إجراء تنفيذي محدد بالاسم والفرع</div>
        <p style="margin: 0; font-size: 11px; color: #475569;">توجيه صريح: (إلغاء الخصم على الصنف X · نقل 40 قطعة من فرع A إلى B · تصريف مقاس L).</p>
      </div>
    </div>

    <div class="img-container">
      <img src="${imgDecisions}" alt="شاشة خطط القرارات" />
    </div>

    <div class="callout-indigo" style="margin-top: 10px;">
      <b>ثلاث خطط مجمعة تلائم استراتيجية شركتكم:</b><br/>
      • <b>خطة أقصى ربح (Max Profit):</b> لأعلى استرداد مالي فوري للشركات ذات السيولة المريحة.<br/>
      • <b>الخطة المتوازنة (Balanced):</b> تحييد المخاطر والالتزام التام بالحدود النقدية المتاحة للشركة.<br/>
      • <b>خطة أقل مخاطرة (Min Risk):</b> قرارات بنسبة ثقة إحصائية تتجاوز 60% لضمان الأمان التام.
    </div>
  </div>

  <div class="page-break"></div>

  <!-- ======================== صفحة 4: غرفة العمليات وخطة الشراكة ======================== -->
  <div class="header">
    <h2>4. غرفة اتخاذ القرارات وإثبات القيمة (War Room & Realized Value)</h2>
    <div class="badge">الشفافية والتنفيذ</div>
  </div>

  <div class="section">
    <div class="section-title"><span class="num">4</span> لا نتركك مع التوصيات.. بل نقيس الأرباح المحققة فعليًا!</div>
    <p>الميزة التنافسية الأهم في خدمتنا هي <b>غرفة العمليات (War Room) ومحرك إثبات القيمة</b>، حيث نتابع مسار القرار حتى يدخل أثره المالي خزينتكم:</p>

    <div class="img-container">
      <img src="${imgWarRoom}" alt="غرفة اتخاذ القرارات War Room" />
    </div>

    <div class="grid-2" style="margin-top: 10px;">
      <div class="callout-green" style="margin: 0;">
        <b>دورة حياة القرار المضمونة:</b><br/>
        1. <b>مفتوح (Open):</b> يراجعه المسؤول في شركتك ويعتمده.<br/>
        2. <b>قيد التنفيذ (In Progress):</b> يبدأ تنفيذه في الفروع أو المخازن.<br/>
        3. <b>قيد القياس (Measuring):</b> يراقب النظام المبيعات والأرباح بعد الإجراء.<br/>
        4. <b>تم القياس (Measured):</b> تسجيل الأرباح الصافية المحققة فعليًا.
      </div>

      <div class="callout-indigo" style="margin: 0;">
        <b>مبدأ الشفافية المطلقة (Audit Trail):</b><br/>
        • توثيق اسم كل من اعتمد القرار وتاريخ التنفيذ بدقة.<br/>
        • تقارير مقارنة تثبت كم دخل خزانة شركتكم قبل وبعد تطبيق كل قرار.<br/>
        • دليل دامغ لمجلس الإدارة على جدوى وعائد الاستثمار.
      </div>
    </div>
  </div>

  <div class="section">
    <div class="section-title"><span class="num">5</span> كيف نبدأ العمل معًا؟ (خطة الشراكة في 3 خطوات)</div>
    <table class="guide-table">
      <thead>
        <tr>
          <th>المرحلة</th>
          <th>المدة الزمنية</th>
          <th>ما نقدمه لشركتكم</th>
          <th>المطلوب من شركتكم</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><b>1. الفحص المالي الاستكشافي (Audit)</b></td>
          <td>3 إلى 5 أيام عمل</td>
          <td>تحليل شامل لفواتير ومخزون آخر 12 شهرًا، وتقديم تقرير مفصل بمبالغ التسرّب المقدرة بالجنيه.</td>
          <td>تزويدنا بنسخة مشفرة من بيانات المبيعات والمخزون السابقة.</td>
        </tr>
        <tr>
          <td><b>2. تشغيل رادار القرارات (Activation)</b></td>
          <td>أسبوع واحد</td>
          <td>تثبيت المنصة في بيئتكم، تدريب فريق الإدارة على شاشات مركز القيادة وغرفة العمليات.</td>
          <td>جلسة عمل واحدة لاعتماد خطة القرارات الأولى (Balanced Plan).</td>
        </tr>
        <tr>
          <td><b>3. جني واسترداد الأرباح (Recovery)</b></td>
          <td>شهريًا / ربع سنويًا</td>
          <td>متابعة تنفيذ التوصيات، قياس القيمة المستردة أسبوعيًا، وتحديث تقارير مجلس الإدارة.</td>
          <td>تنفيذ الإجراءات المتفق عليها في الفروع وقنوات البيع.</td>
        </tr>
      </tbody>
    </table>
  </div>

  <div style="text-align: center; margin-top: 25px; border-top: 2px solid #4f46e5; padding-top: 15px;">
    <h3 style="margin: 0 0 6px; color: #1e1b4b; font-size: 15px;">هل أنتم مستعدون لاسترداد الأرباح المحبوسة في شركتكم؟</h3>
    <p style="margin: 0; color: #475569; font-size: 11.5px;">يسعدنا عقد جلسة عمل استكشافية مجانية لعرض محاكاة تفاعلية على بيانات تجريبية تثبت حجم العائد المالي المتوقع لشركتكم.</p>
  </div>

</body>
</html>`;

  const htmlPath = path.join(__dirname, "Executive_Proposal_Pitch.html");
  fs.writeFileSync(htmlPath, htmlContent, "utf8");
  console.log("Pitch HTML created:", htmlPath);

  const browser = await puppeteer.launch({
    executablePath: CHROME_PATH,
    headless: "new",
    args: ["--no-sandbox", "--disable-setuid-sandbox"],
  });

  const pdfPage = await browser.newPage();
  await pdfPage.goto(`file://${htmlPath}`, { waitUntil: "networkidle0" });

  const pdfPath = path.join(__dirname, "Executive_Proposal_Pitch.pdf");
  await pdfPage.pdf({
    path: pdfPath,
    format: "A4",
    printBackground: true,
    margin: { top: "8mm", bottom: "8mm", left: "10mm", right: "10mm" },
  });

  console.log("PDF generated successfully at:", pdfPath);
  await browser.close();
}

exportPitchPdf().catch((err) => {
  console.error("Error generating pitch PDF:", err);
  process.exit(1);
});
