"""Arabic rendering of the sentences the decision engines generate.

The engines write English templates with numbers and names filled in (e.g. "Only 3.2 days of cover against a 14-day supplier lead time").
Here every template has an Arabic twin. A response is translated only when the caller sends `Accept-Language: ar`; any sentence
without a matching template is returned unchanged (English), so a missing rule can never break a screen.
Product names, SKUs, location names and other business data are never translated.
"""
from __future__ import annotations
import re
from functools import lru_cache

# ---- vocabulary used inside placeholders (data values that come from fixed sets)
TERMS = {
    # margin drivers
    "deeper discounts": "خصومات أعمق", "higher cost of goods": "ارتفاع تكلفة البضاعة", "more returns and refunds": "زيادة المرتجعات والاسترداد",
    "quality losses": "خسائر الجودة", "printing rework": "إعادة الطباعة", "production rejects": "مرفوضات الإنتاج", "higher campaign spend": "زيادة إنفاق الحملات",
    # stages / defects / causes
    "Fabric": "القماش", "Finishing": "التشطيب", "Cutting": "القص", "Final": "الفحص النهائي", "Printing": "الطباعة", "Sewing": "الخياطة",
    "Color Misalignment": "عدم محاذاة الألوان", "Print Cracking": "تشقق الطباعة", "Size Variance": "اختلاف المقاس", "Ink Smudge": "تلطخ الحبر",
    "Fabric Defect": "عيب في القماش", "Packing Error": "خطأ في التعبئة", "Finishing Defect": "عيب في التشطيب", "Stitch Defect": "عيب في الخياطة",
    "No significant issue": "لا توجد مشكلة جوهرية", "Operator method": "طريقة المشغّل", "Machine calibration": "معايرة الماكينة", "Material variation": "تفاوت الخامات",
    "Pattern / measurement": "الباترون / القياسات", "Handling / packing": "المناولة / التعبئة", "Curing temperature": "حرارة التثبيت", "Process variation": "تفاوت العملية",
    # misc
    "Procurement": "المشتريات", "Operations": "العمليات", "Merchandising": "الميرشاندايزينج", "Quality": "الجودة", "Marketing": "التسويق", "Management": "الإدارة",
    "Production": "الإنتاج", "Finance": "المالية", "a manager": "مدير",
    # workflow statuses
    "new": "جديد", "under review": "قيد المراجعة", "approved": "معتمد", "in progress": "قيد التنفيذ", "done": "منتهٍ", "rejected": "مرفوض", "measured": "تم قياسها",
    "unmeasurable": "غير قابلة للقياس", "measuring": "قيد القياس", "failed": "فشل", "warning": "تحذير", "missing": "مفقود", "ok": "سليم", "success": "نجح", "partial": "جزئي", "unassigned": "غير مُسنَد",
}


def _term(v: str) -> str:
    v = v.strip()
    return TERMS.get(v, TERMS.get(v.lower(), v))


# (english template, arabic template). {name} = any text. Longer / more specific templates first is handled automatically.
RULES: list[tuple[str, str]] = [
    # ------------------------------------------------ product action: titles
    ("Transfer stock: {nm}", "نقل مخزون: {nm}"), ("Replenish: {nm}", "إعادة التوريد: {nm}"), ("Discount to clear: {nm}", "خصم لتصريف المخزون: {nm}"),
    ("Stop replenishing: {nm}", "إيقاف التوريد: {nm}"), ("Phase out: {nm}", "سحب تدريجي: {nm}"), ("Fix quality: {nm}", "معالجة الجودة: {nm}"), ("Scale up: {nm}", "التوسّع: {nm}"),
    # problems
    ("Stock is in the wrong place", "المخزون في المكان الخطأ"), ("Likely to run out of stock", "مرجّح أن ينفد المخزون"),
    ("Stock is unlikely to sell at current pace", "من غير المرجّح تصريف المخزون بالوتيرة الحالية"), ("Over-supplied while demand is slow", "توريد زائد مع بطء الطلب"),
    ("Slow, declining product with trapped capital", "منتج بطيء ومتراجع وفيه رأس مال محبوس"), ("Quality problems are driving rejects and returns", "مشاكل الجودة تسبب مرفوضات ومرتجعات"),
    ("Winner with room to grow", "منتج رابح وفيه مجال للنمو"),
    # reasons
    ("{loc} has {doc} days of cover (supplier lead time {lead} days)", "{loc} عنده تغطية {doc} يوم (مدة توريد المورّد {lead} يوم)"),
    ("{loc} holds {doc} days of cover and can spare stock", "{loc} عنده تغطية {doc} يوم ويقدر يتنازل عن جزء من المخزون"),
    ("Demand here is {x}x faster than at the source", "الطلب هنا أسرع بمقدار {x} مرة من مصدر النقل"),
    ("Only {doc} days of cover against a {lead}-day supplier lead time", "تغطية {doc} يوم فقط مقابل مدة توريد {lead} يوم"),
    ("Expected demand about {v} units/day; stock is {s} units (reorder point {r})", "الطلب المتوقع حوالي {v} وحدة/يوم؛ المخزون {s} وحدة (نقطة إعادة الطلب {r})"),
    ("Risk model also rates this combination as likely to stock out next month", "نموذج المخاطر أيضًا يرجّح نفاد هذا المنتج في هذا المكان الشهر القادم"),
    ("Already stocked out for {d} days in the last 3 months", "نفد المخزون فعلًا لمدة {d} يوم خلال آخر 3 شهور"),
    ("Quality reject rate {q} is in the worst 15% of products", "معدل رفض الجودة {q} ضمن أسوأ 15% من المنتجات"),
    ("Customer return rate here is {r} (portfolio median {m})", "معدل مرتجعات العملاء هنا {r} (وسيط المحفظة {m})"),
    ("Estimated quality loss in the last 180 days: {l}", "خسارة الجودة التقديرية خلال آخر 180 يوم: {l}"),
    ("{doc} days of cover at expected demand; sells only ~{s} of {t} units in 90 days", "{doc} يوم تغطية عند الطلب المتوقع؛ يُباع حوالي {s} فقط من {t} وحدة خلال 90 يوم"),
    ("About {u} units ({v} at cost) are unlikely to sell", "حوالي {u} وحدة ({v} بسعر التكلفة) من غير المرجّح بيعها"),
    ("Dead-stock risk model rates this {p} likely to remain unsold", "نموذج مخاطر المخزون الراكد يرجّح بنسبة {p} أن يظل غير مباع"),
    ("A {d} discount keeps margin above the {f} floor (max feasible {m})", "خصم {d} يُبقي الهامش فوق الحد الأدنى {f} (أقصى خصم ممكن {m})"),
    ("{u} units can move to a location with a shortage", "{u} وحدة يمكن نقلها إلى مكان فيه عجز"),
    ("Stock is still being received while cover is already very high", "ما زال المخزون يُستلم رغم أن التغطية مرتفعة جدًا"),
    ("Sales over the last 90 days are {y}x the same period last year", "مبيعات آخر 90 يوم تساوي {y} ضعف نفس الفترة من العام الماضي"),
    ("Margin {m} is above the portfolio median ({p})", "الهامش {m} أعلى من وسيط المحفظة ({p})"),
    ("Healthy cover ({d} days) and a normal return rate ({r})", "تغطية سليمة ({d} يوم) ومعدل مرتجعات طبيعي ({r})"),
    ("Cover, sales trend, margin and quality are all within normal ranges", "التغطية واتجاه المبيعات والهامش والجودة كلها ضمن النطاق الطبيعي"),
    # actions
    ("Transfer {u} units of {p} from {a} to {b}", "انقل {u} وحدة من {p} من {a} إلى {b}"),
    ("Move {u} surplus units of {p} out of {a} to locations short of stock", "انقل {u} وحدة فائضة من {p} خارج {a} إلى أماكن تعاني نقص المخزون"),
    ("Order about {u} units of {p} for {a}", "اطلب حوالي {u} وحدة من {p} لـ {a}"),
    ("Run a {d} additional discount on {p} at {a} (margin floor protected)", "نفّذ خصمًا إضافيًا {d} على {p} في {a} (مع حماية الحد الأدنى للهامش)"),
    ("Stop incoming replenishment of {p} for {a} until cover falls below {d} days", "أوقف توريد {p} إلى {a} حتى تنخفض التغطية عن {d} يوم"),
    ("Plan the phase-out of {p}: no re-orders, clear existing stock", "خطّط للسحب التدريجي لـ {p}: بدون إعادة طلب وتصريف المخزون الحالي"),
    ("Open a corrective-action review on {p} (quality rejects and returns)", "افتح مراجعة إجراء تصحيحي على {p} (مرفوضات الجودة والمرتجعات)"),
    ("Increase supply and visibility for {p} at {a}", "زوّد التوريد والظهور لـ {p} في {a}"),
    # ------------------------------------------------ margin erosion
    ("Margin erosion: {p}", "تآكل الهامش: {p}"), ("Selling more but earning less", "بيع أكثر لكن ربح أقل"),
    ("Units {u} but contribution per unit {c} vs the previous 90 days", "الوحدات {u} لكن مساهمة الوحدة {c} مقارنة بآخر 90 يوم السابقة"),
    ("Low Stock Push: {c}", "حملة على مخزون منخفض: {c}"), ("Production Issue: {c}", "حملة مع مشكلة إنتاج: {c}"), ("Quality Issue: {c}", "حملة مع مشكلة جودة: {c}"),
    ("Low Stock: {c}", "مخزون منخفض: {c}"), ("Production Delay: {c}", "تأخر إنتاج: {c}"),
    ("Margin {a} -> {b}", "الهامش {a} ← {b}"),
    ("Biggest drag: {d} ({v} lower profit); total controllable drag {t}", "أكبر عامل ضغط: {d} (ربح أقل بمقدار {v})؛ إجمالي الضغط الذي يمكن التحكم فيه {t}"),
    ("{a} - restoring this driver to last quarter's level recovers about {v} per quarter", "{a} — إعادة هذا العامل لمستوى الربع الماضي تسترد حوالي {v} في الربع"),
    ("last 90 days vs previous 90 days", "آخر 90 يوم مقابل 90 يوم السابقة"),
    ("Cap discount depth and review wholesale discount tiers", "ضع حدًا لعمق الخصم وراجع شرائح خصومات الجملة"),
    ("Review BOM consumption and supplier prices for this product", "راجع استهلاك قائمة المواد وأسعار الموردين لهذا المنتج"),
    ("Investigate return reasons and tighten size/fit information", "افحص أسباب المرتجعات وحسّن معلومات المقاس والقصّة"),
    ("Open a corrective-action plan on the main defects", "افتح خطة إجراء تصحيحي على العيوب الرئيسية"),
    ("Fix the printing process (machine/consumables) causing rework", "أصلح عملية الطباعة (الماكينة/المستهلكات) المسببة لإعادة الطباعة"),
    ("Reduce reject rate on the production line", "قلّل معدل الرفض على خط الإنتاج"),
    ("Reduce or re-target campaign spend", "قلّل إنفاق الحملات أو أعد توجيهه"), ("Review price list and channel mix", "راجع قائمة الأسعار وتوزيع القنوات"),
    # ------------------------------------------------ marketing
    ("Campaign is pushing demand into stock that covers only {d} days (supplier lead time {l} days)", "الحملة تدفع الطلب نحو مخزون يغطي {d} يوم فقط (مدة توريد المورّد {l} يوم)"),
    ("Pause or cap the campaign until stock is replenished or transferred in", "أوقف الحملة أو حدّ منها حتى يُعاد توريد المخزون أو ينتقل إليه"),
    ("Production for this product is delayed in {s} of recent orders with a {r} reject rate, and cover is only {d} days", "إنتاج هذا المنتج متأخر في {s} من الأوامر الأخيرة بمعدل رفض {r}، والتغطية {d} يوم فقط"),
    ("Hold paid support until production recovers", "أوقف الدعم المدفوع حتى يتعافى الإنتاج"),
    ("Product has a {q} QC reject rate and {r} quality-related returns", "المنتج عليه معدل رفض جودة {q} و{r} من المرتجعات المرتبطة بالجودة"),
    ("Shift budget to a healthier product until the quality issue is fixed", "انقل الميزانية لمنتج أسلم حتى تُحل مشكلة الجودة"),
    ("Marketing spend and inventory/quality are in conflict", "إنفاق التسويق يتعارض مع المخزون/الجودة"),
    ("Campaign {c}: spend {s} on {p}, runs {a} to {b}", "الحملة {c}: إنفاق {s} على {p}، من {a} إلى {b}"),
    ("{d} days of cover but only {m} of marketing in the last 90 days", "{d} يوم تغطية لكن تسويق {m} فقط خلال آخر 90 يوم"),
    ("Add targeted campaign support", "أضف دعمًا تسويقيًا موجّهًا"),
    ("Support overstocked product: {p}", "دعم منتج مكدّس: {p}"), ("Excess stock with little marketing", "مخزون زائد مع تسويق قليل"),
    ("{d} days of consumer-channel cover", "{d} يوم تغطية في قنوات المستهلك"),
    ("Marketing spend last 90 days: {a} (portfolio median {b})", "إنفاق التسويق آخر 90 يوم: {a} (وسيط المحفظة {b})"),
    ("Run a targeted campaign for {p} to pull forward demand", "نفّذ حملة موجّهة لـ {p} لتقديم الطلب"),
    ("spend x share of campaign period beyond stock coverage (estimate)", "الإنفاق × نسبة فترة الحملة التي تتجاوز تغطية المخزون (تقدير)"),
    ("assumes 15% of stock value could be pulled forward (conservative scenario)", "بافتراض إمكانية تقديم 15% من قيمة المخزون (سيناريو متحفظ)"),
    ("Attributed revenue comes from the campaign file (modelled attribution); it is not reconciled to Sales_Transactions.", "الإيراد المنسوب مصدره ملف الحملات (إسناد نموذجي) وغير مطابق لملف المبيعات."),
    # ------------------------------------------------ operations
    ("Fix the {b} bottleneck", "معالجة اختناق {b}"), ("One production stage causes the largest share of delays", "مرحلة إنتاج واحدة تسبب أكبر نسبة من التأخير"),
    ("{b} is the primary bottleneck in {o} orders and {s} of all bottleneck delay days", "الاختناق الرئيسي هو {b} في {o} أمر، ويمثل {s} من إجمالي أيام التأخير"),
    ("{h} overtime hours and {c} of rejected output (at cost) sit on these orders", "{h} ساعة إضافية و{c} من الإنتاج المرفوض (بسعر التكلفة) على هذه الأوامر"),
    ("Add capacity / re-sequence work at {b}; review line balancing", "أضف طاقة / أعد ترتيب العمل في {b}؛ وراجع توازن الخط"),
    ("Machine {m}: unplanned downtime up {p}", "الماكينة {m}: ارتفاع التوقف غير المخطط بنسبة {p}"), ("Unplanned downtime is rising", "التوقف غير المخطط في ازدياد"),
    ("{a} unplanned downtime hours in the last 6 months vs {b} before", "{a} ساعة توقف غير مخطط خلال آخر 6 شهور مقابل {b} قبلها"),
    ("EGP cost of downtime is not in the data; priced only through printing rework when the machine is a printer", "تكلفة التوقف بالجنيه غير موجودة في البيانات؛ تُقدَّر فقط عبر إعادة الطباعة إذا كانت الماكينة طابعة"),
    ("Schedule preventive maintenance on {m} and review the top failure reasons", "جدول صيانة وقائية للماكينة {m} وراجع أهم أسباب الأعطال"),
    ("30% of rejected-output cost on bottleneck orders (scenario); overtime cost in EGP is not in the data", "30% من تكلفة الإنتاج المرفوض على أوامر الاختناق (سيناريو)؛ تكلفة الوقت الإضافي بالجنيه غير موجودة في البيانات"),
    ("10% of the machine's printing rework cost (scenario)", "10% من تكلفة إعادة الطباعة للماكينة (سيناريو)"),
    # ------------------------------------------------ quality
    ("Quality loss: {d} at {s} ({p})", "خسارة جودة: {d} في {s} ({p})"), ("A recurring defect is costing money", "عيب متكرر يكلّف أموالًا"),
    ("{d} at {s} stage lost {v} in the last 180 days ({u} rejected units)", "{d} في مرحلة {s} كلّف {v} خلال آخر 180 يوم ({u} وحدة مرفوضة)"),
    ("Recorded root cause: {c}", "السبب الجذري المسجّل: {c}"),
    ("Association with returns/CSAT is tracked on the Quality page; causality is not claimed", "الارتباط بالمرتجعات/رضا العملاء يظهر في صفحة الجودة؛ ولا يُدّعى وجود سببية"),
    ("Run a corrective action on {d} ({c}) at {s} for {p}", "نفّذ إجراءً تصحيحيًا على {d} ({c}) في {s} للمنتج {p}"),
    ("recoverable = 50% of recent loss if the defect is halved (scenario)", "القيمة القابلة للاسترداد = 50% من الخسارة الأخيرة إذا انخفض العيب للنصف (سيناريو)"),
    ("{t} move together (rho {r}, {n} months). This is an association; it does not prove cause.", "{t} يتحركان معًا (rho {r}، {n} شهر). هذا ارتباط وليس إثباتًا للسبب."),
    ("No reliable relationship found between {t} at a {l}-month lag (rho {r}, p {p}).", "لم نجد علاقة موثوقة بين {t} بفارق {l} شهر (rho {r}، p {p})."),
    ("Higher QC reject rates and quality-related returns", "ارتفاع معدلات رفض الجودة والمرتجعات المرتبطة بالجودة"),
    ("Printing reject rates and quality-related returns", "معدلات رفض الطباعة والمرتجعات المرتبطة بالجودة"),
    ("Production reject rates and quality-related returns", "معدلات رفض الإنتاج والمرتجعات المرتبطة بالجودة"),
    ("Quality-related returns and customer satisfaction (CSAT)", "المرتجعات المرتبطة بالجودة ورضا العملاء (CSAT)"),
    ("QC reject rates and return/quality tickets", "معدلات رفض الجودة وتذاكر المرتجعات/الجودة"),
    ("QC reject rates and return/quality tickets", "معدلات رفض الجودة وتذاكر المرتجعات/الجودة"),
    # ------------------------------------------------ sizes
    ("Size {s} share of sales rose {p} pts vs the prior 12 months", "حصة المقاس {s} من المبيعات ارتفعت {p} نقطة مقارنة بآخر 12 شهر سابقة"),
    ("Size {s} share fell {p} pts; {r} of its sales come back for size/fit", "حصة المقاس {s} انخفضت {p} نقطة؛ و{r} من مبيعاته تعود بسبب المقاس/القصّة"),
    ("Size {s} share fell {p} pts", "حصة المقاس {s} انخفضت {p} نقطة"),
    ("Re-weight reorder by size: {p} @ {l}", "أعد توزيع الطلب حسب المقاس: {p} @ {l}"),
    ("Reorder mix no longer matches what customers actually buy", "توزيع المقاسات في إعادة الطلب لم يعد يطابق ما يشتريه العملاء فعلًا"),
    ("Reorder {t} units split by size as: {a}", "أعد طلب {t} وحدة موزعة حسب المقاس كالتالي: {a}"),
    ("Current stock by size is unavailable (Inventory_History has no Size column). 'baseline' = the sales mix of the prior 12 months, used as a proxy for the implicit stocking curve.",
     "مخزون المقاسات الحالي غير متاح (ملف المخزون لا يحتوي عمود المقاس). 'الأساس' = توزيع مبيعات آخر 12 شهر السابقة كبديل لمنحنى التخزين الضمني."),
    # ------------------------------------------------ strategy
    ("Weak demand, trapped stock and below-average margin", "طلب ضعيف ومخزون محبوس وهامش أقل من المتوسط"),
    ("Stock is far above what demand needs in most locations", "المخزون أعلى بكثير من حاجة الطلب في معظم الأماكن"),
    ("Excess stock with only moderate demand", "مخزون زائد مع طلب متوسط فقط"),
    ("Demand outruns stock; supply side is healthy enough to respond", "الطلب يسبق المخزون والتوريد قادر على الاستجابة"),
    ("Stock is short in some locations while elsewhere it is not", "المخزون ناقص في بعض الأماكن وليس في غيرها"),
    ("A quality, production or supplier weakness limits this product", "ضعف في الجودة أو الإنتاج أو التوريد يحدّ من هذا المنتج"),
    ("Strong demand and margin with healthy inventory", "طلب وهامش قويان مع مخزون سليم"),
    ("Demand is healthy but stock is in the wrong places", "الطلب جيد لكن المخزون في أماكن غير مناسبة"),
    ("No dimension is far enough from normal to justify a change", "لا يوجد بُعد بعيد عن الطبيعي بما يبرر التغيير"),
    # ------------------------------------------------ suppliers
    ("Investigate supplier: {s}", "افحص المورّد: {s}"), ("Supplier performance is costing more than the purchase price shows", "أداء المورّد يكلّف أكثر مما يظهره سعر الشراء"),
    ("On-time delivery fell {p} pts to {r} (last 6 months vs the previous 6)", "انخفض التسليم في الميعاد {p} نقطة إلى {r} (آخر 6 شهور مقابل 6 قبلها)"),
    ("True cost is {t} of spend (observed {o} + estimated risk {e})", "التكلفة الحقيقية {t} من الإنفاق (فعلية {o} + مخاطر تقديرية {e})"),
    ("Review {s}: agree delivery and quality targets, or shift volume to a lower true-cost supplier", "راجع {s}: اتفق على أهداف التسليم والجودة أو انقل الكميات لمورّد أقل تكلفة حقيقية"),
    ("Observed cost {a} (rejected material {b} + spend above the market-median price {c}); estimated risk cost {d} (assumption-driven)",
     "التكلفة الفعلية {a} (خامات مرفوضة {b} + إنفاق أعلى من وسيط السعر {c})؛ تكلفة المخاطر التقديرية {d} (قائمة على افتراضات)"),
    ("Observed Cost = rejected material value + spend above the material's median price (facts from Purchase_Orders)", "التكلفة الفعلية = قيمة الخامات المرفوضة + الإنفاق فوق وسيط سعر الخامة (حقائق من أوامر الشراء)"),
    ("Estimated Risk Cost = delay days / rejected units x exposed daily gross profit x {k} pass-through ASSUMPTION", "تكلفة المخاطر التقديرية = أيام التأخير / الوحدات المرفوضة × الربح اليومي المعرّض × افتراض تمرير {k}"),
    ("association only - correlation does not prove the supplier caused the production delay", "ارتباط فقط — الارتباط لا يثبت أن المورّد سبب تأخير الإنتاج"),
    ("{k} of a late/rejected material day or unit is assumed to reach production", "يُفترض أن {k} من يوم/وحدة الخامة المتأخرة أو المرفوضة يصل أثره للإنتاج"),
    # ------------------------------------------------ KPI / executive
    ("Last 30 days vs previous 30 days", "آخر 30 يوم مقابل 30 يوم السابقة"), ("vs same 30 days last year: {c}", "مقابل نفس الـ30 يوم من العام الماضي: {c}"),
    ("Revenue", "الإيراد"), ("Gross Profit", "إجمالي الربح"), ("Gross Margin", "هامش الربح الإجمالي"), ("Revenue at Risk", "إيراد معرّض للخطر"),
    ("Next-30-day sales at stock-risk locations that stock cannot cover (estimate)", "مبيعات الـ30 يوم القادمة في أماكن خطر المخزون التي لا يغطيها المخزون (تقدير)"),
    ("Recoverable Profit", "ربح قابل للاسترداد"), ("Sum of estimated values of open recommendations (estimates)", "مجموع القيم التقديرية للتوصيات المفتوحة (تقديرات)"),
    ("Dead Stock Value", "قيمة المخزون الراكد"), ("Stock at cost unlikely to sell within 90 days", "مخزون بسعر التكلفة من غير المرجّح بيعه خلال 90 يوم"),
    ("Stockout Exposure", "خسائر نفاد المخزون"), ("Estimated sales already lost to stockouts in the last 3 months", "مبيعات تقديرية ضاعت فعلًا بسبب نفاد المخزون خلال آخر 3 شهور"),
    ("Returns", "المرتجعات"), ("Refunds issued in the last 90 days", "المبالغ المستردة خلال آخر 90 يوم"),
    ("Marketing Efficiency (ROAS)", "كفاءة التسويق (ROAS)"), ("Attributed revenue per EGP of spend, last 90 days (modelled attribution)", "الإيراد المنسوب لكل جنيه إنفاق، آخر 90 يوم (إسناد نموذجي)"),
    ("Production Efficiency", "كفاءة الإنتاج"), ("Average line efficiency, last 90 days", "متوسط كفاءة الخطوط، آخر 90 يوم"),
    # executive "areas" and categories
    ("Replenish", "إعادة التوريد"), ("Transfer inventory", "نقل المخزون"), ("Pause campaign", "إيقاف حملة"), ("Investigate supplier", "فحص مورّد"), ("Fix production issue", "معالجة مشكلة إنتاج"),
    ("Replenish size", "توريد مقاس"), ("Discount", "خصم"), ("Margin", "الهامش"), ("Stop replenishment", "إيقاف التوريد"), ("Support overstock", "دعم مخزون زائد"), ("Scale", "توسّع"),
    # ------------------------------------------------ API-level messages
    ("No data has been imported yet.", "لم يتم استيراد أي بيانات بعد."), ("Newest business data is {d} days old - decisions may be out of date.", "أحدث بيانات الأعمال عمرها {d} يوم — قد تكون القرارات قديمة."),
    ("Data updated {a}.", "تم تحديث البيانات {a}."), ("less than an hour ago", "منذ أقل من ساعة"), ("{n} hour ago", "منذ {n} ساعة"), ("{n} hours ago", "منذ {n} ساعة"), ("{n} days ago", "منذ {n} يوم"),
    ("No analytics are available yet. Import the company data first.", "لا توجد تحليلات بعد. استورد بيانات الشركة أولًا."),
    ("Email or password is not correct.", "البريد الإلكتروني أو كلمة المرور غير صحيحة."), ("This account is not active.", "هذا الحساب غير مفعّل."),
    ("Please sign in to continue.", "من فضلك سجّل الدخول للمتابعة."), ("Your session has expired. Please sign in again.", "انتهت جلستك. سجّل الدخول من جديد."),
    ("Your session is not valid. Please sign in again.", "جلستك غير صالحة. سجّل الدخول من جديد."),
    ("Your role ({r}) does not have access to this area.", "دورك ({r}) لا يملك صلاحية الوصول لهذا القسم."),
    ("Too many requests. Please wait a moment and retry.", "طلبات كثيرة جدًا. انتظر قليلًا ثم أعد المحاولة."),
    ("Something went wrong on our side. The incident was logged; please try again.", "حدث خطأ من جانبنا وتم تسجيله. من فضلك حاول مرة أخرى."),
    ("Some inputs are not valid. Please check them and try again.", "بعض المدخلات غير صحيحة. راجعها وحاول مرة أخرى."),
    ("A user with this email already exists.", "يوجد مستخدم بنفس البريد الإلكتروني بالفعل."), ("Please enter a valid email address.", "من فضلك أدخل بريدًا إلكترونيًا صحيحًا."),
    ("A store manager needs at least one allowed location.", "مدير الفرع يحتاج فرعًا واحدًا مسموحًا على الأقل."), ("User not found.", "المستخدم غير موجود."),
    ("There must always be at least one active CEO account.", "يجب أن يبقى حساب CEO واحد مفعّل على الأقل."),
    ("Your current password is not correct.", "كلمة المرور الحالية غير صحيحة."), ("Choose a password that is different from the current one.", "اختر كلمة مرور مختلفة عن الحالية."),
    ("A data refresh is already running. Please wait for it to finish.", "يوجد تحديث بيانات قيد التشغيل. انتظر حتى ينتهي."),
    ("The configured company data folder does not exist or is not readable. Ask IT to check DATA_DIRECTORY.", "مجلد بيانات الشركة غير موجود أو لا يمكن قراءته. اطلب من فريق IT مراجعة DATA_DIRECTORY."),
    ("No CSV files were found in the company data folder. Copy the updated files there and try again.", "لا توجد ملفات CSV في مجلد بيانات الشركة. انسخ الملفات المحدثة إليه ثم حاول مرة أخرى."),
    ("This recommendation no longer exists.", "هذه التوصية لم تعد موجودة."), ("Product {p} was not found.", "المنتج {p} غير موجود."),
    ("Product {p} was not found in your accessible data.", "المنتج {p} غير موجود ضمن البيانات المتاحة لك."), ("Action not found.", "الإجراء غير موجود."), ("Alert not found.", "التنبيه غير موجود."),
    ("This product has no stock or sales in the locations you can access.", "هذا المنتج ليس له مخزون أو مبيعات في الأماكن المتاحة لك."), ("No size data for product {p}.", "لا توجد بيانات مقاسات للمنتج {p}."),
    ("HIGH STOCKOUT RISK - likely to run out before new stock can arrive.", "خطر نفاد مرتفع — مرجّح أن ينفد قبل وصول مخزون جديد."), ("Watch: stock is close to the reorder point.", "تنبيه: المخزون قريب من نقطة إعادة الطلب."),
    ("Transfers assume the inventory locations hold interchangeable physical stock. Transfer cost is not in the data and is taken from configuration.", "النقل يفترض أن مخزون الأماكن قابل للتبادل فعليًا. تكلفة النقل غير موجودة في البيانات وتؤخذ من الإعدادات."),
    ("These files are labelled as modelled/training data in their Data_Class column. Figures built on them are demonstrations, not company results.", "هذه الملفات موسومة كبيانات نموذجية/تدريبية في عمود Data_Class. الأرقام المبنية عليها للعرض التوضيحي وليست نتائج الشركة الفعلية."),
    ("Material purchases are below net sales.", "مشتريات الخامات أقل من صافي المبيعات."),
    ("Relationships shown are associations in the data. They do not prove that one problem caused another.", "العلاقات المعروضة ارتباطات في البيانات ولا تثبت أن مشكلة تسببت في أخرى."),
    ("Inventory productivity uses cost data your role cannot access.", "إنتاجية المخزون تعتمد على بيانات تكلفة لا يتاح دورك الوصول إليها."),
    ("Procurement details are not available to your role.", "تفاصيل المشتريات غير متاحة لدورك."), ("This recommendation is outside the locations you manage.", "هذه التوصية خارج الأماكن التي تديرها."),
    ("Only accepted recommendations can have a realised outcome.", "التوصيات المقبولة فقط يمكن تسجيل نتيجة فعلية لها."),
    ("Realised values are entered by users after acting on a recommendation. Nothing is assumed: an accepted recommendation with no recorded outcome counts as expected value only.",
     "القيم الفعلية يدخلها المستخدمون بعد تنفيذ التوصية. لا شيء يُفترض: التوصية المقبولة بلا نتيجة مسجلة تُحتسب كقيمة متوقعة فقط."),
    ("There is nothing to export for this dataset yet.", "لا يوجد ما يُصدَّر لهذه البيانات بعد."),
    ("The job failed. Details are in the server log.", "فشلت المهمة. التفاصيل في سجل الخادم."),
    ("The server was restarted while this job was running.", "أُعيد تشغيل الخادم أثناء تنفيذ هذه المهمة."),
    ("Material purchases in the last 12 months ({a}) exceed net sales ({b}). Purchase_Orders quantities or costs may not be on the same scale as sales; supplier cost figures should be read as relative, not absolute.",
     "مشتريات الخامات خلال آخر 12 شهر ({a}) تتجاوز صافي المبيعات ({b}). قد تكون كميات أو تكاليف أوامر الشراء بمقياس مختلف عن المبيعات؛ لذا تُقرأ تكاليف الموردين كأرقام نسبية لا مطلقة."),
    ("ESTIMATE: stockout days x trailing 90-day average daily sales x actual selling price. Average daily sales during a stockout month can be depressed, so this is conservative.",
     "تقدير: أيام النفاد × متوسط المبيعات اليومية لآخر 90 يوم × سعر البيع الفعلي. متوسط المبيعات خلال شهر النفاد قد يكون منخفضًا لذا التقدير متحفظ."),
]

# ---------------------------------------------------------------- commercial intelligence (leakage, supply readiness, allocation, discounts, command center)
TERMS.update({"Quality loss": "خسارة الجودة", "production": "الإنتاج", "quality": "الجودة", "stockouts": "نفاد المخزون", "discounts": "الخصومات", "returns": "المرتجعات",
              "Retail": "التجزئة", "Online": "الأونلاين", "Wholesale": "الجملة"})
RULES += [
    ("Stockout opportunity loss", "خسارة فرص البيع بسبب النفاد"), ("Discount leakage", "تسرّب الخصومات"), ("Returns & refunds", "المرتجعات والاسترداد"), ("Production & print waste", "هدر الإنتاج والطباعة"),
    ("Quality loss", "خسارة الجودة"),
    ("Stockout days x trailing 90-day daily sales x gross profit per unit. Conservative: sales are depressed during a stockout.", "أيام النفاد × متوسط المبيعات اليومية لآخر 90 يوم × الربح الإجمالي للوحدة. تقدير متحفظ لأن المبيعات تنخفض أثناء النفاد."),
    ("Discount value granted above the comfort band in Retail and Online. Assumes no volume lift, which is what the data shows.", "قيمة الخصم الممنوح فوق النطاق المريح في التجزئة والأونلاين. يفترض عدم وجود زيادة في الكميات، وهو ما تُظهره البيانات."),
    ("Estimated loss on rejected units from QC inspections (Quality file), attributed to the units the sales ledger can account for.", "الخسارة المقدّرة على الوحدات المرفوضة في فحوص الجودة (ملف الجودة)، منسوبة إلى الوحدات التي يغطيها سجل المبيعات."),
    ("Gross profit lost on restocked returns plus refunds on quality-related returns.", "الربح الإجمالي المفقود على المرتجعات المعاد تخزينها بالإضافة إلى استرداد مرتجعات الجودة."),
    ("Rejected production and print units at unit cost, plus print rework cost, attributed to the units the sales ledger can account for.", "وحدات الإنتاج والطباعة المرفوضة بتكلفة الوحدة، مضافًا إليها تكلفة إعادة الطباعة، منسوبة إلى الوحدات التي يغطيها سجل المبيعات."),
    ("Quality inspection losses and production rejects come from different files and may partly overlap; they are shown separately and added without netting.", "خسائر فحوص الجودة ومرفوضات الإنتاج من ملفات مختلفة وقد تتداخل جزئيًا؛ تُعرض منفصلة وتُجمع دون خصم التداخل."),
    ("Wholesale discounts are a structural price tier and are not counted as leakage.", "خصومات الجملة شريحة سعرية ثابتة ولا تُحتسب كتسرّب."),
    ("Leakage is what already happened in the last 12 months. It is not the same as recoverable profit: only part of it can be recovered.", "التسرّب هو ما حدث فعلًا خلال آخر 12 شهرًا. وهو ليس الربح القابل للاسترداد: يمكن استرداد جزء منه فقط."),
    ("{a} (12 months)", "{a} (12 شهرًا)"),
    ("Forward-looking estimate: gross profit that stock cannot cover at stock-risk locations (lead time + 14 days) plus the expected loss on stock unlikely to sell.", "تقدير مستقبلي: الربح الإجمالي الذي لا يغطيه المخزون في الأماكن المعرضة للنفاد (مدة التوريد + 14 يومًا) مضافًا إليه الخسارة المتوقعة على مخزون يُستبعد بيعه."),
    ("Factory records cover more units than the sales ledger. Quality and production leakage are attributed per product by min(1, units sold / units produced); unscaled values are shown for transparency.", "سجلات المصنع تغطي وحدات أكثر من سجل المبيعات. يُنسب تسرّب الجودة والإنتاج لكل منتج بنسبة min(1، المباع ÷ المنتج)؛ وتُعرض القيم قبل التعديل للشفافية."),
    # supply readiness
    ("No raw-material stock on hand exists in the data: requirement and supplier reliability are reported, not a physical shortage.", "لا توجد بيانات عن مخزون الخامات الفعلي: يعرض النظام الاحتياج وموثوقية الموردين، وليس عجزًا فعليًا."),
    ("Requirement uses the demand forecast and Product_BOM quantities as supplied; BOM is a modelled training BOM.", "يعتمد الاحتياج على توقع الطلب وكميات قائمة المواد (BOM) كما وردت؛ وقائمة المواد هنا نموذجية للتدريب."),
    ("Supplier risk is based on the last 12 months of purchase orders: lateness vs promised date, average delay when late, and rejected share.", "مخاطر الموردين مبنية على أوامر الشراء لآخر 12 شهرًا: التأخر عن الموعد المتفق عليه، ومتوسط التأخير عند التأخر، ونسبة المرفوض."),
    ("Order at least {n} days ahead of need and keep a buffer: {p}% of recent purchase orders arrived late", "اطلب قبل الحاجة بـ {n} يومًا على الأقل واحتفظ بمخزون أمان: {p}% من أوامر الشراء الأخيرة وصلت متأخرة"),
    ("No change needed: supplier delivery is reliable", "لا حاجة لتغيير: توريد المورد موثوق"),
    ("Factory, quality and suppliers look able to meet the replenishment.", "المصنع والجودة والموردون قادرون على تلبية إعادة التوريد."),
    ("Replenishment may be delayed", "قد تتأخر إعادة التوريد"), ("Watch", "مراقبة"),
    ("production bottleneck: {b}", "اختناق في الإنتاج: {b}"), ("{p} of recent production orders ran late", "{p} من أوامر الإنتاج الأخيرة تأخرت"),
    ("depends on {m} (supplier risk {r}/100)", "يعتمد على {m} (مخاطر المورد {r}/100)"), ("high quality reject rate", "معدل رفض جودة مرتفع"),
    # allocation
    ("Wholesale is contract-driven: confirm commitments before moving stock out of the Wholesale Desk. The planning horizon is the target cover (45 days by default) or lead time + 14 days, whichever is longer. Demand is the forecast pace per channel; profit per unit is each channel's actual gross profit per unit (last 180 days).",
     "الجملة تعتمد على تعاقدات: أكّد الالتزامات قبل نقل مخزون من مكتب الجملة. أفق التخطيط هو التغطية المستهدفة (45 يومًا افتراضيًا) أو مدة التوريد + 14 يومًا، أيهما أطول. الطلب هو وتيرة التوقع لكل قناة؛ والربح للوحدة هو الربح الإجمالي الفعلي للوحدة في كل قناة (آخر 180 يومًا)."),
    ("ESTIMATE: extra gross profit over the planning horizon if stock sits where profit per unit is highest, assuming demand follows the forecast pace.", "تقدير: ربح إجمالي إضافي خلال أفق التخطيط إذا وُضع المخزون حيث الربح للوحدة الأعلى، بافتراض أن الطلب يتبع وتيرة التوقع."),
    # discounts
    ("Discount depth differs mostly by channel, so every channel is analysed separately.", "عمق الخصم يختلف أساسًا بحسب القناة، لذلك تُحلَّل كل قناة على حدة."),
    ("The volume test compares months of the SAME product (with month effects removed). It is an association, not a proven price elasticity.", "اختبار الكميات يقارن شهور نفس المنتج (بعد إزالة أثر الموسم). هو ارتباط وليس مرونة سعرية مُثبتة."),
    ("Seasonal offers, campaigns and stock availability can move volume and discount together and are not fully separable in this data.", "العروض الموسمية والحملات وتوفر المخزون قد تحرّك الكميات والخصم معًا ولا يمكن فصلها تمامًا في هذه البيانات."),
    ("In Retail and Online, deeper discounts did not produce more units, but every extra discount step cost gross profit. Keep discounts at or below the comfort band unless a campaign proves its lift.",
     "في التجزئة والأونلاين، الخصومات الأعمق لم تُنتج وحدات أكثر، لكن كل درجة خصم إضافية كلّفت ربحًا إجماليًا. أبقِ الخصومات عند النطاق المريح أو أقل إلا إذا أثبتت حملة أثرها."),
    ("Deeper discounts are associated with more units in at least one channel: compare the break-even lift with the measured lift before deepening any discount.", "الخصومات الأعمق مرتبطة بوحدات أكثر في قناة واحدة على الأقل: قارن الزيادة اللازمة للتعادل بالزيادة المقاسة قبل تعميق أي خصم."),
    ("Not enough variation in discount depth to test.", "لا يوجد تباين كافٍ في عمق الخصم للاختبار."),
    ("No measurable volume lift from deeper discounts (the effect cannot be told apart from zero).", "لا توجد زيادة قابلة للقياس في الكميات من الخصومات الأعمق (الأثر لا يمكن تمييزه عن الصفر)."),
    ("Deeper discounts are associated with more units.", "الخصومات الأعمق مرتبطة بوحدات أكثر."), ("Deeper discounts are associated with fewer units.", "الخصومات الأعمق مرتبطة بوحدات أقل."),
    ("Wholesale discounts are a structural price tier (28-38%) and are not tested as a promotion.", "خصومات الجملة شريحة سعرية ثابتة (28-38%) ولا تُختبر كترويج."),
    # command center
    ("Last 12 months: QC losses + production and print waste", "آخر 12 شهرًا: خسائر الفحص + هدر الإنتاج والطباعة"),
    ("{n} products at high risk of running out", "{n} منتجات معرضة بشدة للنفاد"), ("{n} products at high dead-stock risk", "{n} منتجات معرضة بشدة لخطر المخزون الراكد"), ("{n} materials with high supplier risk", "{n} خامات بمخاطر مورد مرتفعة"),
    ("Advance purchase of {m}", "تبكير شراء {m}"), ("Cap discounts on {p}", "وضع سقف للخصومات على {p}"), ("Investigate leakage on {p}", "فحص التسرّب في {p}"),
    ("{label} is the biggest leak ({share} of leakage)", "{label} هو أكبر مصدر تسرّب ({share} من التسرّب)"),
    ("Start with {p}, where {d} is the main driver", "ابدأ بـ {p}، حيث {d} هو المحرك الرئيسي"),
    ("Keep Retail and Online discounts at or below {cap}; average is {avg} today", "أبقِ خصومات التجزئة والأونلاين عند {cap} أو أقل؛ المتوسط اليوم {avg}"),
    ("{e} of discount was granted above the {c} comfort band in 12 months, with no measurable volume lift", "تم منح خصم بقيمة {e} فوق النطاق المريح {c} خلال 12 شهرًا دون زيادة قابلة للقياس في الكميات"),
    ("Main supplier {s}; average delay when late {d} days; {n} products depend on it", "المورد الرئيسي {s}؛ متوسط التأخير عند التأخر {d} يومًا؛ {n} منتجات تعتمد عليه"),
    ("Profit that depends on this material (not a saving)", "ربح يعتمد على هذه الخامة (وليس توفيرًا)"), ("Discount given away above the comfort band", "خصم ممنوح فوق النطاق المريح"),
    ("Leaked in the last 12 months (not a saving)", "تسرّب خلال آخر 12 شهرًا (وليس توفيرًا)"), ("Leakage in the last 12 months", "تسرّب خلال آخر 12 شهرًا"), ("Expected impact (estimate)", "الأثر المتوقع (تقدير)"),
]

RULES += [
    ("Demand follows the forecast pace for the next 90 days.", "افتراض أن الطلب يتبع وتيرة التوقع للـ 90 يومًا القادمة."),
    ("Volume change assumed: {x} per 5 points of discount (the data shows no measurable lift, so 0% is the supported default).", "تغيّر الكميات المفترض: {x} لكل 5 نقاط خصم (البيانات لا تُظهر زيادة قابلة للقياس، لذلك 0% هو الافتراض المدعوم)."),
    ("Unit cost stays the same.", "تكلفة الوحدة ثابتة."),
    ("Planning horizon is {h} days (target cover or lead time + 14 days, whichever is longer).", "أفق التخطيط {h} يومًا (التغطية المستهدفة أو مدة التوريد + 14 يومًا، أيهما أطول)."),
    ("Only the demand that current stock cannot cover is counted as sold; extra units beyond that stay in stock.", "يُحتسب كمبيع فقط الطلب الذي لا يغطيه المخزون الحالي؛ والوحدات الزائدة عن ذلك تبقى في المخزون."),
    ("Holding cost uses the configured annual capital cost on unit cost.", "تكلفة الاحتفاظ تعتمد على تكلفة رأس المال السنوية المضبوطة مطبّقة على تكلفة الوحدة."),
    ("Cost per unit = quantity in the bill of materials x average purchase price of the material.", "تكلفة الوحدة = الكمية في قائمة المواد × متوسط سعر شراء الخامة."),
    ("{p} of the increase is recovered through selling prices.", "{p} من الزيادة يتم استردادها عبر أسعار البيع."),
    ("Unknown product.", "منتج غير معروف."), ("Unknown material.", "خامة غير معروفة."), ("Unknown scenario.", "سيناريو غير معروف."),
    ("This product has no recent sales in that channel, so the discount cannot be simulated.", "لا توجد مبيعات حديثة لهذا المنتج في هذه القناة، لذلك لا يمكن محاكاة الخصم."),
    ("Discount must be between 0% and 60%.", "يجب أن يكون الخصم بين 0% و60%."), ("Enter a number of units above zero.", "أدخل عدد وحدات أكبر من صفر."),
    ("Price change must be between -50% and +200%.", "يجب أن يكون تغيّر السعر بين -50% و+200%."),
]

RULES += [
    ("Customers are compared with their own buying rhythm, so a monthly buyer and a yearly buyer are judged differently.", "يُقارَن كل عميل بإيقاع شرائه هو، فيُحكم على المشتري الشهري والسنوي بشكل مختلف."),
    ("Profit at risk from overdue customers is what these customers brought in the last 12 months; it is exposure, not a forecast of loss.", "الربح المعرّض للخطر من العملاء المتأخرين هو ما جلبوه خلال آخر 12 شهرًا؛ وهو تعرّض وليس توقعًا للخسارة."),
    ("Customer records in the supplied files are modelled/anonymised training data. No names or contact details are used.", "سجلات العملاء في الملفات المقدمة بيانات تدريب نموذجية ومجهولة الهوية. لا تُستخدم أسماء أو بيانات تواصل."),
    ("Acquisition channels behave almost the same in this data (repeat rate differs by under {n} points), so the source of a customer does not predict their value here.", "قنوات اكتساب العملاء تتصرف بشكل متقارب جدًا في هذه البيانات (معدل التكرار يختلف بأقل من {n} نقطة)، لذلك مصدر العميل لا يتنبأ بقيمته هنا."),
    ("Acquisition channels differ in repeat rate: compare cost per customer before moving budget.", "قنوات الاكتساب تختلف في معدل التكرار: قارن تكلفة العميل قبل نقل الميزانية."),
    ("Unplanned downtime and production delays do not move together month to month (correlation near zero). Maintenance alone is unlikely to fix delays.", "التوقف غير المخطط وتأخير الإنتاج لا يتحركان معًا من شهر لآخر (ارتباط قريب من الصفر). من غير المرجح أن تحل الصيانة وحدها مشكلة التأخير."),
    ("Months with more unplanned downtime tend to have longer production delays.", "الشهور ذات التوقف غير المخطط الأكبر تميل إلى تأخير إنتاج أطول."),
    ("Not enough months to compare downtime with delays.", "لا توجد شهور كافية لمقارنة التوقف بالتأخير."),
    ("Compare stages: the stage with the most downtime is not always the stage that causes the delays.", "قارن المراحل: المرحلة الأكثر توقفًا ليست دائمًا المرحلة التي تسبب التأخير."),
]

# ---- V5 workspace (notifications, command map, time machine, decision board, reports catalogue)
RULES += [
    ("Awaiting approval · estimated {v} EGP (estimate, confidence {c}%)", "بانتظار الاعتماد · تقدير {v} ج.م (تقدير، الثقة {c}%)"),
    ("Business data is out of date", "بيانات العمل قديمة"), ("No data imported yet", "لم تُستورد أي بيانات بعد"), ("Status: {s}", "الحالة: {s}"),
    ("Open for {d} days · status {s} · owner {o}", "مفتوح منذ {d} يومًا · الحالة {s} · المسؤول {o}"),
    ("Outcome {s}: {k}", "النتيجة ({s}): {k}"), ("Measurement finished.", "اكتمل القياس."),
    ("Measured effect {v} EGP gross profit; stands out from placebo tests.", "الأثر المقاس {v} ج.م من إجمالي الربح؛ ويتميّز عن اختبارات المقارنة الوهمية."),
    ("Measured effect {v} EGP gross profit; not distinguishable from chance, so nothing is claimed.", "الأثر المقاس {v} ج.م من إجمالي الربح؛ لا يمكن تمييزه عن الصدفة، لذلك لا يُنسب أي أثر."),
    ("Actions have no due date in the data model, so 'delayed' means open for {n}+ days.", "الإجراءات لا تحمل تاريخ استحقاق في النموذج، لذا «متأخر» تعني مفتوحًا منذ {n} يومًا أو أكثر."),
    ("Edges come from stock/sales rows, the bill of materials, purchase orders and open recommendations. Nothing else is connected.", "الخطوط تأتي من صفوف المخزون والمبيعات وقائمة المواد وأوامر الشراء والتوصيات المفتوحة فقط. لا يوجد أي ربط آخر."),
    ("Business units have no link to locations, products or suppliers in the data, so they are shown without connections.", "وحدات الأعمال غير مرتبطة بالفروع أو المنتجات أو الموردين في البيانات، لذلك تظهر بدون خطوط ربط."),
    ("Decision values are estimates, not realised results.", "قيم القرارات تقديرية وليست نتائج محققة."),
    ("History is rebuilt from the raw monthly tables. Recommendation and alert snapshots are stored as latest-only, so what the system recommended in an earlier month is NOT available.", "التاريخ يُعاد بناؤه من الجداول الشهرية الخام. لقطات التوصيات والتنبيهات تحتفظ بالأحدث فقط، لذلك ما أوصى به النظام في شهر سابق غير متاح."),
    ("Event markers are only campaigns, approvals, executions, measured outcomes and data refreshes that were actually recorded.", "علامات الأحداث هي فقط الحملات والاعتمادات والتنفيذ والنتائج المقاسة وتحديثات البيانات التي سُجّلت فعلًا."),
    ("Your role cannot see this metric.", "دورك لا يسمح برؤية هذا المؤشر."), ("No history in the data for this selection.", "لا يوجد تاريخ في البيانات لهذا الاختيار."),
    ("{c} starts ({p})", "بدء حملة {c} ({p})"), ("{c} ends", "انتهاء حملة {c}"), ("Decision approved by {u}", "اعتمد {u} القرار"), ("Decision marked as executed", "تم تسجيل تنفيذ القرار"),
    ("Outcome {s}", "النتيجة {s}"), ("Data refresh {s} ({n} rows)", "تحديث البيانات: {s} ({n} صف)"),
    ("Cards move only through the existing approval and action endpoints. Dragging a card asks for confirmation and the server decides.", "تتحرك البطاقات فقط عبر مسارات الاعتماد والإجراءات الحالية. السحب يطلب تأكيدًا والقرار النهائي للخادم."),
    ("Values on open and approved cards are estimates. Only the Measured lane can show a measured effect.", "القيم على البطاقات المفتوحة والمعتمدة تقديرية. فقط مسار «تم القياس» يعرض أثرًا مقاسًا."),
    ("Detected by the {e} engine (estimate)", "اكتُشف بواسطة محرك {e} (تقدير)"), ("Approved", "تم الاعتماد"), ("Deferred", "تم التأجيل"), ("Rejected", "تم الرفض"),
    ("Realised value entered manually", "تم إدخال القيمة المحققة يدويًا"), ("Action item created · now {s}", "أُنشئ بند إجراء · الحالة الآن {s}"),
    ("Execution recorded; measurement window started", "سُجّل التنفيذ وبدأت نافذة القياس"), ("Measurement {s}", "القياس: {s}"),
    ("Decisions and estimated value", "القرارات والقيمة التقديرية"), ("Product performance (12 months)", "أداء المنتجات (12 شهرًا)"), ("Dead and slow stock", "المخزون الراكد وبطيء الحركة"),
    ("Supplier true-cost ranking", "ترتيب الموردين حسب التكلفة الحقيقية"), ("one row per open/accepted/deferred decision", "صف لكل قرار مفتوح أو معتمد أو مؤجل"), ("one row per product", "صف لكل منتج"),
    ("one row per product x location", "صف لكل منتج في كل فرع"), ("one row per supplier", "صف لكل مورد"), ("after each data refresh", "بعد كل تحديث للبيانات"),
    ("Exports use the signed-in user's role: cost columns and location rows are filtered exactly as in the application.", "التصدير يتبع دور المستخدم: أعمدة التكلفة وصفوف الفروع تُرشَّح تمامًا كما في التطبيق."),
    ("Power BI Desktop or Report Server can read the CSV/XLSX files or the API on the company network. Embedding Power BI reports inside this application is NOT implemented.", "يمكن لـ Power BI Desktop أو Report Server قراءة ملفات CSV/XLSX أو الـ API داخل شبكة الشركة. تضمين تقارير Power BI داخل هذا التطبيق غير منفّذ."),
    ("Embedding needs a Power BI Report Server (on-premise) or licensed capacity, a service account and an agreed security model; those are infrastructure decisions for the company's IT.", "التضمين يحتاج Power BI Report Server (محلي) أو سعة مرخّصة وحساب خدمة ونموذج أمان متفق عليه؛ وهذه قرارات بنية تحتية لقسم تقنية المعلومات."),
    ("No company data is sent to any cloud service by this application.", "هذا التطبيق لا يرسل أي بيانات للشركة إلى أي خدمة سحابية."),
    # ------------------------------------------------ V5 workspaces (war room, command map, time machine, notifications, analytics)
    ("Awaiting approval · estimated {n} EGP (estimate, confidence {c}%)", "بانتظار الاعتماد · تقدير {n} ج.م (تقدير، الثقة {c}%)"),
    ("Decision marked as executed", "تم تسجيل القرار كمنفَّذ"), ("Execution recorded; measurement window started", "تم تسجيل التنفيذ وبدأت فترة القياس"),
    ("Actions have no due date in the data model, so 'delayed' means open for {n}+ days.", "بنود الإجراءات ليس لها تاريخ استحقاق في البيانات، لذلك «متأخر» تعني مفتوحًا منذ {n}+ يومًا."),
    ("Measurement finished.", "اكتمل القياس."), ("Realised value entered manually", "قيمة محققة أُدخلت يدويًا"),
    ("Business data is out of date", "بيانات الأعمال قديمة"), ("No data imported yet", "لم يتم استيراد بيانات بعد"), ("No history in the data for this selection.", "لا يوجد تاريخ في البيانات لهذا الاختيار."),
    ("Your role cannot see this metric.", "دورك لا يسمح برؤية هذا المؤشر."), ("That location is outside the locations you manage.", "هذا الفرع خارج الفروع التي تديرها."),
    ("That product was not found in your accessible data.", "لم يُعثر على هذا المنتج ضمن البيانات المتاحة لك."),
    ("Your role does not have access to decisions.", "دورك لا يملك صلاحية الوصول إلى القرارات."), ("Your role does not have access to product details.", "دورك لا يملك صلاحية الوصول إلى تفاصيل المنتجات."),
    ("Your role does not have access to the command map.", "دورك لا يملك صلاحية الوصول إلى خريطة القيادة."), ("Your role does not have access to the decision board.", "دورك لا يملك صلاحية الوصول إلى لوحة القرارات."),
    ("Your role does not have access to the time machine.", "دورك لا يملك صلاحية الوصول إلى آلة الزمن."),
    ("Edges come from stock/sales rows, the bill of materials, purchase orders and open recommendations. Nothing else is connected.", "الروابط مأخوذة من صفوف المخزون والمبيعات وقوائم المواد وأوامر الشراء والتوصيات المفتوحة. لا يوجد أي ربط غير ذلك."),
    ("Business units have no link to locations, products or suppliers in the data, so they are shown without connections.", "وحدات الأعمال غير مرتبطة بالفروع أو المنتجات أو الموردين في البيانات، لذلك تظهر بدون روابط."),
    ("Decision values are estimates, not realised results.", "قيم القرارات تقديرية وليست نتائج محققة."),
    ("Cards move only through the existing approval and action endpoints. Dragging a card asks for confirmation and the server decides.", "تتحرك البطاقات فقط عبر مسارات الاعتماد والإجراءات الحالية. سحب البطاقة يطلب تأكيدًا والخادم هو من يقرر."),
    ("Values on open and approved cards are estimates. Only the Measured lane can show a measured effect.", "القيم على البطاقات المفتوحة والمعتمدة تقديرية. فقط مسار «تم القياس» يمكنه عرض أثر مقاس."),
    ("History is rebuilt from the raw monthly tables. Recommendation and alert snapshots are stored as latest-only, so what the system recommended in an earlier month is NOT available.", "التاريخ مُعاد بناؤه من الجداول الشهرية الخام. لقطات التوصيات والتنبيهات تُحفظ كأحدث نسخة فقط، لذلك ما أوصى به النظام في شهر سابق غير متاح."),
    ("Event markers are only campaigns, approvals, executions, measured outcomes and data refreshes that were actually recorded.", "علامات الأحداث هي فقط الحملات والاعتمادات والتنفيذات والنتائج المقاسة وتحديثات البيانات التي سُجلت فعلًا."),
    ("Decisions and estimated value", "القرارات والقيمة التقديرية"), ("Product performance (12 months)", "أداء المنتجات (12 شهرًا)"), ("Dead and slow stock", "المخزون الراكد وبطيء الحركة"), ("Supplier true-cost ranking", "ترتيب الموردين حسب التكلفة الحقيقية"),
    ("one row per open/accepted/deferred decision", "صف لكل قرار مفتوح أو معتمد أو مؤجل"), ("one row per product", "صف لكل منتج"),
]


_PLACEHOLDER = re.compile(r"\{(\w+)\}")


def _compile(en: str) -> re.Pattern:
    parts, last = [], 0
    for m in _PLACEHOLDER.finditer(en):
        parts.append(re.escape(en[last:m.start()]))
        parts.append(f"(?P<{m.group(1)}>.+?)")
        last = m.end()
    parts.append(re.escape(en[last:]))
    return re.compile("^" + "".join(parts) + "$", re.S)


_COMPILED = sorted(((_compile(en), ar, len(_PLACEHOLDER.sub("", en))) for en, ar in RULES), key=lambda t: -t[2])
_EXACT = {en: ar for en, ar in RULES if "{" not in en}
_EGP = re.compile(r"EGP\s?(-?[\d,]+(?:\.\d+)?[KM]?)")
_UNITS = [(re.compile(r"\bdays? of cover\b"), "يوم تغطية")]


def _egp(s: str) -> str:
    return _EGP.sub(lambda m: f"{m.group(1)} ج.م", s)


_ALERT_BODY = re.compile(r"^(?P<problem>.+?)\. (?P<why>.*?) ?Expected impact (?P<egp>EGP -?[\d,.]+)\.$", re.S)


def _val(v: str) -> str:
    """Captured placeholder text: full known sentences are translated, fixed vocabulary is mapped, anything else (names, numbers) is kept."""
    if len(v) > 12 and v in _EXACT:
        return _egp(_EXACT[v])
    return _term(v)


@lru_cache(maxsize=20000)
def tr(s: str) -> str:
    """Translate one string. Returns the input unchanged when no rule matches."""
    if not s or len(s) < 4:
        return s
    if s in _EXACT:
        return _egp(_EXACT[s])
    for rx, ar, _ in _COMPILED:
        m = rx.match(s)
        if m:
            try:
                return _egp(ar.format(**{k: _val(v) for k, v in m.groupdict().items()}))
            except Exception:
                return s
    m = _ALERT_BODY.match(s)      # Alert Center body: "<problem>. <first reason> Expected impact EGP X."
    if m:
        why = tr(m.group("why")).rstrip(". ") + ". " if m.group("why") else ""
        return f"{tr(m.group('problem'))}. {why}" + _egp(f"الأثر المتوقع {m.group('egp')}.")
    return s


SKIP_KEYS = {"rec_key", "alert_key", "id", "email", "user_email", "owner_email", "product_name", "location_name", "supplier_name", "campaign_name", "sku", "product_id", "location_id",
             "defect_type", "root_cause", "stage", "return_reason", "platform", "from_name", "to_name", "machine_id", "bottleneck", "token", "access_token", "refresh_token", "full_name"}


def translate_payload(obj, key: str | None = None):
    """Walk a JSON document and translate every sentence that has a rule. Identifier-like fields are left alone."""
    if isinstance(obj, str):
        return obj if key in SKIP_KEYS else tr(obj)
    if isinstance(obj, list):
        return [translate_payload(x, key) for x in obj]
    if isinstance(obj, dict):
        return {k: translate_payload(v, k) for k, v in obj.items()}
    return obj
