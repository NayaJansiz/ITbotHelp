# مرجع المواد ومجلدات المحاضرات (القسم 11)

> **إضافة v2** (ليست من المصادر الأصلية للدليل): جدول مواد البوت (id والسنة والفصل والمادة والاختصاص والأعداد) لم يعد منسوخاً يدوياً هنا لأنه يتقادم مع كل نشر؛ هو الآن في `SNAPSHOT.md` ويُولَّد من bot.db نفسه بالأمر `python tools/check_bot.py bot.db --snapshot SNAPSHOT.md`. الجدول الأصلي بتاريخ 2026-10-16 مطابق لما ولّدته الأداة في نفس اليوم (عدد المواد 40 والأعداد الكلية والظاهرة).

## 11. مرجع المواد ومجلدات المحاضرات

### مستودع المحاضرات
• الرابط: https://github.com/homs-uni/lecture-site-engine (عام). استنسخه بـ git clone --depth 1 لأن صفحة الويب تمنع الجلب (fetch).
• البنية: subjects/year-N/<مجلد المادة>/lectures/par*.md، وأحياناً DAWRAT/exams.md (محلول جزئياً أو كلياً في بعض المواد).
• أسماء المجلدات ليست بالضرورة نفس أسماء المواد في البوت، فابحث عن الموضوع في كل المجلدات قبل أن تقول إنه غير موجود.

### ربط المواد بمجلدات المحاضرات (كما تم التأكد منه أثناء العمل)

| المادة (id) | مجلد المحاضرات | ملاحظات |
|---|---|---|
| مترجمات (16) | year-3/1-compiler-principles | أرقام المحاضرات تختلف عن أرقام الملفات: par2 = م4، par3 = م5، par4 = م6، par5 = م7، par6 = م8، par7 = م9 |
| ذكاء صنعي (15) | year-3/2-ai-theory |  |
| برمجة متقدمة 2 (14) | year-3/advanced-programming-2 |  |
| اتصالات رقمية (11) | year-3/digital-communications |  |
| لغة انكليزي تخصصية 1 (13) | year-3/computer-networks | تم تأكيد الربط من المستخدم (لا تخلطه مع year-4/computer-networks). par1 = م1، par2 = م2، par3 = م4، par4 = م6، par5 = م5، par6 = م9، par7 = م10، par8 = م11. فيه DAWRAT/exams.md محلول |
| بحوث العمليات 2 (12) | year-3/operations-research-2 | لا يوجد نص محاضرات، فقط manifest |
| بنيان 2 (17) وهندسة البرمجيات 1 (18) واتومات (19) | لا يوجد مجلد | الإجابات تكون inferred-from-concept أو من الصور (اتومات) |
| خوارزميات 1 (8) | year-2/algorithms-data-structures | تغطي D&C وDP وgreedy وgraphs فقط. مواضيع أخرى لها وُجدت في مجلدات أخرى: 1-discrete-mathematics/par9 (أشجار التعبير، preorder وpostorder) و2-programming-1/par1 (برج هانوي، م12) |
| برمجة الويب (9) | year-2/web-applications | HTTP وJS متقدم وTypeScript وNode وReact وExpress وWebSocket وGit وFlexbox وGrid. لا يوجد HTML/CSS أساسي، والمحاضرات 3 و5 و9 مفقودة |
| احتمالات و احصاء (10) | year-2/statistics-probability | 7 ملفات |

مجلدات بلا محاضرات نهائياً (ملف manifest فقط أو لا شيء): السنة 1: electronic-circuits-1 وelectronic-circuits-2؛ السنة 2: computer-architecture وenglish-ict؛ السنة 3: operations-research-2؛ السنة 4: computer-networks وfuzzy-logic وnetwork-analysis-design وnetwork-management؛ السنة 5: system-engineering. إجابات هذه المواد يجب أن تكون موسومة inferred-from-concept.
مجلدات السنة 4 الموجودة في المستودع (بتاريخ 2026-10-16، لم يُتحقق بعد من ربطها بالمواد): 1-applied-stats-data-science و1-os-2-theory وandroid-dev-fundamentals وaudio-processing-theory وcomputer-networks وdatabases-2 وfuzzy-logic وinformation-systems وnetwork-analysis-design وnetwork-management وneural-networks-lectures وparallel-concurrent-programming وprogramming-languages وsoftware-engineering-2.
مجلدات السنة 1 الموجودة في المستودع: 1-numerical-analysis-1 و2-mabade2-th وMath_2 وelectronic-circuits-1 وelectronic-circuits-2 وinteractions-1-units-6-9 وprogramming-2 وprogramming_1. مجلدات السنة 5: 1-kdd وdistributed-systems-theory وinformation-security وnetwork-security وproject-management وsystem-engineering وwireless-networks.
