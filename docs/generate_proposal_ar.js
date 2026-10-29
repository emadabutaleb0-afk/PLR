const puppeteer = require("../frontend/node_modules/puppeteer-core");
const fs = require("fs");
const path = require("path");

const CHROME_PATH = "D:\\New folder\\PLR\\chrome\\win64-156.0.8078.73\\chrome-win64\\chrome.exe";
const OUT_DIR = path.join(__dirname, "screenshots");

async function run() {
  console.log("Generating Executive Arabic Financial Proposal PDF...");

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
<title>العرض المالي والاستراتيجي: رادار تسرّب الأرباح - Profit Leakage Radar</title>
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
    color: #0f172a;
    line-height: 1.6;
    margin: 0;
    padding: 0;
    background: #ffffff;
    font-size: 12.5px;
  }
  
  /* صفحة الغلاف */
  .cover {
    height: 100%;
    min-height: 980px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    padding: 35px 25px;
    background: radial-gradient(circle at 90% 10%, rgba(99, 102, 241, 0.15), transparent 50%),
                radial-gradient(circle at 10% 90%, rgba(16, 185, 129, 0.10), transparent 50%),
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
    padding: 5px 14px;
    border-radius: 9999px;
    font-weight: 700;
    font-size: 11.5px;
  }
  .cover-body {
    margin: auto 0;
    text-align: center;
  }
  .main-tagline {
    display: inline-block;
    background: #eef2ff;
    color: #4338ca;
    padding: 4px 14px;
    border-radius: 9999px;
    font-size: 13px;
    font-weight: 700;
    margin-bottom: 16px;
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
    font-size: 16px;
    color: #334155;
    max-width: 680px;
    margin: 0 auto 30px;
    font-weight: 600;
    line-height: 1.6;
  }
  .cover-formula {
    background: #f8fafc;
    border: 2px dashed #6366f1;
    border-radius: 14px;
    padding: 18px;
    max-width: 640px;
    margin: 0 auto;
    font-size: 14px;
    color: #1e1b4b;
    font-weight: 700;
  }
  .cover-formula span {
    color: #16a34a;
  }
  .cover-pillars {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 14px;
    text-align: right;
    margin-top: 30px;
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
    font-size: 13px;
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

  /* الفصول والتنسيقات */
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
    font-size: 19px;
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
    margin-bottom: 16px;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 14px;
    background: #ffffff;
    page-break-inside: avoid;
  }
  .section-title {
    font-size: 15px;
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
    margin: 10px 0;
    font-size: 12px;
    color: #14532d;
    line-height: 1.6;
  }
  .callout-warn {
    background: #fffbeb;
    border-right: 4px solid #d97706;
    padding: 10px 14px;
    border-radius: 6px;
    margin: 10px 0;
    font-size: 12px;
    color: #78350f;
    line-height: 1.6;
  }
  .callout-indigo {
    background: #eef2ff;
    border-right: 4px solid #4f46e5;
    padding: 10px 14px;
    border-radius: 6px;
    margin: 10px 0;
    font-size: 12px;
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
    padding: 12px;
    text-align: right;
  }
  .kpi-title {
    font-size: 11px;
    color: #64748b;
    font-weight: 700;
    margin-bottom: 4px;
  }
  .kpi-value {
    font-size: 18px;
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
    margin: 10px 0;
  }
  table.guide-table th {
    background: #f1f5f9;
    color: #1e293b;
    text-align: right;
    padding: 8px 10px;
    border: 1px solid #cbd5e1;
    font-weight: 800;
  }
  table.guide-table td {
    padding: 8px 10px;
    border: 1px solid #e2e8f0;
    text-align: right;
    vertical-align: top;
  }
  .badge-tag-mini {
    display: inline-block;
    padding: 2px 7px;
    border-radius: 4px;
    font-size: 10px;
    font-weight: 700;
  }
</style>
</head>
<body>

  <!-- ======================== صفحة الغلاف ======================== -->
  <div class="cover">
    <div class="cover-header">
      <div class="brand-logo">BUSINESS GATE · PROFIT RADAR</div>
      <div class="badge-tag">عرض استراتيجي ومالي لمجلس الإدارة والإدارة التنفيذية</div>
    </div>

    <div class="cover-body">
      <div class="main-tagline">خدمة استرداد الأرباح الذكية (Profit Leakage Radar Service)</div>
      
      <h1 class="cover-title">
        كيف توقف تسرّب الأرباح وترفع صافي الربح<br/>
        <span>دون ميزانيات تسويق إضافية ودون خفض التكاليف؟</span>
      </h1>

      <p class="cover-sub">
        تحليل مالي استراتيجي يكشف أين تضيع أموال شركتك اليوم في الفجوات التشغيلية غير المرئية، وكيف يحوّل رادار الأرباح تلك الخسائر إلى تدفقات نقدية فورية داخل خزينتك.
      </p>

      <div class="cover-formula">
        المعادلة المالية الذهبية:<br/>
        صافي أرباح إضافية = <span>استرداد الهدر المخفي</span> داخل مخزونك الحالي، وتسعيرك، وعملياتك القائمة بالفعل!
      </div>

      <div class="cover-pillars">
        <div class="pillar-card">
          <h4>صفر تكاليف تسويق إضافية</h4>
          <p>لا نطلب منك ضخ جنيه واحد إضافي في الإعلانات أو الاستحواذ على عملاء جدد، بل نستغل الطلب القائم الذي يضيع بسبب النفاد وسوء التوزيع.</p>
        </div>
        <div class="pillar-card">
          <h4>صفر تقليص تكاليف أو جودة</h4>
          <p>لا نوصي بخفض رواتب الموظفين أو المساس بجودة الخامات ومستوى الخدمة، بل نوقف نزيف الهدر في الخصومات العشوائية والأصناف الراكدة.</p>
        </div>
        <div class="pillar-card">
          <h4>عائد نقدي مباشر وسريع</h4>
          <p>قرارات تجارية محددة بالأرقام ومعدل الثقة (Confidence %) تترجم فورًا إلى أموال مستردة قابلة للقياس خلال 30 إلى 90 يومًا.</p>
        </div>
      </div>
    </div>

    <div class="cover-footer">
      <div>إعداد: فريق استشارات استرداد الأرباح والذكاء التجاري</div>
      <div>خدمة تحليل مالي معزولة 100% · متوافقة مع سرية البيانات الداخلية</div>
    </div>
  </div>

  <!-- ======================== صفحة 1: المعضلة التقليدية مقابل الحل الذكي ======================== -->
  <div class="header">
    <h2>1. الفخ المالي التقليدي: لماذا تفشل محاولات زيادة الأرباح المعتادة؟</h2>
    <div class="badge">المأزق الاستراتيجي</div>
  </div>

  <div class="section">
    <div class="section-title"><span class="num">1</span> الفخ التقليدي للشركات: التسويق الإضافي أو خفض النفقات؟</div>
    <p>عندما تسعى أي شركة لزيادة أرباحها، يقع فريق الإدارة عادة في أحد خيارين كلاهما مؤلم ومحفوف بالمخاطر:</p>

    <div class="grid-2">
      <div class="kpi-card" style="border-top: 3px solid #ef4444;">
        <div class="kpi-title" style="color: #b91c1c;">المسار الأول: زيادة ميزانية التسويق والإعلانات</div>
        <p style="margin: 0; font-size: 11.5px; color: #475569;">
          • تكلفة اكتساب العميل (CAC) في ارتفاع مستمر عبر كل المنصات.<br/>
          • تصرف ميزانيات إعلانية على منتجات أوشكت على النفاد في الفروع!<br/>
          • النتيجة: زيادة إيرادات ظاهرية مصحوبة بتآكل الهوامش وانخفاض العائد على الإنفاق الإعلاني (ROAS).
        </p>
      </div>
      <div class="kpi-card" style="border-top: 3px solid #f59e0b;">
        <div class="kpi-title" style="color: #b45309;">المسار الثاني: خفض التكاليف وضغط النفقات</div>
        <p style="margin: 0; font-size: 11.5px; color: #475569;">
          • تقليل جودة المواد الخام يؤدي لزيادة شكاوى العملاء ومعدلات المرتجعات.<br/>
          • تقليص العمالة أو الصيانة يسبب توقف الماكينات واختناق الإنتاج.<br/>
          • النتيجة: تدمير سمعة العلامة التجارية وتراجع رضا العملاء على المدى الطويل.
        </p>
      </div>
    </div>

    <div class="callout-green">
      <b>المسار الثالث (رادار تسرّب الأرباح):</b><br/>
      <b>"الأرباح ليست مفقودة في السوق الخارجي... بل محبوسة ومُهدرة داخل عملياتك الحالية!"</b><br/>
      تحليل بيانات مبيعاتك ومخزونك يثبت أن شركتك تمتلك بالفعل كل المبيعات والعملاء والموارد الكافية لتحقيق هوامش أرباح قياسية، فقط إذا تم إيقاف <b>التسرّب الخفي</b> في العمليات اليومية.
    </div>

    <table class="guide-table">
      <thead>
        <tr>
          <th>المقارنة المالية</th>
          <th>المسار التقليدي (التسويق)</th>
          <th>المسار التقشفي (خفض التكاليف)</th>
          <th>مسار رادار تسرّب الأرباح (Profit Radar)</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><b>التكلفة الرأسمالية</b></td>
          <td>مرتفعة جدًا وكاش فوري يخرج للمنصات</td>
          <td>تكلفة خفية على السمعة والجودة</td>
          <td><b>صفر تكاليف إضافية (Zero Extra Cost)</b></td>
        </tr>
        <tr>
          <td><b>أثر الربحية</b></td>
          <td>مخاطرة تآكل الهامش</td>
          <td>تراجع رضا العملاء والمرتجعات</td>
          <td><b>أرباح صافية 100% تتدفق للخزينة مباشرة</b></td>
        </tr>
        <tr>
          <td><b>سرعة المردود</b></td>
          <td>غير مضمونة وتعتمد على خوارزميات السوق</td>
          <td>بطيئة وتسبب صدمات تشغيلية</td>
          <td><b>نتائج فورية خلال 30 إلى 60 يومًا</b></td>
        </tr>
      </tbody>
    </table>
  </div>

  <div class="page-break"></div>

  <!-- ======================== صفحة 2: مصادر تسرّب الأرباح الأربعة ======================== -->
  <div class="header">
    <h2>2. أين تتسرب أموال شركتك اليوم؟ (تشريح الهدر الربحي)</h2>
    <div class="badge">الأدلة الرقمية</div>
  </div>

  <div class="section">
    <div class="section-title"><span class="num">2</span> مصادر التسرّب الأربعة الكبرى التي يرصدها الرادار</div>
    <p>يقوم محرك الرادار بمسح 100% من فواتير مبيعاتك، حركات المخزون، وأوامر الإنتاج ليكشف الفجوات الأربعة التالية:</p>

    <div class="grid-2">
      <div class="section" style="margin-bottom:0; background: #fff1f2; border-color: #fecdd3;">
        <h4 style="margin: 0 0 4px; color: #9f1239; font-size: 13px;">1. الخصومات الزائدة غير المبررة (Discount Leakage)</h4>
        <p style="margin: 0; font-size: 11.5px; color: #4c0519;">
          <b>الحقيقة الصادمة:</b> أثبتت تحليلاتنا أن تقديم خصومات تتجاوز 10% إلى 20% على أصناف ذات طلب مستقر <b>لم يرفع حجم المبيعات إطلاقًا!</b><br/>
          الشركة ببساطة تقدم أموالها هدية لعميل كان سيشتري المنتج بالسعر الكامل. الرادار يحدد فورًا الأصناف التي يجب إيقاف الخصم عليها لحماية الهامش.
        </p>
      </div>

      <div class="section" style="margin-bottom:0; background: #fff7ed; border-color: #fed7aa;">
        <h4 style="margin: 0 0 4px; color: #9a3412; font-size: 13px;">2. المخزون الراكد مقابل الفرص الضائعة (Trapped Cash)</h4>
        <p style="margin: 0; font-size: 11.5px; color: #431407;">
          <b>مفارقة المخزون:</b> فرع يخسر مبيعات يوميًا لأن الصنف نفد لديه، بينما فرع آخر أو مستودع رئيسي يمتلك 150 قطعة راكدة من نفس الصنف تكفي 200 يوم!<br/>
          الرادار يوجهك لنقل البضاعة المحبوسة فورًا إلى الفروع العطشى دون الحاجة لإنتاج أو شراء قطعة جديدة واحدة.
        </p>
      </div>
    </div>

    <div class="grid-2" style="margin-top: 10px;">
      <div class="section" style="margin-bottom:0; background: #fefce8; border-color: #fef08a;">
        <h4 style="margin: 0 0 4px; color: #854d0e; font-size: 13px;">3. تكاليف المرتجعات واختلال المقاسات (Fit & Returns)</h4>
        <p style="margin: 0; font-size: 11.5px; color: #422006;">
          المرتجع ليس مجرد بيعة ملغاة؛ إنه تكلفة شحن عكسي، هدر تغليف، وتجميد بضاعة.<br/>
          الرادار يحلل إشارات المقاسات التي يتكرر إرجاعها ويربطها بتعديل جدول المقاسات ومحاسبة مصانع وموردي الأقمشة غير المطابقة للمواصفات.
        </p>
      </div>

      <div class="section" style="margin-bottom:0; background: #f5f3ff; border-color: #ddd6fe;">
        <h4 style="margin: 0 0 4px; color: #5b21b6; font-size: 13px;">4. تعارض الحملات الإعلانية مع المخزون (Campaign Collisions)</h4>
        <p style="margin: 0; font-size: 11.5px; color: #2e1065;">
          كم مرة أطلقت شركتك حملة ممولة على صنف لا يتوفر منه سوى مقاس واحد في المخزن؟<br/>
          الرادار يمنع إهدار ميزانية التسويق على أصناف منخفضة المخزون، ويوجه الإنفاق الإعلاني حصرًا لدعم المنتجات ذات الهامش المرتفع والمخزون الآمن.
        </p>
      </div>
    </div>

    <div class="img-container">
      <img src="${imgLeakage}" alt="لوحة كشف تسرّب الأرباح" />
    </div>
  </div>

  <div class="page-break"></div>

  <!-- ======================== صفحة 3: كيف يحول الرادار الهدر إلى أرباح؟ ======================== -->
  <div class="header">
    <h2>3. كيف يحوّل الرادار هذا الهدر إلى أرباح نقدية؟ (آلية العمل)</h2>
    <div class="badge">محرك القرارات التجارية</div>
  </div>

  <div class="section">
    <div class="section-title"><span class="num">3</span> من التحليل النظري إلى قرارات تنفيذية موجهة ومدروسة</div>
    <p>نحن لا نقدم تقارير تقليدية ممتلئة بالرسوم البيانية المعقدة التي تنتهي في الأدراج؛ الرادار يقدم <b>توصيات وقرارات جاهزة للتنفيذ</b> مدعومة بثلاثة عناصر صارمة:</p>

    <div class="grid-3" style="margin-bottom: 12px;">
      <div class="kpi-card">
        <div class="kpi-title">الأثر المالي بالجنيه (EGP)</div>
        <p style="margin: 0; font-size: 11px; color: #475569;">كل قرار مصحوب برقم دقيق يوضح صافي العائد المتوقع عند تنفيذه (مثل: استرداد 140,000 ج.م).</p>
      </div>
      <div class="kpi-card">
        <div class="kpi-title">نسبة الثقة الإحصائية (Confidence %)</div>
        <p style="margin: 0; font-size: 11px; color: #475569;">مؤشر يعتمد على حجم البيانات التاريخية لضمان عدم اتخاذ أي خطوة تخمينية أو غير مؤكدة.</p>
      </div>
      <div class="kpi-card">
        <div class="kpi-title">إجراء تنفيذي محدد بالاسم</div>
        <p style="margin: 0; font-size: 11px; color: #475569;">توجيه صريح ومباشر: (إلغاء الخصم على الصنف X · نقل 40 قطعة من فرع A إلى B · تصريف مقاس L).</p>
      </div>
    </div>

    <div class="img-container">
      <img src="${imgDecisions}" alt="شاشة خطط القرارات" />
    </div>

    <div class="callout-indigo" style="margin-top: 10px;">
      <b>ثلاث خطط تلائم استراتيجية شركتك:</b><br/>
      • <b>خطة أقصى ربح (Max Profit):</b> لأعلى استرداد مالي فوري للشركات ذات السيولة المريحة.<br/>
      • <b>الخطة المتوازنة (Balanced):</b> تحييد المخاطر والالتزام التام بالحدود النقدية المتاحة للشركة.<br/>
      • <b>خطة أقل مخاطرة (Min Risk):</b> قرارات بنسبة ثقة إحصائية تتجاوز 60% لضمان الأمان التام.
    </div>
  </div>

  <div class="page-break"></div>

  <!-- ======================== صفحة 4: غرفة العمليات وقياس القيمة المحققة ======================== -->
  <div class="header">
    <h2>4. غرفة اتخاذ القرارات وإثبات القيمة (War Room & Realized Value)</h2>
    <div class="badge">المتابعة والشفافية</div>
  </div>

  <div class="section">
    <div class="section-title"><span class="num">4</span> لا نتركك مع التوصيات.. بل نقيس القيمة المحققة فعليًا!</div>
    <p>أهم ما يميز خدمتنا هو <b>غرفة العمليات (War Room) ومحرك إثبات القيمة</b>، حيث تنتقل التوصيات من مجرد فكرة إلى أثر نقدي مثبت في سجلاتك المحاسبية:</p>

    <div class="img-container">
      <img src="${imgWarRoom}" alt="غرفة اتخاذ القرارات War Room" />
    </div>

    <div class="grid-2" style="margin-top: 12px;">
      <div class="callout-green" style="margin: 0;">
        <b>دورة حياة القرار المضمونة:</b><br/>
        1. <b>مفتوح (Open):</b> يراجعه المسؤول في شركتك ويعتمده.<br/>
        2. <b>قيد التنفيذ (In Progress):</b> يبدأ تنفيذه في الفروع أو المستودعات.<br/>
        3. <b>قيد القياس (Measuring):</b> يرصد النظام المبيعات والأرباح بعد الإجراء.<br/>
        4. <b>تم القياس (Measured):</b> تسجيل الأرباح الصافية المحققة فعليًا.
      </div>

      <div class="callout-indigo" style="margin: 0;">
        <b>مبدأ الشفافية المطلقة (Audit Trail):</b><br/>
        • يتم توثيق اسم كل من اعتمد القرار وتاريخ التنفيذ.<br/>
        • تقارير مقارنة تثبت كم دخل خزانة شركتك قبل وبعد تطبيق كل قرار.<br/>
        • دليل دامغ لأعضاء مجلس الإدارة على جدوى وعائد الاستثمار.
      </div>
    </div>
  </div>

  <div class="section">
    <div class="section-title"><span class="num">5</span> كيف نبدأ التعاون معك؟ (خطة العمل في 3 خطوات)</div>
    <table class="guide-table">
      <thead>
        <tr>
          <th>المرحلة</th>
          <th>المدة الزمنية</th>
          <th>ماذا نقدم لشركتك؟</th>
          <th>المطلوب من شركتك</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><b>1. الفحص الاستكشافي المالي (Profit Leakage Audit)</b></td>
          <td>3 إلى 5 أيام عمل</td>
          <td>تحليل شامل لفواتير ومخزون آخر 12 شهرًا، وتقديم تقرير مفصل بمبالغ التسرّب المقدرة بالجنيه.</td>
          <td>تزويدنا بنسخة مشفرة من بيانات المبيعات والمخزون السابقة.</td>
        </tr>
        <tr>
          <td><b>2. تشغيل رادار القرارات التفاعلي (Radar Activation)</b></td>
          <td>أسبوع واحد</td>
          <td>تثبيت المنصة في بيئتكم، تدريب فريق الإدارة على شاشات مركز القيادة وغرفة العمليات.</td>
          <td>جلسة عمل واحدة لاعتماد خطة القرارات الأولى (Balanced Plan).</td>
        </tr>
        <tr>
          <td><b>3. جني واسترداد الأرباح الدورية (Profit Recovery Cycle)</b></td>
          <td>شهريًا / ربع سنويًا</td>
          <td>متابعة تنفيذ التوصيات، قياس القيمة المستردة أسبوعيًا، وتحديث تقارير مجلس الإدارة.</td>
          <td>تنفيذ الإجراءات المتفق عليها في الفروع وقنوات البيع.</td>
        </tr>
      </tbody>
    </table>
  </div>

  <div style="text-align: center; margin-top: 30px; border-top: 2px solid #4f46e5; padding-top: 15px;">
    <h3 style="margin: 0 0 6px; color: #1e1b4b; font-size: 16px;">هل أنت مستعد لاسترداد الأرباح المحبوسة في شركتك؟</h3>
    <p style="margin: 0; color: #475569; font-size: 12px;">يسعدنا تقديم جلسة استكشافية مجانية لعرض نموذج المحاكاة على بيانات تجريبية تثبت حجم العائد المالي المتوقع لشركتكم.</p>
  </div>

</body>
</html>`;

  const htmlPath = path.join(__dirname, "Profit_Leakage_Radar_Executive_Proposal_AR.html");
  fs.writeFileSync(htmlPath, htmlContent, "utf8");
  console.log("Proposal HTML created:", htmlPath);

  const browser = await puppeteer.launch({
    executablePath: CHROME_PATH,
    headless: "new",
    args: ["--no-sandbox", "--disable-setuid-sandbox"],
  });

  const pdfPage = await browser.newPage();
  await pdfPage.goto(`file://${htmlPath}`, { waitUntil: "networkidle0" });

  const pdfPath = path.join(__dirname, "Profit_Leakage_Radar_Executive_Proposal_AR.pdf");
  await pdfPage.pdf({
    path: pdfPath,
    format: "A4",
    printBackground: true,
    margin: { top: "10mm", bottom: "10mm", left: "10mm", right: "10mm" },
  });

  console.log("Proposal PDF created successfully at:", pdfPath);
  await browser.close();
}

run().catch((err) => {
  console.error("Error creating proposal PDF:", err);
  process.exit(1);
});
