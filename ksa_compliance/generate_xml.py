from frappe import get_jenv


def generate_xml_file(data: dict):
    env = get_jenv()
    lstrip = env.lstrip_blocks
    trim = env.trim_blocks
    env.lstrip_blocks = True
    env.trim_blocks = True
    try:
        template = env.get_template('ksa_compliance/templates/e_invoice.xml')
        return template.render(
            {
                'invoice': data.get('invoice'),
                'seller_details': data.get('seller_details'),
                'buyer_details': data.get('buyer_details'),
                'business_settings': data.get('business_settings'),
                'prepayment_invoice': data.get('prepayment_invoice'),
            }
        )
    finally:
        env.lstrip_blocks = lstrip
        env.trim_blocks = trim
