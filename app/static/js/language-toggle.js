(function () {
  'use strict';

  const pairs = {
    'Dashboard': 'لوحة التحكم',
    'Open': 'فتح',
    'Back': 'الرجوع',
    'Previous version': 'نسخة قديمة',
    'Current version': 'النسخة الحالية',
    'Create new invoice': 'انشاء مستخلص جديد',
    'Edit': 'تعديل',
    'Add main item': 'اضافة بند رئيسي',
    'Delete category': 'حذف البند',
    'Sub-item': 'بند فرعي',
    'Completion percentage': 'نسبة الانجاز',
    'Category total': 'إجمالي البند',
    'Next version': 'النسخة التالية',
    'View next version': 'عرض النسخة التالية',
    'No next version.': 'لا توجد نسخة تالية.',
    'Edit accounting': 'تعديل الحسابات',
    'Total + taxes': 'الاجمالي + الضرائب',
    'Total previously paid': 'مجموع ما سبق صرفه',
    'Total deductions and previously paid': 'مجموع الخصومات و ما سبق صرفه',
    'Net invoice': 'صافي المستخلص',
    'Add main category to edit': 'اضافة البند للتعديل',
    'Main category title': 'عنوان البند الرئيسي',
    'Sub-items': 'البنود الفرعية',
    'Sub-item title': 'عنوان البند الفرعي',
    'Tax name': 'اسم الضريبة',
    'Deduction name': 'اسم الخصم',
    'Amount in EGP': 'الكمية بالجنية',
    'Choose invoice file': 'اختر ملف المستخلص',
    'Upload Excel file': 'رفع ملف Excel',
    'Tax rate': 'النسبة',
    'User management': 'ادارة المستخدمين',
    'Human resources management': 'ادارة الموارد البشرية',
    'Download backup': 'تحميل النسخة الاحتياطية',
    'Restore Database': 'استعادة قاعدة البيانات',
    'Account': 'الحساب',
    'Logout': 'تسجيل الخروج',
    'Users': 'المستخدمون',
    'Invoices': 'المستخلصات',
    'HR Management': 'إدارة الموارد البشرية',
    'Back to dashboard': 'العودة للوحة التحكم',
    'الرجوع': 'Back',
    'Candidates': 'المتقدمون',
    'Open CV': 'فتح السيرة الذاتية',
    'Delete': 'حذف',
    'No candidates submitted yet': 'لم يتم تقديم متقدمين بعد',
    'Email:': 'البريد الإلكتروني:',
    'Phone:': 'الهاتف:',
    'Age:': 'العمر:',
    'Show': 'إظهار',
    'Hide': 'إخفاء',
    'Sign in': 'تسجيل الدخول',
    'Signing in...': 'جار تسجيل الدخول...',
    'Save': 'حفظ',
    'Cancel': 'إلغاء',
    'Details & search': 'التفاصيل والبحث',
    'Details and search': 'التفاصيل و البحث',
    'Add +': '+ إضافة',
    '+ Add': '+ إضافة',
    'Taxes (optional)': 'الضرائب (اختياري)',
    'Deductions (optional)': 'الخصومات (اختياري)',
    'Previously paid (optional)': 'ما سبق صرفه (اختياري)',
    'Add invoice': 'إضافة مستخلص',
    'Search': 'بحث',
    'Clear': 'مسح',
    'Download summary': 'تحميل الملخص',
    'Upload Excel': 'رفع Excel',
    'Add tax': 'اضافة ضريبة',
    'Add deduction': 'اضافة خصم',
    'Add payment': 'اضافة دفع',
    'Add category': 'اضافة بند',
    'Add sub-item': 'اضافة بند فرعي',
    'Value in EGP': 'قيمة بالجنية',
    'Amount': 'الكمية',
    'Percentage': 'نسبة مئوية',
    'Main and sub-items': 'البنود الرئيسية و الفرعية',
    '(optional)': '(اختياري)',
    'Add user': 'إضافة مستخدم',
    'Total users': 'مجموع المستخدمين',
    'Add User': 'إضافة مستخدم',
    'All users': 'جميع المستخدمين',
    'First name': 'الاسم الاول',
    'Last name': 'الاسم الاخير',
    'Search users': 'ابحث بالاسم أو الدور',
    'Active and inactive': 'نشط و غير نشط',
    'Name': 'الاسم',
    'Status': 'الحالة',
    'Permissions': 'الصلاحيات',
    'Add permission': 'اضافة صلاحية',
    'Add': 'اضافة',
    'Super Admin': 'مشرف عام',
    'Engineer Admin': 'مدير هندسي',
    'Accountant Admin': 'مدير حسابات',
    'Site Manager': 'مدير موقع',
    'Engineer': 'مهندس',
    'Accountant': 'محاسب',
    'super admin': 'مشرف عام',
    'eng admin': 'مدير هندسي',
    'acc admin': 'مدير حسابات',
    'site manager': 'مدير موقع',
    'engineer': 'مهندس',
    'accountant': 'محاسب',
    'Manage Users': 'إدارة المستخدمين',
    'Add Invoices': 'إضافة مستخلصات',
    'Delete Invoices': 'حذف المستخلصات',
    'Approve Invoices': 'اعتماد المستخلصات',
    'Edit Invoices': 'تعديل المستخلصات',
    'Manage accounting': 'إدارة الحسابات',
    'HR Management': 'إدارة الموارد البشرية',
    'View Edits': 'عرض التعديلات',
    'manage users': 'إدارة المستخدمين',
    'add invoices': 'إضافة مستخلصات',
    'delete invoices': 'حذف المستخلصات',
    'approve invoices': 'اعتماد المستخلصات',
    'edit invoices': 'تعديل المستخلصات',
    'accounting': 'إدارة الحسابات',
    'hr management': 'إدارة الموارد البشرية',
    'view edits': 'عرض التعديلات',
    'No matching users found': 'لا يوجد مستخدمين يطابق بحثك',
    'No users available.': 'لا يوجد مستخدمين.',
    'Adding...': 'جار الإضافة...',
    'Adding…': 'جار الإضافة…',
    'Activate': 'تفعيل',
    'Deactivate': 'إلغاء التفعيل',
    'Manage permissions': 'إدارة الصلاحيات',
    'No other users yet.': 'لا يوجد مستخدمون آخرون.',
    'Choose': 'اختر',
    'Choose a permission': 'اختر صلاحية',
    'No additional permissions': 'لا توجد صلاحيات إضافية',
    'No permissions assigned yet.': 'لم يتم تعيين صلاحيات بعد.',
    'Loading permissions...': 'جار تحميل الصلاحيات...',
    'Loading permissions…': 'جار تحميل الصلاحيات…',
    'Close permissions dialog': 'إغلاق نافذة الصلاحيات',
    'Generate PDF': 'إنشاء PDF',
    'Edit category title': 'تعديل عنوان البند',
    'Edit item title': 'تعديل عنوان البند الفرعي',
    'Loading previous version...': 'جار تحميل النسخة السابقة...',
    'Loading history...': 'جار تحميل السجل...',
    'Previous version': 'النسخة السابقة',
    'Next version': 'النسخة التالية',
    'Current version': 'النسخة الحالية',
    'Approved': 'تمت الموافقة',
    'Project name': 'اسم المشروع',
    'Invoice number': 'رقم المستخلص',
    'Contract': 'العقد',
    'Unit number': 'رقم الوحدة',
    'Job type': 'نوع العمل',
    'Contractor name': 'اسم المقاول',
    'Customer name': 'اسم العميل',
    'Updated by': 'تم التحديث بواسطة',
    'Updated at': 'تم التحديث في',
    'Main item': 'البند الرئيسي',
    'Sub item': 'البند الفرعي',
    'Unit type': 'نوع الوحدة',
    'Amount': 'الكمية',
    'Rate': 'الفئة',
    'Completion percentage': 'نسبة الإنجاز',
    'Total': 'الإجمالي',
    'Taxes': 'الضرائب',
    'Deductions': 'الخصومات',
    'Previously paid': 'ما سبق صرفه',
    'Category total': 'إجمالي البند',
    'Edits': 'التعديلات',
    'No items in this category': 'لا توجد عناصر في هذا البند',
    'No main categories in this invoice': 'لا توجد بنود رئيسية في هذا المستخلص',
    'Add tax': 'إضافة ضريبة',
    'Add deduction': 'إضافة خصم',
    'Add payment': 'إضافة دفع',
    'Value in EGP': 'القيمة بالجنيه',
    'Percentage': 'نسبة مئوية',
    'Payment details': 'تفاصيل الدفع',
    'Add category': 'إضافة بند',
    'Add sub-item': 'إضافة بند فرعي',
    'Delete item': 'حذف البند',
    'Delete category': 'حذف البند الرئيسي',
    'Approve': 'موافقة',
    'Approval': 'الموافقة',
    'Username': 'اسم المستخدم',
    'Password': 'كلمة المرور',
    'First name': 'الاسم الأول',
    'Last name': 'الاسم الأخير',
    'Role': 'الدور',
    'All users': 'جميع المستخدمين',
    'Active now': 'نشط الآن',
    'Active': 'نشط',
    'Inactive': 'غير نشط',
    'Total users': 'مجموع المستخدمين',
    'Search by name or role': 'ابحث بالاسم أو الدور'
  };

  const reversePairs = Object.fromEntries(Object.entries(pairs).map(([english, arabic]) => [arabic, english]));
  Object.assign(reversePairs, {
    'الاسم الاول': 'First name',
    'الاسم الاخير': 'Last name',
    'إضافة مستخدم': 'Add user',
    'ادارة المستخدمين': 'User management',
    'ادارة الموارد البشرية': 'Human resources management',
    'اضافة': 'Add',
    'اضافة صلاحية': 'Add permission',
    'لا يوجد مستخدمين يطابق بحثك': 'No matching users found',
    'لا يوجد مستخدمين.': 'No users available.',
    'رقم المستخلص': 'Invoice number',
    'المجموع': 'Total',
    'اجمالي الضرائب': 'Total taxes',
    'إجمالي الضرائب': 'Total taxes',
    'اجمالي الخصومات': 'Total deductions',
    'إجمالي الخصومات': 'Total deductions',
    'ما سبق صرفه': 'Previously paid',
    'الصافي': 'Net total',
    'تحميل ملخص': 'Download summary',
    'اضافة مستخلص': 'Add invoice',
    'مسح': 'Clear',
    'بحث': 'Search',
    '+ إضافة': '+ Add',
    'الرجوع': 'Back',
    'نسخة قديمة': 'Previous version',
    'النسخة الحالية': 'Current version',
    'انشاء مستخلص جديد': 'Create new invoice',
    'تعديل': 'Edit',
    'حفظ': 'Save',
    'الغاء': 'Cancel',
    'اضافة بند رئيسي': 'Add main item',
    'اضافة بند فرعي': 'Add sub-item',
    'اضافة ضريبة': 'Add tax',
    'إضافة ضريبة': 'Add tax',
    'اضافة خصم': 'Add deduction',
    'إضافة خصم': 'Add deduction',
    'اضافة دفع': 'Add payment',
    'إضافة دفع': 'Add payment',
    'اضافة بند': 'Add category',
    'إضافة بند': 'Add category',
    'إضافة مستخلص': 'Add invoice',
    'قيمة بالجنية': 'Value in EGP',
    'الكمية': 'Amount',
    'نسبة مئوية': 'Percentage',
    'القيمة': 'Value',
    'البنود الرئيسية و الفرعية': 'Main and sub-items',
    '(اختياري)': '(optional)',
    'الضرائب (اختياري)': 'Taxes (optional)',
    'الخصومات (اختياري)': 'Deductions (optional)',
    'ما سبق صرفه (اختياري)': 'Previously paid (optional)',
    'حذف البند': 'Delete category',
    'بند فرعي': 'Sub-item',
    'نسبة الانجاز': 'Completion percentage',
    'إجمالي البند': 'Category total',
    'النسخة التالية': 'Next version',
    'عرض النسخة التالية': 'View next version',
    'المستخلص السابق': 'Previous invoice',
    'الاجمالي:': 'Total:',
    'لا توجد نسخة تالية.': 'No next version.',
    'لا توجد نسخة سابقة.': 'No previous version.',
    'لا يمكن تحميل النسخة السابقة.': 'Unable to load the previous version.',
    'لا توجد تعديلات سابقة.': 'No previous edits.',
    'لا يمكن تحميل النسخ السابقة.': 'Unable to load previous versions.',
    'الاجمالي': 'Total',
    'مجموع الضرائب': 'Total taxes',
    'الضرائب': 'Taxes',
    'الخصومات': 'Deductions',
    'مجموع الخصومات': 'Total deductions',
    'ما سبق صرفه': 'Previously paid',
    'لا توجد ضرائب': 'No taxes',
    'لا توجد خصومات': 'No deductions',
    'لا توجد مدفوعات سابقة': 'No previous payments',
    'تفاصيل': 'Details',
    'تعديل الحسابات': 'Edit accounting',
    'الاجمالي + الضرائب': 'Total + taxes',
    'مجموع ما سبق صرفه': 'Total previously paid',
    'مجموع الخصومات و ما سبق صرفه': 'Total deductions and previously paid',
    'صافي المستخلص': 'Net invoice',
    'اضافة البند للتعديل': 'Add main category to edit',
    'عنوان البند الرئيسي': 'Main category title',
    'البنود الفرعية': 'Sub-items',
    'عنوان البند الفرعي': 'Sub-item title',
    'اسم الضريبة': 'Tax name',
    'اسم الخصم': 'Deduction name',
    'الكمية بالجنية': 'Amount in EGP',
    'اختر ملف المستخلص': 'Choose invoice file',
    'رفع ملف Excel': 'Upload Excel file',
    'النسبة': 'Tax rate',
    'التفاصيل و البحث': 'Details and search'
  });
  reversePairs['نشط'] = 'Active';
  reversePairs['غير نشط'] = 'Inactive';
  const storageKey = 'inshaa-language';
  const pageDirection = document.documentElement.dir || 'ltr';
   let observer = null;
  const svg = '<svg viewBox="0 0 28 28" aria-hidden="true" focusable="false"><circle cx="12" cy="14" r="8.5"></circle><path d="M3.5 14h17M12 5.5c2.1 2.4 3.1 5.2 3.1 8.5S14.1 20.1 12 22.5 8.9 17.3 8.9 14 9.9 7.9 12 5.5z"></path><path class="language-arrow" d="M19 5h5v5M24 5l-4.5 4.5"></path></svg>';

  function translateValue(value, dictionary) {
    const leading = value.match(/^\s*/)[0];
    const trailing = value.match(/\s*$/)[0];
    const core = value.trim();
    return dictionary[core] ? leading + dictionary[core] + trailing : value;
  }

  function translatePage(language) {
     if (observer) observer.disconnect();
    const dictionary = language === 'ar' ? pairs : reversePairs;
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    const textNodes = [];
    let node;
    while ((node = walker.nextNode())) textNodes.push(node);
    textNodes.forEach((textNode) => {
      if (textNode.parentElement.closest('script, style, .language-toggle')) return;
      textNode.nodeValue = translateValue(textNode.nodeValue, dictionary);
    });

    document.querySelectorAll('input[placeholder], select option, [title], [aria-label]').forEach((element) => {
      ['placeholder', 'title', 'aria-label'].forEach((attribute) => {
        if (element.hasAttribute(attribute)) {
          element.setAttribute(attribute, translateValue(element.getAttribute(attribute), dictionary));
        }
      });
      if (element.tagName === 'OPTION') element.textContent = translateValue(element.textContent, dictionary);
    });

    document.querySelectorAll('.prev-version-badge span').forEach((element) => {
      const label = element.textContent.trim();
      if (label === 'Current version' || label === 'النسخة الحالية') {
        element.textContent = language === 'ar' ? 'النسخة الحالية' : 'Current version';
      }
      if (label === 'Previous version' || label === 'نسخة قديمة') {
        element.textContent = language === 'ar' ? 'نسخة قديمة' : 'Previous version';
      }
    });
    document.querySelectorAll('.back-link').forEach((element) => {
      element.textContent = language === 'ar' ? 'الرجوع' : 'Back';
    });

    document.documentElement.lang = language === 'ar' ? 'ar' : 'en';
    document.documentElement.dir = pageDirection;
    document.body.classList.toggle('language-ar', language === 'ar');
    document.body.classList.toggle('language-en', language === 'en');
    if (observer) observer.observe(document.body, { childList: true, characterData: true, subtree: true });
  }

  function updateButton(button, language) {
    button.innerHTML = svg + '<span>' + (language === 'ar' ? 'English' : 'عربي') + '</span>';
    button.setAttribute('aria-label', language === 'ar' ? 'Switch to English' : 'التبديل إلى العربية');
    button.title = language === 'ar' ? 'Switch to English' : 'التبديل إلى العربية';
  }

  function init() {
    const header = document.querySelector('.header-inner');
    if (!header) return;

    const host = header.querySelector('.header-actions') || header;
    header.classList.add('language-stable-header');
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'language-toggle';
    host.appendChild(button);

    const style = document.createElement('style');
    style.textContent = '@font-face{font-family:InshaaArabic;src:url("/static/fonts/NotoSansArabic-Regular.ttf") format("truetype");font-weight:400;font-style:normal;font-display:swap}@font-face{font-family:InshaaArabic;src:url("/static/fonts/NotoSansArabic-SemiBold.ttf") format("truetype");font-weight:600;font-style:normal;font-display:swap}@font-face{font-family:InshaaArabic;src:url("/static/fonts/NotoSansArabic-Bold.ttf") format("truetype");font-weight:700;font-style:normal;font-display:swap}.language-stable-font,.language-stable-font *{font-family:InshaaArabic,"Barlow",sans-serif!important}.site-header,.site-header *{direction:ltr!important}.language-stable-header,.language-stable-header *{font-family:"Barlow",sans-serif!important}.language-stable-header{display:flex!important;align-items:center!important;justify-content:space-between!important;direction:ltr!important;flex-direction:row!important;flex-wrap:nowrap!important}.language-stable-header .header-actions{direction:ltr!important;flex-direction:row!important}.language-stable-header>.language-toggle{margin-left:auto}.language-stable-header .settings-btn{flex:0 0 112px}.language-stable-header .backup-link{flex:0 0 174px}.language-stable-header .header-action-btn{flex:0 0 178px}.language-stable-header .logout-link{flex:0 0 138px}.language-toggle{display:inline-flex;align-items:center;justify-content:center;gap:8px;min-height:42px;padding:6px 12px;border:1px solid rgba(255,255,255,.42);border-radius:11px;background:linear-gradient(135deg,rgba(255,255,255,.19),rgba(255,255,255,.07));color:#fff;font:600 13px "Barlow",sans-serif;cursor:pointer;white-space:nowrap;flex:0 0 82px;box-shadow:inset 0 1px 0 rgba(255,255,255,.22),0 4px 12px rgba(2,25,39,.14);transition:transform .22s ease,background .22s ease,border-color .22s ease,box-shadow .22s ease}.language-toggle svg{width:23px;height:23px;fill:none;stroke:currentColor;stroke-width:1.65;stroke-linecap:round;stroke-linejoin:round;overflow:visible}.language-toggle .language-arrow{stroke-width:1.8;transition:transform .22s ease}.language-toggle:hover{transform:translateY(-2px);background:linear-gradient(135deg,rgba(255,255,255,.3),rgba(255,255,255,.12));border-color:rgba(255,255,255,.85);box-shadow:inset 0 1px 0 rgba(255,255,255,.28),0 8px 18px rgba(0,0,0,.2)}.language-toggle:hover .language-arrow{transform:translate(1px,-1px)}.language-toggle:active{transform:translateY(0) scale(.96)}.language-toggle:focus-visible{outline:2px solid #fff;outline-offset:3px}@media(max-width:640px){.language-stable-header{flex-wrap:wrap!important}.language-stable-header .header-actions{flex-wrap:wrap!important}.language-stable-header .settings-btn,.language-stable-header .backup-link,.language-stable-header .header-action-btn,.language-stable-header .logout-link,.language-toggle{flex:0 0 auto}.language-toggle{min-height:40px;padding:6px 10px}.language-toggle span{display:none}}';
    document.head.appendChild(style);

    let language = localStorage.getItem(storageKey) || (document.documentElement.lang === 'ar' ? 'ar' : 'en');
    document.body.classList.add('language-stable-font');
    updateButton(button, language);
    translatePage(language);
    observer = new MutationObserver((mutations) => {
      if (mutations.some((mutation) => mutation.addedNodes.length)) translatePage(language);
    });
    observer.observe(document.body, { childList: true, characterData: true, subtree: true });
    button.addEventListener('click', () => {
      language = language === 'ar' ? 'en' : 'ar';
      localStorage.setItem(storageKey, language);
      translatePage(language);
      updateButton(button, language);
    });
    document.addEventListener('change', (event) => {
      if (event.target.matches('select')) translatePage(language);
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
