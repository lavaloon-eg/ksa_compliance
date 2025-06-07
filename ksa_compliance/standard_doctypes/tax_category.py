from typing import Optional

import frappe

from ..output_models.models import ZatcaTaxCategory


def map_tax_category(
    tax_category_id: Optional[str] = None, item_tax_template_id: Optional[str] = None
) -> ZatcaTaxCategory:
    if tax_category_id:
        zatca_category, custom_category_reason = frappe.get_value(
            'Tax Category', {'name': tax_category_id}, ['custom_zatca_category', 'custom_category_reason']
        )
    elif item_tax_template_id:
        zatca_category, custom_category_reason = frappe.get_value(
            'Item Tax Template',
            {'name': item_tax_template_id},
            ['custom_zatca_item_tax_category', 'custom_category_reason'],
        )
    else:
        zatca_category = 'Standard rate'
        custom_category_reason = None

    zatca_category = zatca_category if zatca_category else 'Standard rate'
    if zatca_category == 'Standard rate':
        return ZatcaTaxCategory(_category_to_code(zatca_category))

    category, reason = zatca_category.split(' || ')
    if custom_category_reason and reason == '{manual entry}':
        reason_data = _reason_to_code_and_arabic(reason, custom_category_reason)
    else:
        reason_data = _reason_to_code_and_arabic(reason)
    return ZatcaTaxCategory(_category_to_code(category), reason_data['reason_code'], reason_data['arabic_reason'])


def _category_to_code(category: str) -> str:
    categories = {
        'Standard rate': 'S',
        'Exempt from Tax': 'E',
        'Zero rated goods': 'Z',
        'Services outside scope of tax / Not subject to VAT': 'O',
    }
    return categories[category]


def _reason_to_code_and_arabic(reason: str, input_reason: Optional[str] = None) -> dict:
    # TODO: Update the lookup to use reason code instead of text decoded from the select field in tax category doctype.
    reasons = {
        'Financial services mentioned in Article 29 of the VAT Regulations': {
            'reason_code': 'VATEX-SA-29',
            'arabic_reason': 'عقد تأمين على الحياة',
        },
        'Life insurance services mentioned in Article 29 of the VAT Regulations': {
            'reason_code': 'VATEX-SA-29-7',
            'arabic_reason': 'الخدمات المالية',
        },
        'Real estate transactions mentioned in Article 30 of the VAT Regulations': {
            'reason_code': 'VATEX-SA-30',
            'arabic_reason': 'التوريدات العقارية المعفاة من الضريبة',
        },
        'Export of goods': {
            'reason_code': 'VATEX-SA-32',
            'arabic_reason': 'صادرات السلع من المملكة',
        },
        'Export of services': {
            'reason_code': 'VATEX-SA-33',
            'arabic_reason': 'صادرات الخدمات من المملكة',
        },
        'The international transport of Goods': {
            'reason_code': 'VATEX-SA-34-1',
            'arabic_reason': 'النقل الدولي للسلع',
        },
        'International transport of passengers': {
            'reason_code': 'VATEX-SA-34-2',
            'arabic_reason': 'النقل الدولي للركاب',
        },
        'Services directly connected and incidental to a Supply of international passenger transport': {
            'reason_code': 'VATEX-SA-34-3',
            'arabic_reason': 'الخدمات المرتبطة مباشرة او عرضيًا بتوريد النقل الدولي للركاب',
        },
        'Supply of a qualifying means of transport': {
            'reason_code': 'VATEX-SA-34-4',
            'arabic_reason': 'توريد وسائل النقل المؤهلة',
        },
        'Any services relating to Goods or passenger transportation as defined in article twenty five of these '
        'Regulations': {
            'reason_code': 'VATEX-SA-34-5',
            'arabic_reason': 'الخدمات ذات الصلة بنقل السلع او الركاب، وفقاً للتعريف الوارد بالمادة الخامسة و العشرين '
            'من اللائحة التنفيذية لنظام ضريبة القيمة المضافة',
        },
        'Medicines and medical equipment': {
            'reason_code': 'VATEX-SA-35',
            'arabic_reason': 'الادوية والمعدات الطبية',
        },
        'Qualifying metals': {
            'reason_code': 'VATEX-SA-36',
            'arabic_reason': 'المعادن المؤهلة',
        },
        'Private education to citizen': {
            'reason_code': 'VATEX-SA-EDU',
            'arabic_reason': 'الخدمات التعليمية الخاصة للمواطنين',
        },
        'Private healthcare to citizen': {
            'reason_code': 'VATEX-SA-HEA',
            'arabic_reason': 'الخدمات الصحية الخاصة للمواطنين',
        },
        'Supply of qualified military goods': {
            'reason_code': 'VATEX-SA-MLTRY',
            'arabic_reason': 'توريد السلع العسكرية المؤهلة',
        },
        '{manual entry}': {'reason_code': 'VATEX-SA-OOS', 'arabic_reason': input_reason},
        'Qualified Supply of Goods in Duty Free area': {
            'reason_code': 'VATEX-SA-DUTYFREE',
            'arabic_reason': 'التوريد المؤهل للسلع في الأسواق الحرة',
        },
    }
    return reasons[reason]
